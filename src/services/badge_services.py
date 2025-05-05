# src/services/badge_service.py
from utils.db import db
from datetime import datetime
from services.market_data import fetch_stock_data, fetch_crypto_data
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime, timedelta, timezone
from utils.constants import ACHIEVEMENTS
from firebase_admin import firestore

# Specify the time zone
tz = timezone.utc

# Get the current time in the specified time zone
now = datetime.now(tz)

def create_badges():
    badges = [
        # Achievement Badges
        {"name": "Market Maven", "description": "Achieve a total portfolio value of $10,000"},
        {"name": "Wall Street Whale", "description": "Achieve a total portfolio value of $100,000"},
        {"name": "Trading Tycoon", "description": "Achieve a total portfolio value of $1,000,000"},
        
        # Trading Volume Badges
        {"name": "Day Trader", "description": "Complete 10 trades in a single day"},
        {"name": "Trading Addict", "description": "Complete 50 trades in a single day"},
        {"name": "Volume King", "description": "Complete 100 trades in a single day"},
        
        # Profit Badges
        {"name": "Profit Hunter", "description": "Make a single trade with 20% profit"},
        {"name": "Golden Touch", "description": "Make a single trade with 50% profit"},
        {"name": "Legendary Trader", "description": "Make a single trade with 100% profit"},
        
        # Diversity Badges
        {"name": "Diversifier", "description": "Own 5 different stocks simultaneously"},
        {"name": "Portfolio Master", "description": "Own 10 different stocks simultaneously"},
        {"name": "Market Mogul", "description": "Own 20 different stocks simultaneously"},
        
        # Crypto Badges
        {"name": "Crypto Curious", "description": "Make your first cryptocurrency trade"},
        {"name": "Crypto Enthusiast", "description": "Own 5 different cryptocurrencies"},
        {"name": "Crypto Whale", "description": "Have $50,000 in cryptocurrency holdings"},
        
        # Risk Badges
        {"name": "Risk Taker", "description": "Invest 50% of your portfolio in a single asset"},
        {"name": "All or Nothing", "description": "Invest 90% of your portfolio in a single asset"},
        {"name": "Diamond Hands", "description": "Hold a losing position for over 7 days"},
        
        # Special Achievement Badges
        {"name": "Perfect Timing", "description": "Buy at daily low and sell at daily high"},
        {"name": "Comeback King", "description": "Recover from a 50% portfolio loss"},
        {"name": "Market Oracle", "description": "Make profit on 5 consecutive trades"},
        
        # Milestone Badges
        {"name": "First Steps", "description": "Complete your first trade"},
        {"name": "Century Club", "description": "Complete 100 total trades"},
        {"name": "Trading Legend", "description": "Complete 1000 total trades"},
        
        # Loss Badges (for humor and realism)
        {"name": "Tuition Paid", "description": "Lose money on your first trade"},
        {"name": "Buy High Sell Low", "description": "Lose 20% on a single trade"},
        {"name": "Portfolio Reset", "description": "Lose 90% of your portfolio value"},
        
        # Time-based Badges
        {"name": "Early Bird", "description": "Make a trade in the first minute of market open"},
        {"name": "Night Owl", "description": "Make a trade in the last minute before market close"},
        {"name": "Weekend Warrior", "description": "Place orders during weekend market closure"},
        
        # Streak Badges
        {"name": "Hot Streak", "description": "Make profit on 3 trades in a row"},
        {"name": "Unstoppable", "description": "Make profit on 7 trades in a row"},
        {"name": "Legendary Streak", "description": "Make profit on 10 trades in a row"},
        
        # Style Badges
        {"name": "Day Trader", "description": "Complete all trades within market hours"},
        {"name": "Swing Trader", "description": "Hold positions overnight"},
        {"name": "Position Trader", "description": "Hold positions for over 30 days"},
        
        # Portfolio Balance Badges
        {"name": "Exactly $10,000", "description": "Have exactly $10,000 in account balance"},
        {"name": "Exactly $100,000", "description": "Have exactly $100,000 in account balance"},
        {"name": "Exactly $1,000,000", "description": "Have exactly $1,000,000 in account balance"},
        
        # Market Condition Badges
        {"name": "Bull Runner", "description": "Make profit during a market uptrend"},
        {"name": "Bear Fighter", "description": "Make profit during a market downtrend"},
        {"name": "Volatility Surfer", "description": "Make profit during high market volatility"}
    ]
    
    badges_ref = db.collection('badges')
    for badge in badges:
        try:
            existing_badge_query = badges_ref.where('name', '==', badge['name']).limit(1).get()
            if not existing_badge_query:
                badges_ref.add(badge)
                print(f"Badge created: {badge['name']}")
            else:
                print(f"Badge already exists: {badge['name']}")
        except Exception as e:
            print(f"Error creating badge {badge['name']}: {str(e)}")


