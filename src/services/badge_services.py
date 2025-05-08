# src/services/badge_service.py
from utils.db import db
from datetime import datetime, timedelta, timezone
from services.market_data import fetch_stock_data, fetch_crypto_data
from google.cloud import firestore
from utils.constants import ACHIEVEMENTS
from firebase_admin import firestore
from flask import url_for

# Specify the time zone
tz = timezone.utc

# Get the current time in the specified time zone
now = datetime.now(tz)

def create_badges():
    """Create badge definitions in the database."""
    try:
        # Import ACHIEVEMENTS directly from constants to ensure we have the latest
        from utils.constants import ACHIEVEMENTS

        # Get reference to the badges collection
        badges_ref = db.collection('badges')
        
        # For each badge in the ACHIEVEMENTS dictionary
        for badge_id, badge_info in ACHIEVEMENTS.items():
            badge_ref = badges_ref.document(badge_id)
            
            # Create or update the badge document
            badge_ref.set({
                'name': badge_info['name'],
                'description': badge_info['description'],
                'icon': badge_info.get('icon', '🏆'),  # Default icon if none provided
                'difficulty': badge_info.get('difficulty', 'medium')
            })
        
        print(f"Created/updated {len(ACHIEVEMENTS)} badges in the database")
        return True
    except Exception as e:
        print(f"Error creating badges: {e}")
        return False

def award_badge(user_id, badge_id):
    """Award a badge to a user.
    
    Args:
        user_id (str): The user's ID
        badge_id (str): The badge ID to award
        
    Returns:
        bool: True if badge was awarded, False otherwise
    """
    try:
        # Check if the badge exists in ACHIEVEMENTS
        if badge_id not in ACHIEVEMENTS:
            print(f"Badge {badge_id} does not exist in ACHIEVEMENTS")
            return False
            
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
            'awarded_at': datetime.now(tz)
        })
        
        print(f"Awarded badge {badge_id} to user {user_id}")
        return True
    
    except Exception as e:
        print(f"Error awarding badge: {e}")
        return False

def remove_duplicate_badges(user_id=None):
    """Remove duplicate badges for a user or all users.
    
    Args:
        user_id (str, optional): The user's ID. If None, clean for all users.
        
    Returns:
        dict: Result with count of removed duplicates
    """
    try:
        # Get all user badges
        if user_id:
            user_badges_query = db.collection('user_badges').where('user_id', '==', user_id)
        else:
            user_badges_query = db.collection('user_badges')
            
        user_badges = list(user_badges_query.stream())
        
        # Track which badges we've seen
        seen_badges = {}  # {user_id: {badge_id: document_ref}}
        duplicate_count = 0
        
        for badge_doc in user_badges:
            badge_data = badge_doc.to_dict()
            current_user_id = badge_data.get('user_id')
            badge_id = badge_data.get('badge_id')
            
            if not current_user_id or not badge_id:
                continue
                
            # Initialize user's entry if not exists
            if current_user_id not in seen_badges:
                seen_badges[current_user_id] = {}
                
            # If we've seen this badge for this user before, it's a duplicate
            if badge_id in seen_badges[current_user_id]:
                # Compare timestamps to keep the older one
                existing_ref = seen_badges[current_user_id][badge_id]
                existing_data = existing_ref.get().to_dict()
                existing_time = existing_data.get('awarded_at')
                current_time = badge_data.get('awarded_at')
                
                # Keep the older badge, delete the newer one
                if current_time and existing_time and current_time > existing_time:
                    badge_doc.reference.delete()
                    duplicate_count += 1
                else:
                    existing_ref.delete()
                    seen_badges[current_user_id][badge_id] = badge_doc.reference
                    duplicate_count += 1
            else:
                # First time seeing this badge for this user
                seen_badges[current_user_id][badge_id] = badge_doc.reference
                
        return {
            'success': True,
            'message': f"Removed {duplicate_count} duplicate badges",
            'count': duplicate_count
        }
        
    except Exception as e:
        print(f"Error removing duplicate badges: {e}")
        return {
            'success': False,
            'error': str(e)
        }

