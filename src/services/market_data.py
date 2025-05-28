# src/services/market_data.py
import finnhub
import requests
from datetime import datetime, timedelta
import pandas as pd
from utils.constants import api_keys
from utils.db import db
import random
from google.cloud import firestore
import traceback
import time
import os

# Cache for API call results to reduce redundant calls
_price_cache = {}
# Track API call times to prevent rate limiting
_last_call_time = {}

# Updated constants
MAX_RETRIES = 3
INITIAL_BACKOFF = 0.5  # seconds
CACHE_DURATION = 300   # 5 minutes

# Rate limiting and API key rotation constants
RATE_LIMIT_COOLDOWN = 60  # 1 minute cooldown for rate limiting
RATE_LIMIT_WINDOW = 60  # 1 minute window
MAX_CALLS_PER_WINDOW = 30  # Maximum calls per minute per key
KEY_COOLDOWN = 60  # 1 minute cooldown after rate limit

# Initialize rate limiting tracking
_rate_limit_timestamps = {}

class MarketDataSource:
    def __init__(self, name, fetch_func, cooldown=60):
        self.name = name
        self.fetch_func = fetch_func
        self.cooldown = cooldown
        self.last_error = None
        self.error_count = 0
        self.last_request = 0

    def is_available(self):
        if self.last_error and time.time() - self.last_error < self.cooldown:
            return False
        return True

    def handle_error(self, error):
        self.last_error = time.time()
        self.error_count += 1
        self.cooldown = min(300, self.cooldown * 2)  # Max 5 minute cooldown
        print(f"[MARKET_DATA] {self.name} error: {error}. Cooldown: {self.cooldown}s")

def get_api_key_index(api_key):
    """Get the index of the given API key in the api_keys list."""
    if not api_key:
        return -1
    
    try:
        return api_keys.index(api_key)
    except ValueError:
        return -1

def get_random_api_key():
    """Select a random API key from the list with basic load balancing."""
    if not api_keys or len(api_keys) == 0:
        print("\n[MARKET_DATA] ⚠️ No Finnhub API keys available - FALLING BACK TO ALTERNATIVE SOURCES ⚠️")
        return None
    
    # Select key with least recent usage if we have timing data
    if len(_last_call_time) > 0 and len(_last_call_time) == len(api_keys):
        # Find the least recently used key
        selected_key = min(_last_call_time.items(), key=lambda x: x[1])[0]
    else:
        # Otherwise just pick randomly
        selected_key = random.choice(api_keys)
    
    # Update the last call time for this key
    _last_call_time[selected_key] = time.time()
    
    key_index = api_keys.index(selected_key)
    
    # Create a emphasized visible log entry with the key details
    print("\n" + "="*50)
    print(f"[MARKET_DATA] SELECTED API KEY #{key_index + 1} OF {len(api_keys)}")
    masked_key = f"{selected_key[:4]}...{selected_key[-4:]}" if len(selected_key) > 8 else "****"
    print(f"[MARKET_DATA] KEY: {masked_key}")
    print("="*50 + "\n")
    
    return selected_key

def is_rate_limited(source):
    """Check if a data source is currently rate limited."""
    last_limit = _rate_limit_timestamps.get(source, 0)
    return (time.time() - last_limit) < RATE_LIMIT_COOLDOWN

def mark_rate_limited(source):
    """Mark a data source as rate limited."""
    _rate_limit_timestamps[source] = time.time()
    print(f"[MARKET_DATA] ⚠️ {source} rate limited, cooling down for {RATE_LIMIT_COOLDOWN}s")

class ApiKeyManager:
    def __init__(self):
        self.calls = {}  # Track API calls per key
        self.cooldowns = {}  # Track cooldown periods
        self._last_reset = {}  # Track when we last reset counts
    
    def can_use_key(self, key):
        """Check if a key can be used."""
        current_time = time.time()
        
        # Check cooldown
        if key in self.cooldowns:
            if current_time - self.cooldowns[key] < KEY_COOLDOWN:
                return False
            del self.cooldowns[key]
        
        # Initialize or reset window if needed
        if key not in self.calls or current_time - self._last_reset.get(key, 0) >= RATE_LIMIT_WINDOW:
            self.calls[key] = 0
            self._last_reset[key] = current_time
        
        return self.calls.get(key, 0) < MAX_CALLS_PER_WINDOW
    
    def mark_call(self, key):
        """Record an API call for a key."""
        if key not in self.calls:
            self.calls[key] = 0
        self.calls[key] += 1
    
    def mark_rate_limited(self, key):
        """Mark a key as rate limited."""
        self.cooldowns[key] = time.time()

# Initialize the key manager
key_manager = ApiKeyManager()