def check_and_award_badges(user_id):
    """Check user's progress and award badges if criteria are met."""
    
    # Check if user has already been awarded the badge
    awarded_badges = fetch_user_badges(user_id)
    awarded_badge_ids = [badge['badge_id'] for badge in awarded_badges]

    # First Trade Badge
    if 'first_trade' not in awarded_badge_ids and has_completed_first_trade(user_id):
        award_badge(user_id, 'first_trade')

    # Big Spender Badge
    if 'big_spender' not in awarded_badge_ids and has_spent_over_amount(user_id, 10000):
        award_badge(user_id, 'big_spender')

    # Day Trader Badge
    if 'day_trader' not in awarded_badge_ids and has_completed_trades_today(user_id, 5):
        award_badge(user_id, 'day_trader')

    # Diversified Badge
    if 'diversified' not in awarded_badge_ids and has_diversified_portfolio(user_id, 5):
        award_badge(user_id, 'diversified')

def has_completed_first_trade(user_id):
    """Check if the user has completed at least one trade."""
    transactions = db.collection('transactions').where('user_id', '==', user_id).limit(1).get()
    return len(transactions) > 0

def has_spent_over_amount(user_id, amount):
    """Check if the user has spent over a certain amount in a single trade."""
    transactions = db.collection('transactions')\
        .where('user_id', '==', user_id)\
        .where('total_amount', '>', amount)\
        .limit(1)\
        .get()
    return len(transactions) > 0

def has_completed_trades_today(user_id, num_trades):
    """Check if the user has completed a certain number of trades today."""
    today = datetime.utcnow().date()
    start_of_day = datetime(today.year, today.month, today.day)
    
    transactions = db.collection('transactions')\
        .where('user_id', '==', user_id)\
        .where('timestamp', '>=', start_of_day)\
        .get()
    return len(transactions) >= num_trades

def has_diversified_portfolio(user_id, num_stocks):
    """Check if the user has a diversified portfolio (owns a certain number of different stocks)."""
    portfolio_items = db.collection('portfolios').where('user_id', '==', user_id).get()
    unique_symbols = set()
    for item in portfolio_items:
        unique_symbols.add(item.to_dict()['symbol'])
    return len(unique_symbols) >= num_stocks

def award_badge(user_id, badge_id):
    """Award a badge to the user."""
    db.collection('user_badges').add({
        'user_id': user_id,
        'badge_id': badge_id,
        'awarded_at': firestore.SERVER_TIMESTAMP
    })
    print(f"Awarded badge {badge_id} to user {user_id}")

def fetch_user_badges(user_id):
    """Fetch all badges awarded to a user."""
    badges = db.collection('user_badges').where('user_id', '==', user_id).get()
    badge_data = []
    for badge in badges:
        badge_ref = db.collection('badges').document(badge.to_dict()['badge_id']).get()
        if badge_ref.exists:
            badge_data.append({
                'badge_id': badge.to_dict()['badge_id'],
                'name': badge_ref.to_dict()['name'],
                'description': badge_ref.to_dict()['description'],
                'icon': badge_ref.to_dict()['icon']
            })
    return badge_data