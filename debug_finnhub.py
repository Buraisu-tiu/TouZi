"""
Debug script to verify Finnhub API keys.
Run this script directly to test if your Finnhub API keys are working.
"""

import requests
import time
import sys
import os

# Add src to path to be able to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_finnhub_api():
    print("\n===== FINNHUB API KEY TEST =====")
    
    # First try to load from api_keys.py
    try:
        from src import api_keys as api_keys_file
        if hasattr(api_keys_file, 'FINNHUB_API_KEYS'):
            keys = api_keys_file.FINNHUB_API_KEYS
            print(f"Loaded {len(keys)} keys from api_keys.py")
            
            for i, key in enumerate(keys):
                print(f"\nTesting key #{i+1}: {key[:4]}...{key[-4:]}")
                test_result = test_single_key(key)
                if test_result['success']:
                    print(f"✅ Key #{i+1} working! Symbol: {test_result['symbol']}, Price: ${test_result['price']}")
                else:
                    print(f"❌ Key #{i+1} failed: {test_result['error']}")
        else:
            print("❌ No Finnhub API keys found in api_keys.py")
    except ImportError:
        print("❌ api_keys.py file not found")
        
    # Try environment variable as backup
    env_key = os.environ.get('FINNHUB_API_KEY')
    if env_key:
        print("\nTesting API key from environment variable")
        test_result = test_single_key(env_key)
        if test_result['success']:
            print(f"✅ Environment key working! Symbol: {test_result['symbol']}, Price: ${test_result['price']}")
        else:
            print(f"❌ Environment key failed: {test_result['error']}")
    else:
        print("\n❌ No Finnhub API key found in environment variables")

def test_single_key(api_key):
    """Test a single Finnhub API key with the quote endpoint"""
    symbol = 'AAPL'  # Test with Apple stock
    url = f'https://finnhub.io/api/v1/quote'
    params = {
        'symbol': symbol,
        'token': api_key
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            if 'c' in data:  # 'c' is current price in Finnhub API
                return {
                    'success': True,
                    'symbol': symbol,
                    'price': data['c']
                }
            else:
                return {
                    'success': False,
                    'error': f"Invalid data format: {data}"
                }
        else:
            return {
                'success': False,
                'error': f"API returned status {response.status_code}: {response.text}"
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    test_finnhub_api()