def _fetch_from_alphavantage(symbol):
    """Fetch stock data from Alpha Vantage."""
    try:
        alpha_vantage_key = os.environ.get('ALPHA_VANTAGE_KEY')
        if not alpha_vantage_key:
            return None
            
        url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={alpha_vantage_key}'
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if 'Global Quote' in data:
                quote = data['Global Quote']
                return {
                    'symbol': symbol,
                    'close': float(quote.get('05. price', 0)),
                    'prev_close': float(quote.get('08. previous close', 0)),
                    'source': 'alphavantage'
                }
    except Exception as e:
        print(f"[MARKET_DATA] Alpha Vantage error: {e}")
    return None

def _fetch_from_finnhub(symbol):
    """Enhanced Finnhub fetch with better error handling."""
    if not api_keys:
        return None

    for key in api_keys:
        if not key_manager.can_use_key(key):
            print(f"[MARKET_DATA] Key {key[:8]}... cooling down, skipping")
            continue
        
        try:
            url = 'https://finnhub.io/api/v1/quote'
            headers = {'X-Finnhub-Token': key}
            params = {'symbol': symbol}
            
            key_manager.mark_call(key)
            response = requests.get(url, params=params)
            
            if response.status_code == 429:
                print(f"[MARKET_DATA] Key {key[:8]}... rate limited")
                key_manager.mark_rate_limited(key)
                continue
            
            if response.status_code == 200:
                data = response.json()
                if 'c' in data:
                    print(f"[MARKET_DATA] Successfully fetched {symbol} data from Finnhub")
                    return {
                        'symbol': symbol,
                        'close': float(data['c']),
                        'prev_close': float(data['pc']),
                        'source': 'finnhub'
                    }
        except Exception as e:
            print(f"[MARKET_DATA] Finnhub error with key {key[:8]}...: {e}")
            continue

    return None

def fetch_stock_data(symbol, force_refresh=False):
    """Enhanced fetch stock data prioritizing Finnhub."""
    cache_key = f"stock_price:{symbol}"
    current_time = time.time()

    # Try memory cache first
    if not force_refresh and cache_key in _price_cache:
        cache_data = _price_cache[cache_key]
        if current_time - cache_data['timestamp'] < CACHE_DURATION:
            print(f"[MARKET_DATA] Using memory cache for {symbol}")
            return cache_data['data']

    # Try Finnhub first (primary source)
    finnhub_result = _fetch_from_finnhub(symbol)
    if finnhub_result:
        _cache_price_data(symbol, finnhub_result)
        return finnhub_result

    # If Finnhub fails, try Alpha Vantage
    alpha_result = _fetch_from_alphavantage(symbol)
    if alpha_result:
        _cache_price_data(symbol, alpha_result)
        return alpha_result

    # If all live sources fail, try cache
    return _get_fallback_price(symbol)

def fetch_crypto_data(symbol):
    """Fetch cryptocurrency data using Coinbase API."""
    try:
        response = requests.get(f'https://api.coinbase.com/v2/prices/{symbol}-USD/spot')
        if response.status_code == 200:
            data = response.json()
            price = float(data['data']['amount'])
            return {
                'symbol': symbol,
                'price': price,
                'prev_close': price * 0.99,  # Approximation as Coinbase doesn't provide previous close
                'change_percent': 0.0  # Placeholder as we don't have historical data here
            }
        else:
            return {'error': f'Failed to fetch crypto data: API returned status {response.status_code}'}
    
    except requests.exceptions.RequestException as e:
        return {'error': f'Failed to fetch crypto data: {str(e)}'}

def fetch_historical_data(symbol, period='1y'):
    """Fetch historical price data using Finnhub instead of yfinance."""
    try:
        if not api_keys:
            return None
        
        # Convert period to timestamps
        end_timestamp = int(time.time())
        period_days = {
            '1d': 1,
            '5d': 5,
            '1m': 30,
            '6m': 180,
            '1y': 365,
            '5y': 1825
        }.get(period, 365)  # Default to 1 year
        
        start_timestamp = end_timestamp - (period_days * 24 * 60 * 60)
        
        # Try each API key until we get data
        for key in api_keys:
            if not key_manager.can_use_key(key):
                continue
            
            url = 'https://finnhub.io/api/v1/stock/candle'
            params = {
                'symbol': symbol,
                'resolution': 'D',  # Daily candles
                'from': start_timestamp,
                'to': end_timestamp,
                'token': key
            }
            
            key_manager.mark_call(key)
            response = requests.get(url, params=params)
            
            if response.status_code == 429:
                key_manager.mark_rate_limited(key)
                continue
            
            if response.status_code == 200:
                data = response.json()
                if data.get('s') == 'ok':
                    # Convert to DataFrame format
                    df = pd.DataFrame({
                        'date': pd.to_datetime(data['t'], unit='s'),
                        'open': data['o'],
                        'high': data['h'],
                        'low': data['l'],
                        'close': data['c'],
                        'volume': data['v']
                    })
                    df.set_index('date', inplace=True)
                    return df
    
    except Exception as e:
        print(f"Error fetching historical data: {e}")
        print(traceback.format_exc())
    
    # Try fallback cache if API fails
    return _get_cached_historical_data(symbol)