def fetch_user_badges(user_id):
    """Fetch all badges awarded to a user with better error handling and no duplicates."""
    try:
        user_badges = db.collection('user_badges').where('user_id', '==', user_id).stream()
        badge_data = []
        processed_badge_ids = set()  # Track which badges we've already processed
        
        for badge_doc in user_badges:
            badge_info = badge_doc.to_dict()
            badge_id = badge_info.get('badge_id')
            
            # Skip if we've already processed this badge ID
            if badge_id in processed_badge_ids:
                continue
                
            processed_badge_ids.add(badge_id)
            
            if badge_id:
                # Get badge details from ACHIEVEMENTS constant
                if badge_id in ACHIEVEMENTS:
                    badge_data.append({
                        'name': ACHIEVEMENTS[badge_id]['name'],
                        'description': ACHIEVEMENTS[badge_id]['description'],
                        'icon': ACHIEVEMENTS[badge_id]['icon'],
                        'awarded_at': badge_info.get('awarded_at'),
                        'badge_id': badge_id
                    })
                else:
                    # Use default values if badge not found in constants
                    badge_data.append({
                        'name': badge_id.replace('_', ' ').title(),
                        'description': 'Achievement unlocked',
                        'icon': '🏆',
                        'awarded_at': badge_info.get('awarded_at'),
                        'badge_id': badge_id
                    })

        return sorted(badge_data, key=lambda x: x['awarded_at'] if x['awarded_at'] else datetime.now(), reverse=True)
        
    except Exception as e:
        print(f"Error fetching badges for user {user_id}: {str(e)}")
        return []

