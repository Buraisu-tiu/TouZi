# src/utils/constants.py
# API Keys and Configuration
api_keys = [
    "c5vl9l2ad3ifgl126ddg",  # Finnhub
    "c5vl9l2ad3ifgl126ddg2", # Additional key
]

ALPHA_VANTAGE_API_KEY = 'LL623C2ZURDROHZS'

ALLOWED_FILE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Popular stocks for quick access
POPULAR_STOCKS = [
    {"symbol": "AAPL", "name": "Apple Inc."},
    {"symbol": "MSFT", "name": "Microsoft Corporation"},
    {"symbol": "GOOGL", "name": "Alphabet Inc."},
    {"symbol": "AMZN", "name": "Amazon.com, Inc."},
    {"symbol": "META", "name": "Meta Platforms, Inc."},
    {"symbol": "TSLA", "name": "Tesla, Inc."},
    {"symbol": "NVDA", "name": "NVIDIA Corporation"},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co."},
    {"symbol": "V", "name": "Visa Inc."},
    {"symbol": "JNJ", "name": "Johnson & Johnson"}
]

# Achievement badges and their descriptions
ACHIEVEMENTS = {
    # ===== BEGINNER BADGES (EASY TO EARN) =====
    "first_login": {
        "name": "Welcome Aboard", 
        "description": "Log in for the first time", 
        "icon": "👋",
        "difficulty": "easy"
    },
    "first_trade": {
        "name": "First Steps", 
        "description": "Complete your first trade", 
        "icon": "🚀",
        "difficulty": "easy"
    },
    "first_stock": {
        "name": "Stock Picker", 
        "description": "Buy your first stock", 
        "icon": "📈",
        "difficulty": "easy"
    },
    "first_crypto": {
        "name": "Crypto Curious", 
        "description": "Buy your first cryptocurrency", 
        "icon": "💰",
        "difficulty": "easy"
    },
    "first_profit": {
        "name": "In The Green", 
        "description": "Make your first profitable trade", 
        "icon": "💵",
        "difficulty": "easy"
    },
    "profile_setup": {
        "name": "Identity Established", 
        "description": "Complete your profile settings", 
        "icon": "👤",
        "difficulty": "easy"
    },
    "first_watchlist": {
        "name": "Market Observer", 
        "description": "Add your first item to watchlist", 
        "icon": "👁️",
        "difficulty": "easy"
    },
    "theme_change": {
        "name": "Personal Touch", 
        "description": "Change your theme or accent color", 
        "icon": "🎨",
        "difficulty": "easy"
    },
    
    # ===== INTERMEDIATE BADGES =====
    "five_trades": {
        "name": "Getting Started", 
        "description": "Complete 5 trades", 
        "icon": "🔄",
        "difficulty": "medium"
    },
    "ten_trades": {
        "name": "Regular Trader", 
        "description": "Complete 10 trades", 
        "icon": "🔁",
        "difficulty": "medium"
    },
    "portfolio_1k": {
        "name": "First Grand", 
        "description": "Reach $1,000 in portfolio value", 
        "icon": "💲",
        "difficulty": "medium"
    },
    "small_profit": {
        "name": "Small Victory", 
        "description": "Make a $100 profit on a single trade", 
        "icon": "💸",
        "difficulty": "medium"
    },
    "diversified": {
        "name": "Diversifier", 
        "description": "Own 3 different stocks or cryptos simultaneously", 
        "icon": "📊",
        "difficulty": "medium"
    },
    "day_trader": {
        "name": "Day Trader", 
        "description": "Make 3 trades in a single day", 
        "icon": "⏱️",
        "difficulty": "medium"
    },
    "learn_basics": {
        "name": "Market Student", 
        "description": "Visit the documentation section", 
        "icon": "📚",
        "difficulty": "medium"
    },
    "one_week": {
        "name": "Week One Done", 
        "description": "Log in for 7 consecutive days", 
        "icon": "📅",
        "difficulty": "medium"
    },

    # ===== ADVANCED BADGES =====
    "portfolio_10k": {
        "name": "Market Maven", 
        "description": "Reach $10,000 in portfolio value", 
        "icon": "📈",
        "difficulty": "hard"
    },
    "portfolio_100k": {
        "name": "Wall Street Whale", 
        "description": "Reach $100,000 in portfolio value", 
        "icon": "🐳",
        "difficulty": "hard"
    },
    "portfolio_1m": {
        "name": "Trading Tycoon", 
        "description": "Reach $1,000,000 in portfolio value", 
        "icon": "👑",
        "difficulty": "very hard"
    },
    "big_spender": {
        "name": "Big Spender", 
        "description": "Make a single trade worth over $10,000", 
        "icon": "💰",
        "difficulty": "hard"
    },
    "consistent_profits": {
        "name": "Consistent Performer", 
        "description": "Make profit on 5 consecutive trades", 
        "icon": "📊",
        "difficulty": "hard"
    },
    "investment_guru": {
        "name": "Investment Guru", 
        "description": "Achieve 50% return on investment", 
        "icon": "🧠",
        "difficulty": "hard"
    },
    "well_diversified": {
        "name": "Portfolio Master", 
        "description": "Own 10 different assets simultaneously", 
        "icon": "🔱",
        "difficulty": "hard"
    },
    
    # ===== VOLUME TRADER BADGES =====
    "trading_addict": {
        "name": "Trading Addict", 
        "description": "Complete 50 trades in a single day", 
        "icon": "🔥",
        "difficulty": "very hard"
    },
    "volume_king": {
        "name": "Volume King", 
        "description": "Complete 100 trades in a single day", 
        "icon": "👑",
        "difficulty": "very hard"
    },
    "century_club": {
        "name": "Century Club", 
        "description": "Complete 100 total trades", 
        "icon": "🏆",
        "difficulty": "hard"
    },
    "trading_legend": {
        "name": "Trading Legend", 
        "description": "Complete 1000 total trades", 
        "icon": "🌟",
        "difficulty": "very hard"
    },
    
    # ===== PROFIT HUNTER BADGES =====
    "profit_hunter": {
        "name": "Profit Hunter", 
        "description": "Make a single trade with 20% profit", 
        "icon": "🎯",
        "difficulty": "hard"
    },
    "golden_touch": {
        "name": "Golden Touch", 
        "description": "Make a single trade with 50% profit", 
        "icon": "🏅",
        "difficulty": "hard"
    },
    "legendary_trader": {
        "name": "Legendary Trader", 
        "description": "Make a single trade with 100% profit", 
        "icon": "🌠",
        "difficulty": "very hard"
    },
    
    # ===== CRYPTO SPECIFIC BADGES =====
    "crypto_enthusiast": {
        "name": "Crypto Enthusiast", 
        "description": "Own 5 different cryptocurrencies", 
        "icon": "🪙",
        "difficulty": "medium"
    },
    "crypto_whale": {
        "name": "Crypto Whale", 
        "description": "Have $50,000 in cryptocurrency holdings", 
        "icon": "🐋",
        "difficulty": "hard"
    },
    "bitcoin_maximalist": {
        "name": "Bitcoin Maximalist", 
        "description": "Hold at least 1 whole Bitcoin", 
        "icon": "₿",
        "difficulty": "very hard"
    },
    
    # ===== RISK TAKER BADGES =====
    "risk_taker": {
        "name": "Risk Taker", 
        "description": "Invest 50% of your portfolio in a single asset", 
        "icon": "🎲",
        "difficulty": "medium" 
    },
    "all_in": {
        "name": "All or Nothing", 
        "description": "Invest 90% of your portfolio in a single asset", 
        "icon": "💣",
        "difficulty": "hard"
    },
    "diamond_hands": {
        "name": "Diamond Hands", 
        "description": "Hold a losing position for over 7 days", 
        "icon": "💎",
        "difficulty": "medium"
    },
    
    # ===== SPECIAL ACHIEVEMENT BADGES =====
    "perfect_timing": {
        "name": "Perfect Timing", 
        "description": "Buy at daily low and sell at daily high", 
        "icon": "⏰",
        "difficulty": "very hard"
    },
    "comeback_kid": {
        "name": "Comeback Kid", 
        "description": "Recover from a 50% portfolio loss", 
        "icon": "🔄",
        "difficulty": "hard"
    },
    "market_oracle": {
        "name": "Market Oracle", 
        "description": "Predict market movements correctly 3 times", 
        "icon": "🔮",
        "difficulty": "hard"
    },
    
    # ===== EDUCATIONAL BADGES =====
    "chart_analyst": {
        "name": "Chart Analyst", 
        "description": "Use technical analysis tools 10 times", 
        "icon": "📊",
        "difficulty": "medium"
    },
    "market_researcher": {
        "name": "Market Researcher", 
        "description": "Look up 20 different stocks", 
        "icon": "🔍",
        "difficulty": "medium"
    },
    "documentation_master": {
        "name": "Documentation Master", 
        "description": "Read all documentation sections", 
        "icon": "📘",
        "difficulty": "medium"
    },

    # ===== HUMOROUS BADGES =====
    "tuition_paid": {
        "name": "Tuition Paid", 
        "description": "Lose money on your first trade", 
        "icon": "🎓",
        "difficulty": "easy"
    },
    "buy_high_sell_low": {
        "name": "Buy High, Sell Low", 
        "description": "Lose 20% on a single trade", 
        "icon": "📉",
        "difficulty": "easy"
    },
    "portfolio_reset": {
        "name": "Portfolio Reset", 
        "description": "Lose 90% of your portfolio value", 
        "icon": "🗑️",
        "difficulty": "hard"
    },
    
    # ===== TIME-BASED BADGES =====
    "early_bird": {
        "name": "Early Bird", 
        "description": "Make a trade within the first hour of market open", 
        "icon": "🐦",
        "difficulty": "medium"
    },
    "night_owl": {
        "name": "Night Owl", 
        "description": "Make a trade in the last hour before market close", 
        "icon": "🦉",
        "difficulty": "medium"
    },
    "weekend_warrior": {
        "name": "Weekend Warrior", 
        "description": "Place orders during weekend market closure", 
        "icon": "📆",
        "difficulty": "easy"
    },
    "long_term_investor": {
        "name": "Long Term Investor", 
        "description": "Hold a profitable position for over 30 days", 
        "icon": "🧓",
        "difficulty": "medium"
    },
    
    # ===== STREAK BADGES =====
    "hot_streak": {
        "name": "Hot Streak", 
        "description": "Make profit on 3 trades in a row", 
        "icon": "🔥",
        "difficulty": "medium"
    },
    "unstoppable": {
        "name": "Unstoppable", 
        "description": "Make profit on 7 trades in a row", 
        "icon": "⚡",
        "difficulty": "hard"
    },
    "legendary_streak": {
        "name": "Legendary Streak", 
        "description": "Make profit on 10 trades in a row", 
        "icon": "🌈",
        "difficulty": "very hard"
    },
    
    # ===== EXACT AMOUNT BADGES (FOR FUN) =====
    "exact_10k": {
        "name": "Perfect 10K", 
        "description": "Have exactly $10,000 in account balance", 
        "icon": "🎯",
        "difficulty": "medium"
    },
    "exact_100k": {
        "name": "Perfect 100K", 
        "description": "Have exactly $100,000 in account balance", 
        "icon": "🎯",
        "difficulty": "hard"
    },
    "exact_1m": {
        "name": "Perfect Million", 
        "description": "Have exactly $1,000,000 in account balance", 
        "icon": "🎯",
        "difficulty": "very hard"
    },
    
    # ===== SOCIAL BADGES =====
    "friend_referral": {
        "name": "Influencer", 
        "description": "Refer a friend to the platform", 
        "icon": "👥",
        "difficulty": "medium"
    },
    "leaderboard_entry": {
        "name": "On The Board", 
        "description": "Appear on the leaderboard", 
        "icon": "📋",
        "difficulty": "hard"
    },
    "top_10": {
        "name": "Top 10 Trader", 
        "description": "Reach the top 10 on the leaderboard", 
        "icon": "🔝",
        "difficulty": "very hard"
    },
    "number_one": {
        "name": "Number One", 
        "description": "Reach the #1 position on the leaderboard", 
        "icon": "🥇",
        "difficulty": "very hard"
    }
}

# Trading limits
DAILY_TRANSACTION_LIMIT = 10
MIN_TRANSACTION_AMOUNT = 1.00
MAX_TRANSACTION_AMOUNT = 1000000.00
TRADING_FEE_PERCENTAGE = 0.001  # 0.1%

# Market indices for reference
MARKET_INDICES = {
    'SPY': 'S&P 500',
    'DIA': 'Dow Jones Industrial Average',
    'QQQ': 'Nasdaq 100',
    'IWM': 'Russell 2000'
}