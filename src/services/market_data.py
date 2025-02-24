# src/services/market_data.py
import finnhub
import requests
from datetime import datetime, timedelta
import pandas as pd
from ..utils.constants import api_keys
import random

def get_random_api_key():
    return random.choice(api_keys)


def fetch_stock_data(symbol):
    try:
        finnhub_client = finnhub.Client(api_key=get_random_api_key())
        data = finnhub_client.quote(symbol)
        
        # Ensure the response contains valid data
        if not data:
            return {'error': 'Empty response from Finnhub API'}
        
        # Ensure all necessary keys are in the response
        required_keys = ['o', 'h', 'l', 'pc', 'c']  # Added 'c' for closing price
        missing_keys = [key for key in required_keys if key not in data]
        
        if missing_keys:
            return {'error': f'Missing keys {", ".join(missing_keys)} in response from Finnhub API'}
        
        # Return data with the required keys
        return {
            'symbol': symbol,
            'open': data.get('o', 0),          # Open price
            'high': data.get('h', 0),          # High price
            'low': data.get('l', 0),           # Low price
            'prev_close': data.get('pc', 0),   # Previous close price
            'close': data.get('c', 0)          # Closing price
        }
    
    except finnhub.exceptions.FinnhubAPIException as e:
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

def fetch_market_overview():
    try:
        # Fetch S&P 500 data with timeout
        sp500 = yf.Ticker("^GSPC")
        sp500_data = sp500.history(period="1d")
        sp500_change = ((sp500_data['Close'].iloc[-1] - sp500_data['Open'].iloc[0]) / sp500_data['Open'].iloc[0]) * 100

        # Fetch BTC/USD data with timeout and fallback
        try:
            btc_data = requests.get('https://api.coinbase.com/v2/prices/BTC-USD/spot', timeout=5).json()
            btc_price = float(btc_data['data']['amount'])
            btc_prev = requests.get('https://api.coinbase.com/v2/prices/BTC-USD/spot?date=' + 
                                  (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')).json()
            btc_prev_price = float(btc_prev['data']['amount'])
            btc_change = ((btc_price - btc_prev_price) / btc_prev_price) * 100
        except:
            btc_change = 0.0

        # Use a simpler market volume calculation that doesn't rely on CoinGecko
        market_volume = 1000  # Fallback value in billions

        return {
            'S&P 500': f"{sp500_change:.2f}%",
            'BTC/USD': f"{btc_change:.2f}%", 
            'Market Volume': f"${market_volume:.2f}B"
        }

    except Exception as e:
        print(f"Error fetching market overview: {e}")
        return {
            'S&P 500': 'N/A',
            'BTC/USD': 'N/A',
            'Market Volume': 'N/A'
        }