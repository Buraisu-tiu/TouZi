# Stock Trading Simulator Constants 

# API Key storage for load balancing and retry mechanisms
api_keys = []

def reset_api_keys():
    """Reset the API keys - useful for testing and when keys are refreshed"""
    global api_keys
    api_keys = []
    
    # Try to load from api_keys.py file
    try:
        import api_keys as api_keys_file
        if hasattr(api_keys_file, 'FINNHUB_API_KEYS'):
            for key in api_keys_file.FINNHUB_API_KEYS:
                if key and key not in api_keys:
                    api_keys.append(key)
            print(f"Reset loaded {len(api_keys)} Finnhub API keys")
    except ImportError:
        # api_keys.py doesn't exist
        pass
        
    # Check for environment variable as backup
    import os
    finnhub_key = os.environ.get('FINNHUB_API_KEY')
    if finnhub_key and finnhub_key not in api_keys:
        api_keys.append(finnhub_key)

# Standard Stock Market Indices
MARKET_INDICES = {
    '^GSPC': 'S&P 500',
    '^DJI': 'Dow Jones Industrial Average',
    '^IXIC': 'NASDAQ Composite',
    '^RUT': 'Russell 2000'
}

# Popular stocks for basic displays and examples
POPULAR_STOCKS = [
    {"symbol": "AAPL", "name": "Apple Inc."},
    {"symbol": "MSFT", "name": "Microsoft Corporation"},
    {"symbol": "AMZN", "name": "Amazon.com Inc."},
    {"symbol": "GOOGL", "name": "Alphabet Inc."},
    {"symbol": "META", "name": "Meta Platforms, Inc."},
    {"symbol": "TSLA", "name": "Tesla, Inc."},
    {"symbol": "NVDA", "name": "NVIDIA Corporation"},
    {"symbol": "BRK-B", "name": "Berkshire Hathaway Inc."},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co."},
    {"symbol": "JNJ", "name": "Johnson & Johnson"},
    {"symbol": "V", "name": "Visa Inc."},
    {"symbol": "PG", "name": "Procter & Gamble Co."},
    {"symbol": "UNH", "name": "UnitedHealth Group Inc."},
    {"symbol": "HD", "name": "Home Depot Inc."},
    {"symbol": "BAC", "name": "Bank of America Corp."},
    {"symbol": "MA", "name": "Mastercard Inc."},
    {"symbol": "DIS", "name": "Walt Disney Co."},
    {"symbol": "NFLX", "name": "Netflix, Inc."},
    {"symbol": "INTC", "name": "Intel Corporation"},
    {"symbol": "VZ", "name": "Verizon Communications Inc."},
    {"symbol": "ADBE", "name": "Adobe Inc."},
    {"symbol": "CSCO", "name": "Cisco Systems, Inc."},
    {"symbol": "CRM", "name": "Salesforce, Inc."},
    {"symbol": "PFE", "name": "Pfizer Inc."},
    {"symbol": "WMT", "name": "Walmart Inc."}
]

# API Rate Limits
FINNHUB_RATE_LIMIT = {
    'calls_per_minute': 30,
    'window_size': 60,  # seconds
    'cooldown_period': 60  # seconds after rate limit
}

ALPHA_VANTAGE_RATE_LIMIT = {
    'calls_per_minute': 5,
    'window_size': 60,
    'cooldown_period': 60
}

YFINANCE_RATE_LIMIT = {
    'calls_per_minute': 2000,  # More lenient but should still be careful
    'window_size': 3600,  # 1 hour
    'cooldown_period': 300  # 5 minutes
}

# Portfolio and Trading Constants
MAX_TRADE_QUANTITY = 10000  # Maximum number of shares/units in a single trade
TRADING_FEE_RATE = 0.001    # Trading fee as a decimal (0.1%)
INITIAL_BALANCE = 10000     # Starting balance for new users

# Default user settings
DEFAULT_USER_SETTINGS = {
    "theme": "light",
    "notifications": True,
    "currency": "USD",
    "language": "en",
    "show_tutorial": True,
    "home_page": "dashboard",
    "date_format": "MM/DD/YYYY",
    "time_format": "24h",
    "stock_price_alert": 5.0,
    "portfolio_diversification_alert": True,
    "trade_execution_confirmation": True,
    "api_key_status": "active",
    "last_login": None,
    "watchlist": [],
    "trading_strategy": "long_term",
    "risk_tolerance": "medium",
    "investment_goals": "growth",
    "account_type": "individual",
    "leverage_enabled": False,
    "screener_filters": {},
    "order_history": [],
    "trade_notes": {},
    "referral_code_used": False,
    "achievements": []
}