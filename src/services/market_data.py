# src/services/market_data.py
import finnhub
import requests
from datetime import datetime, timedelta
import pandas as pd
from utils.constants import api_keys
from utils.db import db
import random
import yfinance as yf
from google.cloud import firestore
import traceback
import time
import os

# Cache for API call results to reduce redundant calls
_price_cache = {}
# Track API call times to prevent rate limiting
_last_call_time = {}

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

def fetch_stock_data(symbol, api_key=None, force_refresh=False):
    """Fetch stock data with multiple API sources for reliability."""
    cache_key = f"{symbol}:{api_key if api_key else 'default'}"
    current_time = time.time()
    
    # Check cache first
    if not force_refresh and cache_key in _price_cache:
        cache_entry = _price_cache[cache_key]
        if current_time - cache_entry['timestamp'] < 300:  # 5 minutes cache
            print(f"[MARKET_DATA] Using cached data for {symbol}")
            return cache_entry['data']
    
    print(f"\n[MARKET_DATA] Fetching fresh data for {symbol}")
    
    # Try Finnhub first - this is our primary source
    try:
        if not api_key:
            api_key = get_random_api_key()
        
        if api_key:
            print(f"[MARKET_DATA] Using Finnhub API key: {api_key[:4]}...{api_key[-4:]}")
            
            # Add delay to prevent rate limiting
            if symbol in _last_call_time:
                since_last_call = current_time - _last_call_time[symbol]
                if since_last_call < 0.5:  # At least 500ms between calls
                    sleep_time = 0.5 - since_last_call
                    time.sleep(sleep_time)
            
            _last_call_time[symbol] = current_time
            
            # Make API call with proper error handling
            finnhub_client = finnhub.Client(api_key=api_key)
            data = finnhub_client.quote(symbol)
            
            # Validate the response data thoroughly
            if isinstance(data, dict) and 'c' in data:
                current_price = float(data['c'])
                prev_close = float(data.get('pc', current_price))
                
                # Additional validation to ensure prices are reasonable
                if current_price > 0 and prev_close > 0:
                    result = {
                        'symbol': symbol,
                        'open': float(data.get('o', current_price)),
                        'high': float(data.get('h', current_price)),
                        'low': float(data.get('l', current_price)),
                        'prev_close': prev_close,
                        'close': current_price,
                        'source': 'finnhub'
                    }
                    
                    # Cache successful result
                    _price_cache[cache_key] = {
                        'timestamp': current_time,
                        'data': result
                    }
                    
                    print(f"[MARKET_DATA] ✅ Successfully fetched {symbol} price: ${current_price}")
                    return result
                else:
                    print(f"[MARKET_DATA] ⚠️ Invalid price values for {symbol}: {data}")
            else:
                print(f"[MARKET_DATA] ⚠️ Invalid response format for {symbol}: {data}")
    except Exception as e:
        print(f"[MARKET_DATA] ❌ Finnhub error for {symbol}: {str(e)}")
        if "Invalid API key" in str(e):
            # Remove invalid key if possible
            if api_key in api_keys and len(api_keys) > 1:
                api_keys.remove(api_key)
                print(f"[MARKET_DATA] Removed invalid API key. {len(api_keys)} keys remaining.")
    
    # If Finnhub fails, try yfinance
    try:
        print(f"[MARKET_DATA] Trying yfinance for {symbol}")
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='2d')
        
        if len(hist) >= 1:
            today = hist.iloc[-1]
            prev_close = float(hist.iloc[-2]['Close']) if len(hist) >= 2 else float(today['Open'])
            current_price = float(today['Close'])
            
            if current_price > 0:
                result = {
                    'symbol': symbol,
                    'open': float(today['Open']),
                    'high': float(today['High']),
                    'low': float(today['Low']),
                    'prev_close': prev_close,
                    'close': current_price,
                    'source': 'yfinance'
                }
                
                # Cache successful result
                _price_cache[cache_key] = {
                    'timestamp': current_time,
                    'data': result
                }
                
                print(f"[MARKET_DATA] ✅ Successfully fetched {symbol} price from yfinance: ${current_price}")
                return result
    except Exception as e:
        print(f"[MARKET_DATA] ❌ yfinance error for {symbol}: {str(e)}")
    
    # As a last resort, check database cache
    try:
        stock_ref = db.collection('stock_prices').document(symbol)
        stock_doc = stock_ref.get()
        if stock_doc.exists:
            stock_data = stock_doc.to_dict()
            cached_price = stock_data.get('close', 0)
            if cached_price > 0:
                print(f"[MARKET_DATA] Using database cache for {symbol}")
                return {
                    'symbol': symbol,
                    'open': stock_data.get('open', cached_price),
                    'high': stock_data.get('high', cached_price),
                    'low': stock_data.get('low', cached_price),
                    'prev_close': stock_data.get('prev_close', cached_price),
                    'close': cached_price,
                    'source': 'database_cache'
                }
    except Exception as e:
        print(f"[MARKET_DATA] ❌ Database cache error for {symbol}: {str(e)}")
    
    print(f"[MARKET_DATA] ⚠️ All data sources failed for {symbol}")
    return {
        'symbol': symbol,
        'error': f'Unable to fetch price data for {symbol}',
        'close': 0,
        'source': 'error'
    }

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
    """Fetch historical price data for a stock symbol."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            return None
            
        # Convert the DataFrame to the expected format
        df = pd.DataFrame()
        df['date'] = hist.index
        df['open'] = hist['Open']
        df['high'] = hist['High']
        df['low'] = hist['Low']
        df['close'] = hist['Close']
        df['volume'] = hist['Volume']
        
        return df
    except Exception as e:
        print(f"Error fetching historical data for {symbol}: {e}")
        return None

def fetch_user_portfolio(user_id):
    """Fetch the current user's portfolio data including performance metrics and detailed positions."""
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
        
        return {
            'summary': summary,
            'positions': sorted(detailed_positions, key=lambda x: x['value'], reverse=True) # Sort by value
        }

    except Exception as e:
        print(f"Error fetching user portfolio for {user_id}: {e}")
        traceback.print_exc()
        # Return a default empty structure on error
        return {
            'summary': {
                'Total Assets': '$0.00', 'Cash Balance': '$0.00', 'Invested Value': '$0.00',
                'Total P/L': '$0.00 (0.0%)', "Today's P/L": '$0.00', 'Active Positions': 0,
                'Win Rate': '0.0%', 'total_value_raw': 0, 'invested_value_raw': 0,
                'available_cash_raw': 0, 'day_change_raw': 0, 'total_pl_raw': 0
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

