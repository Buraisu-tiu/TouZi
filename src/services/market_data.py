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
from flask_caching import Cache


cache = Cache(config={'CACHE_TYPE': 'redis'})

def get_random_api_key():
    key = random.choice(api_keys)  # Ensure API_KEYS is a valid list
    print(f"Using API Key: {key}")  # Debugging
    return key

def fetch_stock_data(symbol):
    try:
        api_key = get_random_api_key()
        print(f"Using API Key: {api_key}")  

        finnhub_client = finnhub.Client(api_key=api_key)
        data = finnhub_client.quote(symbol)
        print(f"Raw API Response for {symbol}: {data}")  

        # Ensure the response is a dictionary
        if not isinstance(data, dict):
            return {'error': f'Invalid API response format for {symbol}. Data: {data}'}

        # Check if key 'c' (current price) exists
        if 'c' not in data:
            return {'error': f'API response missing key "c" for {symbol}. Data: {data}'}

        # Return structured stock data
        return {
            'symbol': symbol,
            'open': data.get('o', 0),
            'high': data.get('h', 0),
            'low': data.get('l', 0),
            'prev_close': data.get('pc', 0),
            'close': data.get('c', 0)
        }

    except finnhub.FinnhubAPIException as e:
        return {'error': f'Finnhub API error: {str(e)}'}
    except Exception as e:
        return {'error': f'Error fetching stock data: {str(e)}'}




        
def fetch_crypto_data(symbol):
    try:
        print(f"DEBUG: Requesting crypto price for {symbol}")  # Debugging
        response = requests.get(f'https://api.coinbase.com/v2/prices/{symbol}-USD/spot')
        response.raise_for_status()
        data = response.json()
        
        if 'data' not in data or 'amount' not in data['data']:
            print(f"ERROR: Unexpected response structure {data}")  # Debugging
            return {'error': 'Invalid response from crypto API'}
        
        price = round(float(data['data']['amount']), 2)
        print(f"DEBUG: Fetched crypto price: {price}")  # Debugging
        return {'price': price}
    
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Request failed - {str(e)}")  # Debugging
        return {'error': f'Failed to fetch crypto price: {str(e)}'}


def fetch_historical_data(symbol):
    try:
        # Initialize the Finnhub client with a random API key
        finnhub_client = finnhub.Client(api_key=get_random_api_key())
        
        # Define the time range for the historical data
        end_date = int(datetime.now().timestamp())
        start_date = int((datetime.now() - timedelta(days=30)).timestamp())
        
        print(f"Fetching historical data for symbol: {symbol} from {start_date} to {end_date}")
        
        # Make the API call to fetch stock candles
        res = finnhub_client.stock_candles(symbol, 'D', start_date, end_date)
        
        # Print the raw response from the API
        print(f"Response from Finnhub for {symbol}: {res}")
        
        # Check if the response indicates success
        if res['s'] == 'ok':
            # Create a DataFrame from the response
            df = pd.DataFrame(res)
            df['t'] = pd.to_datetime(df['t'], unit='s')
            df.set_index('t', inplace=True)
            df = df.rename(columns={'c': 'close'})
            print(f"Successfully fetched historical data for {symbol}")
            return df
        else:
            print(f"Failed to fetch historical data for {symbol}: {res.get('s', 'unknown error')}")
            return None
    except Exception as e:
        print(f"An error occurred while fetching historical data for {symbol}: {str(e)}")
        return None
    

def fetch_user_portfolio(user_id):
    user_ref = db.collection('users').document(user_id)
    user = user_ref.get().to_dict()
    portfolio_query = db.collection('portfolios').where('user_id', '==', user_id).stream()
    
    total_value = user['balance']
    previous_day_value = user['balance']  # Start with the balance for previous day's value
    for item in portfolio_query:
        item_data = item.to_dict()
        if item_data['asset_type'] == 'stock':
            price_data = fetch_stock_data(item_data['symbol'])
            if 'error' not in price_data:
                current_price = price_data['close']
                total_value += current_price * item_data['shares']
                
                # Fetch previous day's closing price
                previous_day_data = fetch_historical_data(item_data['symbol'])
                if previous_day_data is not None and not previous_day_data.empty:
                    previous_close = previous_day_data['close'].iloc[-1]  # Get the last closing price
                    previous_day_value += previous_close * item_data['shares']
        elif item_data['asset_type'] == 'crypto':
            price_data = fetch_crypto_data(item_data['symbol'])
            if 'error' not in price_data:
                current_price = price_data['price']
                total_value += current_price * item_data['shares']
                
                # Fetch previous day's closing price for crypto
                previous_day_data = fetch_historical_data(item_data['symbol'])
                if previous_day_data is not None and not previous_day_data.empty:
                    previous_close = previous_day_data['close'].iloc[-1]  # Get the last closing price
                    previous_day_value += previous_close * item_data['shares']

    # Calculate today's change
    todays_change = total_value - previous_day_value

    return {
        'Total Value': f'${total_value:.2f}',
        "Today's Change": f'${todays_change:.2f}',  # Format today's change
        'Available Cash': f'${user["balance"]:.2f}'
    }

def calculate_price_change(current: float, previous: float) -> tuple[float, str]:
    """
    Calculate price change and percentage safely.
    Returns: (percentage_change, formatted_change_string)
    """
    try:
        if previous <= 0:
            return (0.0, "N/A")
            
        change_percentage = ((current - previous) / previous) * 100
        change_str = f"{change_percentage:+.2f}%"
        return (change_percentage, change_str)
    except (TypeError, ZeroDivisionError):
        return (0.0, "N/A")

def fetch_recent_orders(user_id, limit=5):
    orders_query = db.collection('transactions').where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
    orders = []
    for order in orders_query.stream():
        order_data = order.to_dict()
        orders.append({
            'Date': order_data['timestamp'].strftime('%Y-%m-%d'),
            'Symbol': order_data['symbol'],
            'Type': order_data['asset_type'],
            'Quantity': order_data['shares'],
            'Status': 'Completed'  # You might want to add a status field to your transactions
        })
    return orders