def _get_cached_historical_data(symbol):
    """Get historical data from cache or database."""
    try:
        doc = db.collection('historical_prices').document(symbol).get()
        if doc.exists:
            data = doc.to_dict()
            if 'prices' in data:
                return pd.DataFrame(data['prices'])
    except Exception as e:
        print(f"Cache retrieval error: {e}")
    return None

def fetch_user_portfolio(user_id):
    """Enhanced portfolio fetching with better error handling and caching."""
    cache_key = f"portfolio:{user_id}"
    current_time = time.time()
    
    # Try memory cache first
    if cache_key in _price_cache:
        cache_data = _price_cache[cache_key]
        if current_time - cache_data['timestamp'] < CACHE_DURATION:
            print(f"[MARKET_DATA] Using cached portfolio for {user_id}")
            return cache_data['data']
    
    try:
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            # Return a default empty structure if user not found
            return {
                'summary': {
                    'Total Assets': '$0.00', 'Cash Balance': '$0.00', 'Invested Value': '$0.00',
                    'Total P/L': '$0.00 (0.0%)', "Today's P/L": '$0.00', 'Active Positions': 0,
                    'Win Rate': '0.0%', 'total_value_raw': 0, 'invested_value_raw': 0,
                    'available_cash_raw': 0, 'day_change_raw': 0, 'total_pl_raw': 0
                },
                'positions': []
            }
        
        user_data = user_doc.to_dict()
        cash_balance = user_data.get('balance', 0)
        
        portfolio_items_query = db.collection('portfolios').where('user_id', '==', user_id).stream()
        
        detailed_positions = []
        total_invested_value_current = 0.0
        total_purchase_cost = 0.0
        total_day_change_value = 0.0
        active_positions_count = 0

        for item_doc in portfolio_items_query:
            item_data = item_doc.to_dict()
            symbol = item_data['symbol']
            shares = float(item_data.get('shares', 0))
            purchase_price = float(item_data.get('purchase_price', 0))

            if shares <= 0: # Skip positions with no shares
                continue
            
            active_positions_count += 1
            
            price_data = fetch_stock_data(symbol) # This already has caching
            current_price = purchase_price # Fallback to purchase price
            prev_close_price = purchase_price # Fallback for day change calculation

            if price_data and 'close' in price_data and price_data['close'] is not None and price_data['close'] > 0:
                current_price = float(price_data['close'])
                prev_close_price = float(price_data.get('prev_close', current_price)) # Use current if prev_close is missing
            elif price_data and price_data.get('source') == 'error':
                 print(f"⚠️ API failed for {symbol} in fetch_user_portfolio, using purchase price.")
            
            current_position_value = shares * current_price
            position_purchase_cost = shares * purchase_price
            
            profit_loss = current_position_value - position_purchase_cost
            profit_loss_pct = (profit_loss / position_purchase_cost * 100) if position_purchase_cost > 0 else 0
            day_change = (current_price - prev_close_price) * shares
            
            detailed_positions.append({
                'symbol': symbol,
                'shares': shares,
                'purchase_price': purchase_price,
                'current_price': current_price,
                'value': current_position_value,
                'profit_loss': profit_loss,
                'profit_loss_pct': profit_loss_pct,
                'day_change': day_change,
                'purchase_date': item_data.get('purchase_date', datetime.utcnow()) 
            })
            
            total_invested_value_current += current_position_value
            total_purchase_cost += position_purchase_cost
            total_day_change_value += day_change

        total_portfolio_value = total_invested_value_current + cash_balance
        overall_profit_loss = total_invested_value_current - total_purchase_cost if active_positions_count > 0 else 0
        
        # Calculate overall P/L percentage based on the total cost of current holdings
        overall_profit_loss_percentage = (overall_profit_loss / total_purchase_cost * 100) if total_purchase_cost > 0 else 0

        # Get transaction data for win rate (simplified)
        transactions_query = db.collection('transactions').where('user_id', '==', user_id).where('transaction_type', '==', 'SELL').stream()
        total_sell_trades = 0
        winning_sell_trades = 0
        for t_doc in transactions_query:
            t_data = t_doc.to_dict()
            total_sell_trades +=1
            if t_data.get('profit_loss', 0) > 0:
                winning_sell_trades +=1
        win_rate = (winning_sell_trades / total_sell_trades * 100) if total_sell_trades > 0 else 0
        
        summary = {
            'Total Assets': f'${total_portfolio_value:,.2f}',
            'Cash Balance': f'${cash_balance:,.2f}',
            'Invested Value': f'${total_invested_value_current:,.2f}',
            'Total P/L': f"{'+' if overall_profit_loss >= 0 else ''}${overall_profit_loss:,.2f} ({overall_profit_loss_percentage:.1f}%)",
            "Today's P/L": f"{'+' if total_day_change_value >= 0 else ''}${total_day_change_value:,.2f}",
            'Active Positions': active_positions_count,
            'Win Rate': f"{win_rate:.1f}%",
            # Raw values for easier use in templates/JS if needed
            'total_value_raw': total_portfolio_value,
            'invested_value_raw': total_invested_value_current,
            'available_cash_raw': cash_balance,
            'day_change_raw': total_day_change_value,
            'total_pl_raw': overall_profit_loss
        }
        
        # Cache the result before returning
        _price_cache[cache_key] = {
            'timestamp': current_time,
            'data': {
                'summary': summary,
                'positions': detailed_positions
            }
        }
        
        return {
            'summary': summary,
            'positions': sorted(detailed_positions, key=lambda x: x['value'], reverse=True)
        }

    except Exception as e:
        print(f"Error fetching user portfolio for {user_id}: {e}")
        traceback.print_exc()
        # Return a default structure
        return {
            'summary': {
                'Total Assets': '$0.00',
                'Cash Balance': '$0.00',
                'Invested Value': '$0.00',
                'Total P/L': '$0.00 (0.0%)',
                "Today's P/L": '$0.00',
                'Active Positions': 0,
                'Win Rate': '0.0%',
                'total_value_raw': 0,
                'invested_value_raw': 0,
                'available_cash_raw': 0,
                'day_change_raw': 0,
                'total_pl_raw': 0
            },
            'positions': []
        }

