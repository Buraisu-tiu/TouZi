# src/services/badge_services.py
from utils.db import db
from utils.constants import ACHIEVEMENTS
from google.cloud import firestore
from datetime import datetime, time
import json
from services.market_data import fetch_stock_data

# Dictionary of badge conditions
BADGE_CONDITIONS = {
    'first_login': lambda user_id: check_first_login_badge(user_id),
    'night_owl': lambda user_id: check_night_owl_badge(user_id),
    'big_spender': lambda user_id: check_big_spender_badge(user_id),
    'portfolio_diversity': lambda user_id: check_portfolio_diversity(user_id),
    'millionaire': lambda user_id: check_millionaire_badge(user_id),
    'veteran_trader': lambda user_id: check_veteran_trader_badge(user_id),
    'theme_change': lambda user_id: check_theme_change_badge(user_id),
}

def create_badges():
    """Create all badges in the database."""
    try:
        # Get existing badges to avoid duplicates
        badges_ref = db.collection('badges')
        existing_badges = {doc.id: doc.to_dict() for doc in badges_ref.stream()}
        
        # Create/update badges from ACHIEVEMENTS constant
        for badge_id, badge_data in ACHIEVEMENTS.items():
            badge_doc = badges_ref.document(badge_id)
            if badge_id not in existing_badges:
                badge_doc.set({
                    'name': badge_data['name'],
                    'description': badge_data['description'],
                    'created_at': firestore.SERVER_TIMESTAMP
                })
                print(f"Created badge: {badge_data['name']}")
            else:
                # Update existing badge if needed
                if existing_badges[badge_id].get('name') != badge_data['name'] or \
                   existing_badges[badge_id].get('description') != badge_data['description']:
                    badge_doc.update({
                        'name': badge_data['name'],
                        'description': badge_data['description'],
                        'updated_at': firestore.SERVER_TIMESTAMP
                    })
                    print(f"Updated badge: {badge_data['name']}")
        
        return True
    except Exception as e:
        print(f"Error creating badges: {e}")
        return False

def award_badge(user_id, badge_id):
    """Award a badge to a user if they don't already have it."""
    try:
        # Check if user already has this badge
        existing_badge = db.collection('user_badges')\
            .where('user_id', '==', user_id)\
            .where('badge_id', '==', badge_id)\
            .limit(1)\
            .get()
        
        if len(list(existing_badge)) > 0:
            print(f"User {user_id} already has badge {badge_id}")
            return False
        
        # Award the badge
        db.collection('user_badges').add({
            'user_id': user_id,
            'badge_id': badge_id,
            'awarded_at': firestore.SERVER_TIMESTAMP
        })
        
        print(f"Awarded badge {badge_id} to user {user_id}")
        return True
        
    except Exception as e:
        print(f"Error awarding badge: {e}")
        return False

def check_and_award_badges(user_id):
    """Check all badge criteria and award badges that the user qualifies for."""
    try:
        # Get user data
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get().to_dict()
        
        if not user:
            print(f"User {user_id} not found in check_and_award_badges")
            return []
        
        awarded = []
        
        # These badges don't depend on asset_type
        if check_first_login_badge(user_id):
            awarded.append('first_login')
            
        if check_night_owl_badge(user_id):
            awarded.append('night_owl')
            
        if check_big_spender_badge(user_id):
            awarded.append('big_spender')
        
        if check_portfolio_diversity(user_id):
            awarded.append('portfolio_diversity')
            
        if check_millionaire_badge(user_id):
            awarded.append('millionaire')
        
        if check_veteran_trader_badge(user_id):
            awarded.append('veteran_trader')
            
        if check_theme_change_badge(user_id):
            awarded.append('theme_change')
        
        # Deliberately exclude any crypto-specific badges since
        # we no longer track asset types
        
        return awarded
    except Exception as e:
        print(f"Error in check_and_award_badges: {e}")
        return []

