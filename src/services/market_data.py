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
        response.raise_for_status()
        data = response.json()
        
        if 'data' in data and 'amount' in data['data']:
            return {'price': round(float(data['data']['amount']), 2)}
        return {'error': 'Invalid response from crypto API'}
    
    except requests.exceptions.RequestException as e:
        return {'error': f'Failed to fetch crypto price: {str(e)}'}

def fetch_historical_data(symbol):
    """Fetch historical price data using yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period='1mo')
        
        if not df.empty:
            df = df.rename(columns={
                'Close': 'close',
                'High': 'high',
                'Low': 'low',
                'Open': 'open',
                'Volume': 'volume'
            })
            return df
        
        return None
    except Exception as e:
        return None

def calculate_total_portfolio_value(user_id):
    """Calculate total portfolio value and active positions."""
    try:
        user = db.collection('users').document(user_id).get().to_dict()
        total_value = user.get('balance', 0)
        active_positions = 0

        portfolio_items = db.collection('portfolios')\
            .where('user_id', '==', user_id)\
            .stream()

        for item in portfolio_items:
            item_data = item.to_dict()
            
            if item_data.get('shares', 0) > 0:
                active_positions += 1
                
                if item_data['asset_type'] == 'stock':
                    stock_data = fetch_stock_data(item_data['symbol'])
                    if stock_data and 'close' in stock_data:
                        total_value += stock_data['close'] * item_data['shares']
                elif item_data['asset_type'] == 'crypto':
                    crypto_data = fetch_crypto_data(item_data['symbol'])
                    if crypto_data and 'price' in crypto_data:
                        total_value += crypto_data['price'] * item_data['shares']

        return {
            'total_value': round(total_value, 2),
            'active_positions': active_positions,
            'available_cash': user.get('balance', 0),
            'invested_value': round(total_value - user.get('balance', 0), 2)
        }
    except Exception as e:
        return {
            'total_value': 0.0,
            'active_positions': 0,
            'available_cash': 0.0,
            'invested_value': 0.0
        }

def calculate_price_change(current, previous):
    """Calculate price change and percentage."""
    try:
        if previous <= 0:
            return 0.0, "N/A"
        change_percentage = ((current - previous) / previous) * 100
        return change_percentage, f"{change_percentage:+.2f}%"
    except (TypeError, ZeroDivisionError):
        return 0.0, "N/A"

def fetch_recent_orders(user_id, limit=5):
    """Fetch recent orders for a user."""
    orders_query = db.collection('transactions')\
        .where('user_id', '==', user_id)\
        .order_by('timestamp', direction=firestore.Query.DESCENDING)\
        .limit(limit)
    orders = []
    for order in orders_query.stream():
        order_data = order.to_dict()
        orders.append({
            'Date': order_data['timestamp'].strftime('%Y-%m-%d'),
            'Symbol': order_data['symbol'],
            'Type': order_data['asset_type'],
            'Quantity': order_data['shares'],
            'Status': 'Completed'
        })
    return orders

