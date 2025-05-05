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

def get_random_api_key():
    """Select a random API key from the list."""
    return random.choice(api_keys)

def fetch_stock_data(symbol):
    """Fetch stock data using Finnhub and fallback to yfinance."""
    try:
        # Try Finnhub first
        api_key = get_random_api_key()
        finnhub_client = finnhub.Client(api_key=api_key)
        data = finnhub_client.quote(symbol)
        
        if isinstance(data, dict) and 'c' in data:
            return {
                'symbol': symbol,
                'open': data.get('o', 0),
                'high': data.get('h', 0),
                'low': data.get('l', 0),
                'prev_close': data.get('pc', 0),
                'close': data.get('c', 0)
            }
        
        # Fallback to yfinance
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period='2d')
        
        if len(hist) >= 2:
            today = hist.iloc[-1]
            yesterday = hist.iloc[-2]
            return {
                'symbol': symbol,
                'open': float(today['Open']),
                'high': float(today['High']),
                'low': float(today['Low']),
                'prev_close': float(yesterday['Close']),
                'close': float(today['Close'])
            }
        else:
            return {'error': f'No data available for {symbol}'}

    except Exception as e:
        return {'error': f'Failed to fetch stock data: {str(e)}'}

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

def calculate_total_portfolio_value(user_id):
    """Calculate the total value of a user's portfolio including cash."""
    try:
        # Get user's cash balance
        user = db.collection('users').document(user_id).get().to_dict()
        cash_balance = user.get('balance', 0) if user else 0
        
        # Get all portfolio items
        portfolio_items = db.collection('portfolios').where('user_id', '==', user_id).stream()
        
        total_value = cash_balance
        invested_value = 0
        active_positions = 0
        
        # Calculate value of each position
        for item in portfolio_items:
            active_positions += 1
            item_data = item.to_dict()
            symbol = item_data['symbol']
            shares = item_data['shares']
            
            # Get current price
            if item_data['asset_type'] == 'stock':
                price_data = fetch_stock_data(symbol)
                if price_data and 'close' in price_data:
                    current_price = price_data['close']
                else:
                    current_price = item_data.get('purchase_price', 0)
            else:  # crypto
                price_data = fetch_crypto_data(symbol)
                if price_data and 'price' in price_data:
                    current_price = price_data['price']
                else:
                    current_price = item_data.get('purchase_price', 0)
            
            position_value = shares * current_price
            invested_value += position_value
            total_value += position_value
        
        return {
            'total_value': total_value,
            'invested_value': invested_value,
            'available_cash': cash_balance,
            'active_positions': active_positions
        }
    except Exception as e:
        print(f"Error calculating portfolio value: {e}")
        return {
            'total_value': 0,
            'invested_value': 0,
            'available_cash': 0,
            'active_positions': 0
        }

def calculate_price_change(current, previous):
    """Calculate percentage change and format as string."""
    if previous <= 0:
        return 0, "0.00%"
        
    change_pct = ((current - previous) / previous) * 100
    change_str = f"{'+' if change_pct > 0 else ''}{change_pct:.2f}%"
    
    return change_pct, change_str

def fetch_user_portfolio(user_id):
    """Fetch the current user's portfolio data including performance metrics."""
    try:
        # Get all portfolio items for the user
        portfolio_items = db.collection('portfolios').where('user_id', '==', user_id).stream()

        # Initialize portfolio metrics
        total_value = 0.0
        invested_value = 0.0
        total_profit_loss = 0.0
        active_positions = 0
        day_change = 0.0
        winning_trades = 0
        total_trades = 0

        # Get the user's transaction history
        transactions = db.collection('transactions').where('user_id', '==', user_id).stream()
        transaction_list = list(transactions)
        total_trades = len(transaction_list)
        if total_trades > 0:
            winning_trades = sum(1 for t in transaction_list if t.to_dict().get('profit_loss', 0) > 0)

        # Analyze portfolio
        for item in portfolio_items:
            active_positions += 1
            item_data = item.to_dict()
            symbol = item_data['symbol']
            shares = item_data['shares']
            purchase_price = item_data.get('purchase_price', 0)
            
            # Get current price
            if item_data['asset_type'] == 'stock':
                price_data = fetch_stock_data(symbol)
                if price_data and 'close' in price_data:
                    current_price = price_data['close']
                    prev_price = price_data.get('prev_close', current_price)
                else:
                    current_price = purchase_price
                    prev_price = purchase_price
            else:  # crypto
                price_data = fetch_crypto_data(symbol)
                if price_data and 'price' in price_data:
                    current_price = price_data['price']
                    prev_price = price_data.get('prev_close', current_price)
                else:
                    current_price = purchase_price
                    prev_price = purchase_price
            
            # Calculate values
            position_value = shares * current_price
            position_cost = shares * purchase_price
            position_pl = position_value - position_cost
            position_day_change = shares * (current_price - prev_price)
            
            # Update totals
            total_value += position_value
            invested_value += position_value
            total_profit_loss += position_pl
            day_change += position_day_change

        # Get user's cash balance
        user = db.collection('users').document(user_id).get().to_dict()
        cash_balance = user.get('balance', 0) if user else 0
        
        # Add cash to total value
        total_value += cash_balance
        
        # Calculate win rate
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # Return portfolio summary data
        return {
            'Total Assets': f'${total_value:.2f}',
            'Cash Balance': f'${cash_balance:.2f}',
            'Invested Value': f'${invested_value:.2f}',
            'Total P/L': f"{'+'if total_profit_loss >= 0 else ''}{total_profit_loss:.2f} ({total_profit_loss/invested_value*100:.1f}%)" if invested_value > 0 else '$0.00',
            "Today's P/L": f"{'+'if day_change >= 0 else ''}{day_change:.2f}" if day_change != 0 else '$0.00',
            'Active Positions': active_positions,
            'Win Rate': f"{win_rate:.1f}%",
            'total_value': total_value,
            'invested_value': invested_value,
            'available_cash': cash_balance
        }
    except Exception as e:
        print(f"Error fetching portfolio: {e}")
        return {
            'Total Assets': '$0.00',
            'Cash Balance': '$0.00',
            'Invested Value': '$0.00',
            'Total P/L': '$0.00',
            "Today's P/L": '$0.00',
            'Active Positions': 0,
            'Win Rate': '0.0%',
            'total_value': 0,
            'invested_value': 0,
            'available_cash': 0
        }

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