def check_and_award_badges(user_id):
    """Check for and award badges to a user based on their achievements."""
    try:
        # Fetch user data
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get().to_dict()
        if not user:
            print(f"User {user_id} not found")
            return False
            
        ########## BEGINNER BADGES (EASY TO EARN) ##########
        
        # 1. First Login Badge - Award automatically when this function runs
        award_badge(user_id, 'first_login')
        
        # Get all user transactions for reuse in multiple badge checks
        transactions = list(db.collection('transactions').where('user_id', '==', user_id).stream())
        transaction_count = len(transactions)
        
        # 2. First Trade Badge
        if transaction_count >= 1:
            award_badge(user_id, 'first_trade')
        
        # 3. First Stock Badge
        stock_purchases = [t for t in transactions if 
                          t.to_dict().get('transaction_type') == 'BUY' and 
                          t.to_dict().get('asset_type') == 'stock']
        if len(stock_purchases) > 0:
            award_badge(user_id, 'first_stock')
            
        # 4. First Crypto Badge
        crypto_purchases = [t for t in transactions if 
                           t.to_dict().get('transaction_type') == 'BUY' and 
                           t.to_dict().get('asset_type') == 'crypto']
        if len(crypto_purchases) > 0:
            award_badge(user_id, 'first_crypto')
        
        # 5. First Profit Badge
        profitable_trades = [t for t in transactions if 
                            t.to_dict().get('transaction_type') == 'SELL' and
                            t.to_dict().get('profit_loss', 0) > 0]
        if len(profitable_trades) > 0:
            award_badge(user_id, 'first_profit')
        
        # 6. Profile Setup Badge - Check if user has set profile picture or other profile fields
        try:
            default_profile_pic = url_for('static', filename='default-profile.png')
            profile_pic = user.get('profile_picture', '')
            
            has_custom_pic = profile_pic and profile_pic != default_profile_pic
            has_custom_username = user.get('username') != user.get('email', '').split('@')[0]
            
            # Consider profile complete if they have a custom pic or have changed username from default
            if has_custom_pic or has_custom_username:
                award_badge(user_id, 'profile_setup')
        except Exception as e:
            print(f"Error checking profile_setup badge: {e}")
        
        # 7. First Watchlist Badge
        try:
            watchlist_ref = db.collection('watchlists').document(user_id)
            watchlist = watchlist_ref.get()
            if watchlist.exists and len(watchlist.to_dict().get('symbols', [])) > 0:
                award_badge(user_id, 'first_watchlist')
        except Exception as e:
            print(f"Error checking first_watchlist badge: {e}")
        
        # 8. Theme Change Badge
        try:
            default_accent = '#64ffda'
            default_bg = '#0a0a0a'
            if user.get('accent_color') != default_accent or user.get('background_color') != default_bg:
                award_badge(user_id, 'theme_change')
        except Exception as e:
            print(f"Error checking theme_change badge: {e}")
        
        ########## INTERMEDIATE BADGES ##########
        
        # 9. Five Trades Badge
        if transaction_count >= 5:
            award_badge(user_id, 'five_trades')
        
        # 10. Ten Trades Badge
        if transaction_count >= 10:
            award_badge(user_id, 'ten_trades')

        ########## PORTFOLIO VALUE BADGES ##########
        
        # Get portfolio data for value-based badges
        try:
            # Fetch user's portfolio
            portfolio_items = list(db.collection('portfolios').where('user_id', '==', user_id).stream())
            
            # Calculate total portfolio value (including cash balance)
            portfolio_value = user.get('balance', 0)  # Start with cash balance
            unique_assets = set()
            
            for item in portfolio_items:
                item_data = item.to_dict()
                symbol = item_data.get('symbol', '')
                shares = item_data.get('shares', 0)
                asset_type = item_data.get('asset_type', 'stock')
                
                # Add to unique assets set
                unique_assets.add(symbol)
                
                # Get current price based on asset type
                current_price = 0
                if asset_type == 'stock':
                    price_data = fetch_stock_data(symbol)
                    if price_data and 'close' in price_data:
                        current_price = price_data['close']
                else:  # crypto
                    price_data = fetch_crypto_data(symbol)
                    if price_data and 'price' in price_data:
                        current_price = price_data['price']
                
                # Calculate position value and add to total
                position_value = shares * current_price
                portfolio_value += position_value
            
            # 11. Portfolio 1k Badge
            if portfolio_value >= 1000:
                award_badge(user_id, 'portfolio_1k')
                
            # 12. Portfolio 10k Badge
            if portfolio_value >= 10000:
                award_badge(user_id, 'portfolio_10k')
                
            # 13. Portfolio 100k Badge
            if portfolio_value >= 100000:
                award_badge(user_id, 'portfolio_100k')
                
            # 14. Portfolio 1M Badge
            if portfolio_value >= 1000000:
                award_badge(user_id, 'portfolio_1m')
        except Exception as e:
            print(f"Error checking portfolio value badges: {e}")

        ########## PROFIT BADGES ##########
        
        # 15. Small Profit Badge (Make $100 profit on a single trade)
        try:
            profit_trades = db.collection('transactions')\
                .where('user_id', '==', user_id)\
                .where('profit_loss', '>=', 100)\
                .limit(1)\
                .get()
                
            if len(list(profit_trades)) > 0:
                award_badge(user_id, 'small_profit')
        except Exception as e:
            print(f"Error checking small_profit badge: {e}")

        # 16. Big Spender Badge (Single trade worth over $10,000)
        try:
            big_trades = db.collection('transactions')\
                .where('user_id', '==', user_id)\
                .where('total_amount', '>=', 10000)\
                .limit(1)\
                .get()
                
            if len(list(big_trades)) > 0:
                award_badge(user_id, 'big_spender')
        except Exception as e:
            print(f"Error checking big_spender badge: {e}")
            
        ########## DIVERSITY & ACTIVITY BADGES ##########
        
        # 17. Diversified Badge (Own 3 different stocks/cryptos)
        if len(unique_assets) >= 3:
            award_badge(user_id, 'diversified')
            
        # 18. Day Trader Badge (Make 3 trades in a single day)
        try:
            # Group transactions by day
            from collections import defaultdict
            trades_by_day = defaultdict(int)
            
            for t in transactions:
                t_data = t.to_dict()
                if 'timestamp' in t_data:
                    trade_date = t_data['timestamp'].strftime('%Y-%m-%d')
                    trades_by_day[trade_date] += 1
            
            # Check if any day has 3+ trades
            if any(count >= 3 for count in trades_by_day.values()):
                award_badge(user_id, 'day_trader')
        except Exception as e:
            print(f"Error checking day_trader badge: {e}")
            
        # 19. Learn Basics Badge (Visit documentation section)
        try:
            user_activity = db.collection('user_activity')\
                .where('user_id', '==', user_id)\
                .where('activity_type', '==', 'viewed_documentation')\
                .limit(1)\
                .get()
                
            if len(list(user_activity)) > 0:
                award_badge(user_id, 'learn_basics')
        except Exception as e:
            print(f"Error checking learn_basics badge: {e}")
            
        # 20. One Week Badge (Log in for 7 consecutive days)
        try:
            login_streak = user.get('login_streak', 0)
            if login_streak >= 7:
                award_badge(user_id, 'one_week')
        except Exception as e:
            print(f"Error checking one_week badge: {e}")
            
        ########## VOLUME TRADER BADGES ##########
        
        # 21. Century Club Badge (Complete 100 total trades)
        if transaction_count >= 100:
            award_badge(user_id, 'century_club')
            
        # 22. Trading Legend Badge (Complete 1000 total trades)
        if transaction_count >= 1000:
            award_badge(user_id, 'trading_legend')
            
        # Calculate trading stats for the current day
        try:
            today = datetime.now(tz).date()
            today_trades = [t for t in transactions if 
                            t.to_dict().get('timestamp').date() == today]
            today_trades_count = len(today_trades)
            
            # 23. Trading Addict Badge (50 trades in a single day)
            if today_trades_count >= 50:
                award_badge(user_id, 'trading_addict')
                
            # 24. Volume King Badge (100 trades in a single day)
            if today_trades_count >= 100:
                award_badge(user_id, 'volume_king')
        except Exception as e:
            print(f"Error checking volume trader badges: {e}")
            
        ########## PROFIT HUNTER BADGES ##########
        
        try:
            # Find trades with significant profits
            trades_with_profits = []
            for t in transactions:
                t_data = t.to_dict()
                if t_data.get('transaction_type') == 'SELL' and 'profit_loss' in t_data and 'purchase_price' in t_data:
                    purchase_price = t_data.get('purchase_price', 0)
                    if purchase_price > 0:
                        profit_percentage = (t_data.get('profit_loss', 0) / purchase_price) * 100
                        trades_with_profits.append({
                            'profit_percentage': profit_percentage,
                            'timestamp': t_data.get('timestamp')
                        })
                        
            # Sort by profit percentage
            if trades_with_profits:
                trades_with_profits.sort(key=lambda x: x['profit_percentage'], reverse=True)
                max_profit_percentage = trades_with_profits[0]['profit_percentage']
                
                # 25. Profit Hunter Badge (20% profit on a single trade)
                if max_profit_percentage >= 20:
                    award_badge(user_id, 'profit_hunter')
                    
                # 26. Golden Touch Badge (50% profit on a single trade)
                if max_profit_percentage >= 50:
                    award_badge(user_id, 'golden_touch')
                    
                # 27. Legendary Trader Badge (100% profit on a single trade)
                if max_profit_percentage >= 100:
                    award_badge(user_id, 'legendary_trader')
        except Exception as e:
            print(f"Error checking profit hunter badges: {e}")
            
        ########## CRYPTO SPECIFIC BADGES ##########
        
        try:
            # 28. Crypto Enthusiast Badge (Own 5 different cryptocurrencies)
            crypto_holdings = [item for item in portfolio_items if item.to_dict().get('asset_type') == 'crypto']
            unique_cryptos = set([item.to_dict().get('symbol') for item in crypto_holdings])
            
            if len(unique_cryptos) >= 5:
                award_badge(user_id, 'crypto_enthusiast')
                
            # 29. Crypto Whale Badge (Have $50,000 in cryptocurrency holdings)
            crypto_value = 0
            for item in crypto_holdings:
                item_data = item.to_dict()
                symbol = item_data.get('symbol')
                shares = item_data.get('shares', 0)
                
                # Get current price
                crypto_data = fetch_crypto_data(symbol)
                if crypto_data and 'price' in crypto_data:
                    crypto_value += shares * crypto_data['price']
            
            if crypto_value >= 50000:
                award_badge(user_id, 'crypto_whale')
                
            # 30. Bitcoin Maximalist Badge (Hold at least 1 whole Bitcoin)
            for item in crypto_holdings:
                item_data = item.to_dict()
                symbol = item_data.get('symbol')
                shares = item_data.get('shares', 0)
                
                if symbol == 'BTC' and shares >= 1:
                    award_badge(user_id, 'bitcoin_maximalist')
                    break
        except Exception as e:
            print(f"Error checking crypto badges: {e}")

        return True
    except Exception as e:
        print(f"Error checking badges: {e}")
        return False