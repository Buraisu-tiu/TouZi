# src/utils/constants.py
# API Keys and Configuration
api_keys = [
    'ctitlv1r01qgfbsvh1dgctitlv1r01qgfbsvh1e0',
    'ctitnthr01qgfbsvh59gctitnthr01qgfbsvh5a0',
    'ctjgjm1r01quipmu2qi0ctjgjm1r01quipmu2qig'
]

ALPHA_VANTAGE_API_KEY = 'LL623C2ZURDROHZS'

ALLOWED_FILE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

POPULAR_STOCKS = [
        {'symbol': 'AAPL', 'name': 'Apple Inc.'},
        {'symbol': 'MSFT', 'name': 'Microsoft Corporation'},
        {'symbol': 'GOOGL', 'name': 'Alphabet Inc.'},
        {'symbol': 'AMZN', 'name': 'Amazon.com Inc.'},
        {'symbol': 'NVDA', 'name': 'NVIDIA Corporation'},
        {'symbol': 'META', 'name': 'Meta Platforms Inc.'},
        {'symbol': 'BRK.B', 'name': 'Berkshire Hathaway Inc.'},
        {'symbol': 'TSLA', 'name': 'Tesla Inc.'},
        {'symbol': 'JPM', 'name': 'JPMorgan Chase & Co.'},
        {'symbol': 'V', 'name': 'Visa Inc.'},
        {'symbol': 'JNJ', 'name': 'Johnson & Johnson'},
        {'symbol': 'WMT', 'name': 'Walmart Inc.'},
        {'symbol': 'MA', 'name': 'Mastercard Incorporated'},
        {'symbol': 'PG', 'name': 'Procter & Gamble Company'},
        {'symbol': 'HD', 'name': 'Home Depot Inc.'},
        {'symbol': 'BAC', 'name': 'Bank of America Corporation'},
        {'symbol': 'DIS', 'name': 'Walt Disney Company'},
        {'symbol': 'ADBE', 'name': 'Adobe Inc.'},
        {'symbol': 'NFLX', 'name': 'Netflix Inc.'},
        {'symbol': 'CRM', 'name': 'Salesforce Inc.'},
        {'symbol': 'CSCO', 'name': 'Cisco Systems Inc.'},
        {'symbol': 'PFE', 'name': 'Pfizer Inc.'},
        {'symbol': 'CMCSA', 'name': 'Comcast Corporation'},
        {'symbol': 'INTC', 'name': 'Intel Corporation'},
        {'symbol': 'VZ', 'name': 'Verizon Communications'},
        {'symbol': 'ABT', 'name': 'Abbott Laboratories'},
        {'symbol': 'PEP', 'name': 'PepsiCo Inc.'},
        {'symbol': 'KO', 'name': 'Coca-Cola Company'},
        {'symbol': 'MRK', 'name': 'Merck & Co.'},
        {'symbol': 'AMD', 'name': 'Advanced Micro Devices'},
        {'symbol': 'PYPL', 'name': 'PayPal Holdings Inc.'},
        {'symbol': 'TMO', 'name': 'Thermo Fisher Scientific'},
        {'symbol': 'COST', 'name': 'Costco Wholesale'},
        {'symbol': 'DHR', 'name': 'Danaher Corporation'},
        {'symbol': 'ACN', 'name': 'Accenture plc'},
        {'symbol': 'UNH', 'name': 'UnitedHealth Group'},
        {'symbol': 'NKE', 'name': 'Nike Inc.'},
        {'symbol': 'TXN', 'name': 'Texas Instruments'},
        {'symbol': 'NEE', 'name': 'NextEra Energy'},
        {'symbol': 'LLY', 'name': 'Eli Lilly and Company'},
        {'symbol': 'QCOM', 'name': 'Qualcomm Inc.'},
        {'symbol': 'MDT', 'name': 'Medtronic plc'},
        {'symbol': 'RTX', 'name': 'Raytheon Technologies'},
        {'symbol': 'AMGN', 'name': 'Amgen Inc.'},
        {'symbol': 'CVX', 'name': 'Chevron Corporation'},
        {'symbol': 'XOM', 'name': 'Exxon Mobil Corporation'},
        {'symbol': 'SBUX', 'name': 'Starbucks Corporation'},
        {'symbol': 'BMY', 'name': 'Bristol-Myers Squibb'},
        {'symbol': 'UPS', 'name': 'United Parcel Service'},
        {'symbol': 'CAT', 'name': 'Caterpillar Inc.'}
    ]

ACHIEVEMENTS = {
    'first_trade': {
        'name': 'First Trade',
        'description': 'Complete your first trade',
        'icon': '🌟'
    },
    'big_spender': {
        'name': 'Big Spender',
        'description': 'Complete a trade worth over $10,000',
        'icon': '💰'
    },
    'day_trader': {
        'name': 'Day Trader',
        'description': 'Complete 5 trades in one day',
        'icon': '📈'
    },
    'diversified': {
        'name': 'Diversified',
        'description': 'Own 5 different stocks simultaneously',
        'icon': '🎯'
    }
}

# Trading limits
DAILY_TRANSACTION_LIMIT = 10
MIN_TRANSACTION_AMOUNT = 1.00
MAX_TRANSACTION_AMOUNT = 1000000.00
TRADING_FEE_PERCENTAGE = 0.001  # 0.1%