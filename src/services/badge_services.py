# src/services/badge_service.py
from utils.db import db
from datetime import datetime
from services.market_data import fetch_stock_data, fetch_crypto_data
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime, timedelta, timezone

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
    """Enhanced badge checking system"""
    try:
        # Get user data
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get().to_dict()
        if not user:
            return
        
        # Get portfolio data
        portfolio_refs = db.collection('portfolios').where(filter=FieldFilter("user_id", "==", user_id)).stream()
        portfolio_items = [item.to_dict() for item in portfolio_refs]
        
        # Get transaction history
        transactions = db.collection('transactions').where(filter=FieldFilter("user_id", "==", user_id)).order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
        
        # Calculate total portfolio value
        total_value = user['balance']
        for item in portfolio_items:
            if item['asset_type'] == 'stock':
                stock_data = fetch_stock_data(item['symbol'])
                if 'error' not in stock_data:
                    total_value += stock_data['close'] * item['shares']
            elif item['asset_type'] == 'crypto':
                crypto_data = fetch_crypto_data(item['symbol'])
                if 'error' not in crypto_data:
                    total_value += crypto_data['price'] * item['shares']

        # Check Achievement Badges
        if total_value >= 1000000:
            award_badge(user_id, "Trading Tycoon")
        elif total_value >= 100000:
            award_badge(user_id, "Wall Street Whale")
        elif total_value >= 10000:
            award_badge(user_id, "Market Maven")

        # Check Trading Volume Badges
        today = datetime.now(tz).date()
        today_trades = [t.to_dict() for t in transactions if t.to_dict()['timestamp'].date() == today]
        trades_count = len(today_trades)
        
        if trades_count >= 100:
            award_badge(user_id, "Volume King")
        elif trades_count >= 50:
            award_badge(user_id, "Trading Addict")
        elif trades_count >= 10:
            award_badge(user_id, "Day Trader")

        # Check Portfolio Diversity
        unique_stocks = len(set(item['symbol'] for item in portfolio_items if item['asset_type'] == 'stock'))
        if unique_stocks >= 20:
            award_badge(user_id, "Market Mogul")
        elif unique_stocks >= 10:
            award_badge(user_id, "Portfolio Master")
        elif unique_stocks >= 5:
            award_badge(user_id, "Diversifier")

        # Check Profit Streak
        profit_streak = 0
        max_streak = 0
        for t in transactions:
            t_data = t.to_dict()
            if t_data.get('profit_loss', 0) > 0:
                profit_streak += 1
                max_streak = max(max_streak, profit_streak)
            else:
                profit_streak = 0

        if max_streak >= 10:
            award_badge(user_id, "Legendary Streak")
        elif max_streak >= 7:
            award_badge(user_id, "Unstoppable")
        elif max_streak >= 3:
            award_badge(user_id, "Hot Streak")

        # Check Crypto Badges
        crypto_holdings = [item for item in portfolio_items if item['asset_type'] == 'crypto']
        crypto_value = sum(item['shares'] * fetch_crypto_data(item['symbol'])['price'] 
                         for item in crypto_holdings)

        if crypto_value >= 50000:
            award_badge(user_id, "Crypto Whale")
        if len(crypto_holdings) >= 5:
            award_badge(user_id, "Crypto Enthusiast")
        if crypto_holdings:
            award_badge(user_id, "Crypto Curious")

        # Check Risk Badges
        for item in portfolio_items:
            item_value = item['shares'] * (
                fetch_stock_data(item['symbol'])['close'] if item['asset_type'] == 'stock'
                else fetch_crypto_data(item['symbol'])['price']
            )
            if item_value / total_value >= 0.9:
                award_badge(user_id, "All or Nothing")
            elif item_value / total_value >= 0.5:
                award_badge(user_id, "Risk Taker")

        # Check Loss Badges
        biggest_loss = min((t.to_dict().get('profit_loss', 0) / t.to_dict()['total_amount'] 
                          for t in transactions if t.to_dict().get('profit_loss') is not None), 
                         default=0)
        
        if biggest_loss <= -0.9:
            award_badge(user_id, "Portfolio Reset")
        elif biggest_loss <= -0.2:
            award_badge(user_id, "Buy High Sell Low")

        # Continue with route handlers and other functionality...
        
    except Exception as e:
        print(f"Error checking badges: {str(e)}")
        return False

def award_badge(user_id, badge_name):
    """Award a badge to a user and create notification"""
    try:
        # Get badge document
        badge_query = db.collection('badges').where('name', '==', badge_name).limit(1).get()
        if not badge_query:
            return False

        badge_doc = list(badge_query)[0]
        badge_id = badge_doc.id

        # Check if user already has the badge
        existing_badge_query = db.collection('user_badges').where(
            'user_id', '==', user_id).where(
            'badge_id', '==', badge_id).limit(1).get()
        
        if not list(existing_badge_query):
            # Award the badge
            db.collection('user_badges').add({
                'user_id': user_id,
                'badge_id': badge_id,
                'date_earned': datetime.utcnow()
            })
            
            # Create notification
            db.collection('notifications').add({
                'user_id': user_id,
                'type': 'badge_earned',
                'badge_name': badge_name,
                'badge_description': badge_doc.to_dict()['description'],
                'timestamp': datetime.utcnow(),
                'read': False
            })
            
            return True
            
    except Exception as e:
        print(f"Error awarding badge: {str(e)}")
        return False