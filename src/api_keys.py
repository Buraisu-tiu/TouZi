"""
LOCAL API KEYS FILE

This file stores API keys for local development.
DO NOT commit this file to version control!
Add this file to .gitignore
"""

# Finnhub API keys
FINNHUB_API_KEYS = [
    'd0rigqhr01qumepee8ogd0rigqhr01qumepee8p0', 'd0rihf9r01qumepeecb0d0rihf9r01qumepeecbg'
]

# Single key reference for backward compatibility
FINNHUB_API_KEY = FINNHUB_API_KEYS[0] if FINNHUB_API_KEYS else None

# Alpha Vantage API key (if you have one)
ALPHA_VANTAGE_KEY = None