def calculate_total_portfolio_value(user_id):
    """
    Calculate a simplified total value of a user's portfolio.
    This function is kept for potential quick summaries if the full fetch_user_portfolio is too heavy,
    but fetch_user_portfolio is now the recommended function for comprehensive data.
    """
    portfolio_summary = fetch_user_portfolio(user_id)['summary']
    return {
            'total_value': portfolio_summary['total_value_raw'],
            'invested_value': portfolio_summary['invested_value_raw'],
            'available_cash': portfolio_summary['available_cash_raw'],
            'active_positions': portfolio_summary['Active Positions']
        }

def calculate_price_change(current, previous):
    """Calculate percentage change and format as string."""
    if previous <= 0:
        return 0, "0.00%"
        
    change_pct = ((current - previous) / previous) * 100
    change_str = f"{'+' if change_pct > 0 else ''}{change_pct:.2f}%"
    
    return change_pct, change_str

def fetch_recent_orders(user_id, limit=5):
    """Fetch the user's most recent transactions."""
    try:
        transactions = db.collection('transactions')\
            .where('user_id', '==', user_id)\
            .order_by('timestamp', direction=firestore.Query.DESCENDING)\
            .limit(limit)\
            .stream()
        
        orders = []
        for transaction in transactions:
            t_data = transaction.to_dict()
            orders.append({
                'Date': t_data.get('timestamp').strftime('%Y-%m-%d %H:%M:%S') if 'timestamp' in t_data else 'N/A',
                'Symbol': t_data.get('symbol', 'N/A'),
                'Type': t_data.get('transaction_type', 'N/A'),
                'Quantity': t_data.get('shares', 0),
                'Price': t_data.get('price', 0),
                'Status': 'Completed'
            })
        
        return orders
    except Exception as e:
        print(f"Error fetching recent orders: {e}")
        return []

def get_api_keys_status():
    """Get the status of all API keys for display in the UI."""
    # Check Finnhub keys
    finnhub_status = {
        'available': len(api_keys) > 0,
        'count': len(api_keys),
        'keys': [f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "****" for key in api_keys],
        'status': 'Available' if len(api_keys) > 0 else 'Not configured'
    }
    
    # Check if we have Alpha Vantage
    alpha_vantage_key = os.environ.get('ALPHA_VANTAGE_KEY')
    alpha_vantage_status = {
        'available': alpha_vantage_key is not None,
        'status': 'Available' if alpha_vantage_key else 'Not configured'
    }
    
    # YFinance is always available as a fallback
    yfinance_status = {
        'available': True,
        'status': 'Available (rate-limited)'
    }
    
    # Coinbase is also always available for crypto
    coinbase_status = {
        'available': True,
        'status': 'Available'
    }
    
    return {
        'finnhub': finnhub_status,
        'alpha_vantage': alpha_vantage_status,
        'yfinance': yfinance_status,
        'coinbase': coinbase_status
    }