def check_first_login_badge(user_id):
    """Check if the user qualifies for the first login badge."""
    try:
        # Check if user already has the badge
        existing_badge = db.collection('user_badges')\
            .where('user_id', '==', user_id)\
            .where('badge_id', '==', 'first_login')\
            .limit(1)\
            .get()
        
        if len(list(existing_badge)) == 0:
            # User doesn't have the badge, award it
            award_badge(user_id, 'first_login')
            return True
            
        return False
    except Exception as e:
        print(f"Error checking first login badge: {e}")
        return False

def check_night_owl_badge(user_id):
    """Award badge if user logs in late at night (11 PM - 4 AM)."""
    try:
        # Get user's last login time
        user = db.collection('users').document(user_id).get().to_dict()
        last_login = user.get('last_login')
        
        if last_login:
            # Convert to datetime
            if isinstance(last_login, firestore.SERVER_TIMESTAMP):
                last_login = datetime.now()  # Use current time if SERVER_TIMESTAMP
                
            # Check if time is between 11 PM and 4 AM
            login_time = last_login.time()
            night_start = time(23, 0)  # 11 PM
            night_end = time(4, 0)  # 4 AM
            
            is_night_owl = (login_time >= night_start) or (login_time <= night_end)
            
            if is_night_owl:
                # Check if user already has the badge
                existing_badge = db.collection('user_badges')\
                    .where('user_id', '==', user_id)\
                    .where('badge_id', '==', 'night_owl')\
                    .limit(1)\
                    .get()
                
                if len(list(existing_badge)) == 0:
                    # User doesn't have the badge, award it
                    award_badge(user_id, 'night_owl')
                    return True
                    
        return False
    except Exception as e:
        print(f"Error checking night owl badge: {e}")
        return False

def check_portfolio_diversity(user_id):
    """Check if the user has a diverse portfolio (at least 5 different assets)."""
    try:
        portfolio = db.collection('portfolios').where('user_id', '==', user_id).stream()
        symbols = set()
        
        for item in portfolio:
            item_data = item.to_dict()
            symbol = item_data.get('symbol')
            if symbol:
                symbols.add(symbol)
        
        diversity_achieved = len(symbols) >= 5
        
        if diversity_achieved:
            # Check if user already has the badge
            existing_badge = db.collection('user_badges')\
                .where('user_id', '==', user_id)\
                .where('badge_id', '==', 'portfolio_diversity')\
                .limit(1)\
                .get()
            
            if len(list(existing_badge)) == 0:
                # User doesn't have the badge, award it
                award_badge(user_id, 'portfolio_diversity')
                return True
                
        return False
    except Exception as e:
        print(f"Error checking portfolio diversity: {e}")
        return False

def check_big_spender_badge(user_id):
    """Check if the user has spent more than $10,000 in a single transaction."""
    try:
        # Find any transaction with a total amount > $10,000
        transactions = db.collection('transactions')\
            .where('user_id', '==', user_id)\
            .where('total_amount', '>', 10000)\
            .limit(1)\
            .get()
        
        if len(list(transactions)) > 0:
            # Check if user already has the badge
            existing_badge = db.collection('user_badges')\
                .where('user_id', '==', user_id)\
                .where('badge_id', '==', 'big_spender')\
                .limit(1)\
                .get()
            
            if len(list(existing_badge)) == 0:
                # User doesn't have the badge, award it
                award_badge(user_id, 'big_spender')
                return True
                
        return False
    except Exception as e:
        print(f"Error checking big spender badge: {e}")
        return False

def check_millionaire_badge(user_id):
    """Check if the user's portfolio is worth over $1 million."""
    try:
        # Get user data (for balance)
        user = db.collection('users').document(user_id).get().to_dict()
        balance = user.get('balance', 0)
        
        # Get all portfolio items
        portfolio_items = db.collection('portfolios').where('user_id', '==', user_id).stream()
        
        # Calculate total portfolio value
        total_value = balance
        
        for item in portfolio_items:
            item_data = item.to_dict()
            symbol = item_data.get('symbol', '')
            shares = item_data.get('shares', 0)
            
            # Get current price using a unified approach
            price_data = fetch_stock_data(symbol)
            if price_data and 'close' in price_data:
                current_price = price_data['close']
                position_value = shares * current_price
                total_value += position_value
        
        millionaire_achieved = total_value >= 1000000
        
        if millionaire_achieved:
            # Check if user already has the badge
            existing_badge = db.collection('user_badges')\
                .where('user_id', '==', user_id)\
                .where('badge_id', '==', 'millionaire')\
                .limit(1)\
                .get()
            
            if len(list(existing_badge)) == 0:
                # User doesn't have the badge, award it
                award_badge(user_id, 'millionaire')
                return True
                
        return False
    except Exception as e:
        print(f"Error checking millionaire badge: {e}")
        return False

def check_veteran_trader_badge(user_id):
    """Check if the user has made at least 100 transactions."""
    try:
        # Count transactions
        transactions_query = db.collection('transactions')\
            .where('user_id', '==', user_id)\
            .get()
            
        transaction_count = len(list(transactions_query))
        
        if transaction_count >= 100:
            # Check if user already has the badge
            existing_badge = db.collection('user_badges')\
                .where('user_id', '==', user_id)\
                .where('badge_id', '==', 'veteran_trader')\
                .limit(1)\
                .get()
            
            if len(list(existing_badge)) == 0:
                # User doesn't have the badge, award it
                award_badge(user_id, 'veteran_trader')
                return True
                
        return False
    except Exception as e:
        print(f"Error checking veteran trader badge: {e}")
        return False

def check_theme_change_badge(user_id):
    """Check if the user has changed their theme."""
    try:
        # Get user data
        user = db.collection('users').document(user_id).get().to_dict()
        
        # Check if user has custom theme settings
        has_custom_theme = (
            user.get('accent_color') is not None or
            user.get('background_color') is not None or
            user.get('text_color') is not None
        )
        
        if has_custom_theme:
            # Check if user already has the badge
            existing_badge = db.collection('user_badges')\
                .where('user_id', '==', user_id)\
                .where('badge_id', '==', 'theme_change')\
                .limit(1)\
                .get()
            
            if len(list(existing_badge)) == 0:
                # User doesn't have the badge, award it
                award_badge(user_id, 'theme_change')
                return True
                
        return False
    except Exception as e:
        print(f"Error checking theme change badge: {e}")
        return False

# Function to fetch all badges for a user
def fetch_user_badges(user_id):
    """Fetch all badges awarded to a user."""
    try:
        badges = []
        # Get all badge IDs for the user
        user_badges = db.collection('user_badges').where('user_id', '==', user_id).stream()
        
        badge_ids = set()
        badge_info = {}
        
        # First, get all unique badge IDs and their award timestamps
        for badge in user_badges:
            badge_data = badge.to_dict()
            badge_id = badge_data.get('badge_id')
            if badge_id and badge_id not in badge_ids:
                badge_ids.add(badge_id)
                badge_info[badge_id] = {
                    'awarded_at': badge_data.get('awarded_at')
                }
        
        # Then, get badge details from badges collection
        for badge_id in badge_ids:
            badge_data = db.collection('badges').where('name', '==', badge_id).limit(1).get()
            
            if len(list(badge_data)) > 0:
                badge_details = badge_data[0].to_dict()
                badges.append({
                    'badge_id': badge_id,
                    'name': badge_details.get('name', badge_id),
                    'description': badge_details.get('description', 'No description available'),
                    'awarded_at': badge_info[badge_id]['awarded_at']
                })
            elif badge_id in ACHIEVEMENTS:
                # Use the fallback from ACHIEVEMENTS constant
                badges.append({
                    'badge_id': badge_id,
                    'name': ACHIEVEMENTS[badge_id]['name'],
                    'description': ACHIEVEMENTS[badge_id]['description'],
                    'awarded_at': badge_info[badge_id]['awarded_at']
                })
            else:
                # Use a generic fallback
                badges.append({
                    'badge_id': badge_id,
                    'name': badge_id.replace('_', ' ').title(),
                    'description': 'Achievement unlocked',
                    'awarded_at': badge_info[badge_id]['awarded_at']
                })
        
        # Sort badges by award date, most recent first
        badges.sort(key=lambda x: x['awarded_at'] if x['awarded_at'] else datetime.now(), reverse=True)
        
        return badges
    except Exception as e:
        print(f"Error fetching badges for user {user_id}: {str(e)}")
        return []