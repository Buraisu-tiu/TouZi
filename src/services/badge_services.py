# src/services/badge_service.py
from utils.db import db
from datetime import datetime, timedelta, timezone
from services.market_data import fetch_stock_data, fetch_crypto_data
from google.cloud import firestore
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
    try:
        print(f"Checking badges for user {user_id}")
        
        # Check if user has already been awarded each badge
        awarded_badges = fetch_user_badges(user_id)
        awarded_badge_ids = [badge['badge_id'] for badge in awarded_badges]
        
        # Basic badges
        # First login badge (easy)
        if 'first_login' not in awarded_badge_ids:
            award_badge(user_id, 'first_login')
            print(f"Awarded 'first_login' badge to user {user_id}")

        # First Trade Badge (easy)
        if 'first_trade' not in awarded_badge_ids and has_completed_first_trade(user_id):
            award_badge(user_id, 'first_trade')
            print(f"Awarded 'first_trade' badge to user {user_id}")

        # First Stock Badge (easy)
        if 'first_stock' not in awarded_badge_ids and has_asset_type(user_id, 'stock'):
            award_badge(user_id, 'first_stock')
            print(f"Awarded 'first_stock' badge to user {user_id}")
            
        # First Crypto Badge (easy)
        if 'first_crypto' not in awarded_badge_ids and has_asset_type(user_id, 'crypto'):
            award_badge(user_id, 'first_crypto')
            print(f"Awarded 'first_crypto' badge to user {user_id}")
            
        # First Profit Badge (easy)
        if 'first_profit' not in awarded_badge_ids and has_profitable_trade(user_id):
            award_badge(user_id, 'first_profit')
            print(f"Awarded 'first_profit' badge to user {user_id}")
            
        # Volume badges
        # Five trades badge (medium)
        if 'five_trades' not in awarded_badge_ids and get_total_trades_count(user_id) >= 5:
            award_badge(user_id, 'five_trades')
            print(f"Awarded 'five_trades' badge to user {user_id}")
            
        # Ten trades badge (medium)
        if 'ten_trades' not in awarded_badge_ids and get_total_trades_count(user_id) >= 10:
            award_badge(user_id, 'ten_trades')
            print(f"Awarded 'ten_trades' badge to user {user_id}")
            
        # Century Club Badge (hard)
        if 'century_club' not in awarded_badge_ids and get_total_trades_count(user_id) >= 100:
            award_badge(user_id, 'century_club')
            print(f"Awarded 'century_club' badge to user {user_id}")
            
        # Trading Legend Badge (very hard)
        if 'trading_legend' not in awarded_badge_ids and get_total_trades_count(user_id) >= 1000:
            award_badge(user_id, 'trading_legend')
            print(f"Awarded 'trading_legend' badge to user {user_id}")
            
        # Day Trader Badge (medium)
        if 'day_trader' not in awarded_badge_ids and has_completed_trades_today(user_id, 3):
            award_badge(user_id, 'day_trader')
            print(f"Awarded 'day_trader' badge to user {user_id}")
            
        # Trading Addict Badge (very hard)
        if 'trading_addict' not in awarded_badge_ids and has_completed_trades_today(user_id, 50):
            award_badge(user_id, 'trading_addict')
            print(f"Awarded 'trading_addict' badge to user {user_id}")
            
        # Volume King Badge (very hard)
        if 'volume_king' not in awarded_badge_ids and has_completed_trades_today(user_id, 100):
            award_badge(user_id, 'volume_king')
            print(f"Awarded 'volume_king' badge to user {user_id}")
            
        # Portfolio Value Badges
        portfolio_value = get_total_portfolio_value(user_id)
        
        # Portfolio $1k Badge (medium)
        if 'portfolio_1k' not in awarded_badge_ids and portfolio_value >= 1000:
            award_badge(user_id, 'portfolio_1k')
            print(f"Awarded 'portfolio_1k' badge to user {user_id}")
            
        # Portfolio $10k Badge (hard)
        if 'portfolio_10k' not in awarded_badge_ids and portfolio_value >= 10000:
            award_badge(user_id, 'portfolio_10k')
            print(f"Awarded 'portfolio_10k' badge to user {user_id}")
            
        # Portfolio $100k Badge (hard)
        if 'portfolio_100k' not in awarded_badge_ids and portfolio_value >= 100000:
            award_badge(user_id, 'portfolio_100k')
            print(f"Awarded 'portfolio_100k' badge to user {user_id}")
            
        # Portfolio $1M Badge (very hard)
        if 'portfolio_1m' not in awarded_badge_ids and portfolio_value >= 1000000:
            award_badge(user_id, 'portfolio_1m')
            print(f"Awarded 'portfolio_1m' badge to user {user_id}")
            
        # Diversification badges
        # Diversified Badge (medium)
        if 'diversified' not in awarded_badge_ids and has_diversified_portfolio(user_id, 3):
            award_badge(user_id, 'diversified')
            print(f"Awarded 'diversified' badge to user {user_id}")
            
        # Well Diversified Badge (hard)
        if 'well_diversified' not in awarded_badge_ids and has_diversified_portfolio(user_id, 10):
            award_badge(user_id, 'well_diversified')
            print(f"Awarded 'well_diversified' badge to user {user_id}")
            
        # Risk badges
        # Risk Taker Badge (medium)
        if 'risk_taker' not in awarded_badge_ids and has_portfolio_concentration(user_id, 50):
            award_badge(user_id, 'risk_taker')
            print(f"Awarded 'risk_taker' badge to user {user_id}")
            
        # All In Badge (hard)
        if 'all_in' not in awarded_badge_ids and has_portfolio_concentration(user_id, 90):
            award_badge(user_id, 'all_in')
            print(f"Awarded 'all_in' badge to user {user_id}")
            
        # Profit badges
        # Profit Hunter Badge (hard)
        if 'profit_hunter' not in awarded_badge_ids and has_profit_percentage(user_id, 20):
            award_badge(user_id, 'profit_hunter')
            print(f"Awarded 'profit_hunter' badge to user {user_id}")
            
        # Golden Touch Badge (hard)
        if 'golden_touch' not in awarded_badge_ids and has_profit_percentage(user_id, 50):
            award_badge(user_id, 'golden_touch')
            print(f"Awarded 'golden_touch' badge to user {user_id}")
            
        # Legendary Trader Badge (very hard)
        if 'legendary_trader' not in awarded_badge_ids and has_profit_percentage(user_id, 100):
            award_badge(user_id, 'legendary_trader')
            print(f"Awarded 'legendary_trader' badge to user {user_id}")

        # Loss badges (humorous ones)
        # Tuition Paid Badge (easy)
        if 'tuition_paid' not in awarded_badge_ids and has_loss_trade(user_id):
            award_badge(user_id, 'tuition_paid')
            print(f"Awarded 'tuition_paid' badge to user {user_id}")
            
        # Buy High Sell Low Badge (easy)
        if 'buy_high_sell_low' not in awarded_badge_ids and has_loss_percentage(user_id, 20):
            award_badge(user_id, 'buy_high_sell_low')
            print(f"Awarded 'buy_high_sell_low' badge to user {user_id}")
            
        # Portfolio Reset Badge (hard)
        if 'portfolio_reset' not in awarded_badge_ids and has_loss_percentage(user_id, 90):
            award_badge(user_id, 'portfolio_reset')
            print(f"Awarded 'portfolio_reset' badge to user {user_id}")
            
        # Streak badges
        # Hot Streak Badge (medium)
        if 'hot_streak' not in awarded_badge_ids and has_consecutive_profitable_trades(user_id, 3):
            award_badge(user_id, 'hot_streak')
            print(f"Awarded 'hot_streak' badge to user {user_id}")
            
        # Unstoppable Badge (hard)
        if 'unstoppable' not in awarded_badge_ids and has_consecutive_profitable_trades(user_id, 7):
            award_badge(user_id, 'unstoppable')
            print(f"Awarded 'unstoppable' badge to user {user_id}")
            
        # Legendary Streak Badge (very hard)
        if 'legendary_streak' not in awarded_badge_ids and has_consecutive_profitable_trades(user_id, 10):
            award_badge(user_id, 'legendary_streak')
            print(f"Awarded 'legendary_streak' badge to user {user_id}")
            
        # Crypto specific badges
        # Crypto Enthusiast Badge (medium)
        if 'crypto_enthusiast' not in awarded_badge_ids and has_crypto_diversity(user_id, 5):
            award_badge(user_id, 'crypto_enthusiast')
            print(f"Awarded 'crypto_enthusiast' badge to user {user_id}")
            
        # Crypto Whale Badge (hard)
        if 'crypto_whale' not in awarded_badge_ids and has_crypto_value(user_id, 50000):
            award_badge(user_id, 'crypto_whale')
            print(f"Awarded 'crypto_whale' badge to user {user_id}")
            
        # Bitcoin Maximalist Badge (very hard)
        if 'bitcoin_maximalist' not in awarded_badge_ids and has_full_bitcoin(user_id):
            award_badge(user_id, 'bitcoin_maximalist')
            print(f"Awarded 'bitcoin_maximalist' badge to user {user_id}")

        # Theme change badge (easy)
        if 'theme_change' not in awarded_badge_ids and has_changed_theme(user_id):
            award_badge(user_id, 'theme_change')
            print(f"Awarded 'theme_change' badge to user {user_id}")

        return True
    except Exception as e:
        print(f"Error checking badges: {e}")
        return False

# Helper functions for badge criteria
def has_completed_first_trade(user_id):
    """Check if the user has completed at least one trade."""
    try:
        transactions = db.collection('transactions').where('user_id', '==', user_id).limit(1).get()
        return len(list(transactions)) > 0
    except Exception as e:
        print(f"Error checking first trade: {e}")
        return False

def has_asset_type(user_id, asset_type):
    """Check if the user has any assets of the specified type."""
    try:
        portfolio = db.collection('portfolios').where('user_id', '==', user_id).where('asset_type', '==', asset_type).limit(1).get()
        return len(list(portfolio)) > 0
    except Exception as e:
        print(f"Error checking asset type: {e}")
        return False

def has_profitable_trade(user_id):
    """Check if the user has ever made a profitable trade."""
    try:
        trades = db.collection('transactions')\
            .where('user_id', '==', user_id)\
            .where('profit_loss', '>', 0)\
            .limit(1)\
            .get()
        return len(list(trades)) > 0
    except Exception as e:
        print(f"Error checking profitable trade: {e}")
        return False

def has_loss_trade(user_id):
    """Check if the user has ever made a losing trade."""
    try:
        trades = db.collection('transactions')\
            .where('user_id', '==', user_id)\
            .where('profit_loss', '<', 0)\
            .limit(1)\
            .get()
        return len(list(trades)) > 0
    except Exception as e:
        print(f"Error checking loss trade: {e}")
        return False

def get_total_trades_count(user_id):
    """Get the total number of trades made by the user."""
    try:
        transactions = db.collection('transactions').where('user_id', '==', user_id).get()
        return len(list(transactions))
    except Exception as e:
        print(f"Error counting trades: {e}")
        return 0

def has_completed_trades_today(user_id, num_trades):
    """Check if the user has completed a certain number of trades today."""
    try:
        today = datetime.now(tz).date()
        start_of_day = datetime(today.year, today.month, today.day, tzinfo=tz)
        
        transactions = db.collection('transactions')\
            .where('user_id', '==', user_id)\
            .where('timestamp', '>=', start_of_day)\
            .get()
        
        return len(list(transactions)) >= num_trades
    except Exception as e:
        print(f"Error checking trades today: {e}")
        return False

def get_total_portfolio_value(user_id):
    """Calculate the total value of a user's portfolio including cash."""
    try:
        # Get user's cash balance
        user = db.collection('users').document(user_id).get().to_dict()
        cash_balance = user.get('balance', 0) if user else 0
        
        # Get all portfolio items
        portfolio_items = db.collection('portfolios').where('user_id', '==', user_id).stream()
        
        total_value = cash_balance
        
        # Calculate value of each position
        for item in portfolio_items:
            item_data = item.to_dict()
            symbol = item_data['symbol']
            shares = item_data['shares']
            
            # Get current price
            if item_data['asset_type'] == 'stock':
                price_data = fetch_stock_data(symbol)
                if price_data and 'close' in price_data:
                    current_price = price_data['close']
                else:
                    current_price = item_data.get('purchase_price', 0)
            else:  # crypto
                price_data = fetch_crypto_data(symbol)
                if price_data and 'price' in price_data:
                    current_price = price_data['price']
                else:
                    current_price = item_data.get('purchase_price', 0)
            
            position_value = shares * current_price
            total_value += position_value
        
        return total_value
    except Exception as e:
        print(f"Error calculating portfolio value: {e}")
        return 0

def has_diversified_portfolio(user_id, num_symbols):
    """Check if the user has a diversified portfolio (owns different symbols)."""
    try:
        portfolio_items = db.collection('portfolios').where('user_id', '==', user_id).stream()
        unique_symbols = set()
        
        for item in portfolio_items:
            unique_symbols.add(item.to_dict()['symbol'])
            
        return len(unique_symbols) >= num_symbols
    except Exception as e:
        print(f"Error checking portfolio diversity: {e}")
        return False

def has_crypto_diversity(user_id, num_crypto):
    """Check if the user has a diverse crypto portfolio."""
    try:
        crypto_items = db.collection('portfolios')\
            .where('user_id', '==', user_id)\
            .where('asset_type', '==', 'crypto')\
            .stream()
            
        unique_crypto = set()
        for item in crypto_items:
            unique_crypto.add(item.to_dict()['symbol'])
            
        return len(unique_crypto) >= num_crypto
    except Exception as e:
        print(f"Error checking crypto diversity: {e}")
        return False

def has_crypto_value(user_id, min_value):
    """Check if the user has crypto assets worth at least min_value."""
    try:
        crypto_items = db.collection('portfolios')\
            .where('user_id', '==', user_id)\
            .where('asset_type', '==', 'crypto')\
            .stream()
            
        total_value = 0
        for item in crypto_items:
            item_data = item.to_dict()
            symbol = item_data['symbol']
            shares = item_data['shares']
            
            price_data = fetch_crypto_data(symbol)
            if price_data and 'price' in price_data:
                current_price = price_data['price']
            else:
                current_price = item_data.get('purchase_price', 0)
                
            position_value = shares * current_price
            total_value += position_value
            
        return total_value >= min_value
    except Exception as e:
        print(f"Error checking crypto value: {e}")
        return False

def has_portfolio_concentration(user_id, percentage):
    """Check if the user has a concentrated position (% in one asset)."""
    try:
        portfolio_value = get_total_portfolio_value(user_id)
        if portfolio_value == 0:
            return False
            
        portfolio_items = db.collection('portfolios').where('user_id', '==', user_id).stream()
        
        for item in portfolio_items:
            item_data = item.to_dict()
            symbol = item_data['symbol']
            shares = item_data['shares']
            
            # Get current price
            if item_data['asset_type'] == 'stock':
                price_data = fetch_stock_data(symbol)
                if price_data and 'close' in price_data:
                    current_price = price_data['close']
                else:
                    current_price = item_data.get('purchase_price', 0)
            else:  # crypto
                price_data = fetch_crypto_data(symbol)
                if price_data and 'price' in price_data:
                    current_price = price_data['price']
                else:
                    current_price = item_data.get('purchase_price', 0)
            
            position_value = shares * current_price
            position_percentage = (position_value / portfolio_value) * 100
            
            if position_percentage >= percentage:
                return True
                
        return False
    except Exception as e:
        print(f"Error checking portfolio concentration: {e}")
        return False

def has_profit_percentage(user_id, percentage):
    """Check if the user has made a single trade with profit percentage >= specified value."""
    try:
        trades = db.collection('transactions').where('user_id', '==', user_id).stream()
        
        for trade in trades:
            trade_data = trade.to_dict()
            
            if trade_data.get('transaction_type') == 'SELL' and trade_data.get('profit_loss'):
                purchase_price = trade_data.get('purchase_price', 0)
                if purchase_price > 0:
                    sell_price = trade_data.get('price', 0)
                    profit_percentage = ((sell_price - purchase_price) / purchase_price) * 100
                    
                    if profit_percentage >= percentage:
                        return True
        
        return False
    except Exception as e:
        print(f"Error checking profit percentage: {e}")
        return False

def has_loss_percentage(user_id, percentage):
    """Check if the user has made a single trade with loss percentage >= specified value."""
    try:
        trades = db.collection('transactions').where('user_id', '==', user_id).stream()
        
        for trade in trades:
            trade_data = trade.to_dict()
            
            if trade_data.get('transaction_type') == 'SELL' and trade_data.get('profit_loss'):
                purchase_price = trade_data.get('purchase_price', 0)
                if purchase_price > 0:
                    sell_price = trade_data.get('price', 0)
                    loss_percentage = ((purchase_price - sell_price) / purchase_price) * 100
                    
                    if loss_percentage >= percentage:
                        return True
        
        return False
    except Exception as e:
        print(f"Error checking loss percentage: {e}")
        return False

def has_consecutive_profitable_trades(user_id, count):
    """Check if the user has made a streak of consecutive profitable trades."""
    try:
        trades = db.collection('transactions')\
            .where('user_id', '==', user_id)\
            .where('transaction_type', '==', 'SELL')\
            .order_by('timestamp', direction=firestore.Query.DESCENDING)\
            .stream()
            
        streak = 0
        
        for trade in trades:
            trade_data = trade.to_dict()
            profit_loss = trade_data.get('profit_loss', 0)
            
            if profit_loss > 0:
                streak += 1
                if streak >= count:
                    return True
            else:
                # Streak broken
                return False
                
        return False
    except Exception as e:
        print(f"Error checking trade streak: {e}")
        return False

def has_full_bitcoin(user_id):
    """Check if the user has at least 1 full Bitcoin."""
    try:
        bitcoin_holdings = db.collection('portfolios')\
            .where('user_id', '==', user_id)\
            .where('asset_type', '==', 'crypto')\
            .where('symbol', '==', 'BTC')\
            .get()
            
        for holding in bitcoin_holdings:
            holding_data = holding.to_dict()
            if holding_data.get('shares', 0) >= 1.0:
                return True
                
        return False
    except Exception as e:
        print(f"Error checking Bitcoin holdings: {e}")
        return False

def has_changed_theme(user_id):
    """Check if the user has changed their theme settings."""
    try:
        user = db.collection('users').document(user_id).get().to_dict()
        
        # Check if user has custom colors set
        if user:
            default_accent = '#64ffda'
            default_bg = '#0a0a0a'
            default_text = '#ffffff'
            
            user_accent = user.get('accent_color')
            user_bg = user.get('background_color')
            user_text = user.get('text_color')
            
            # If any color is different from default
            if (user_accent and user_accent != default_accent) or \
               (user_bg and user_bg != default_bg) or \
               (user_text and user_text != default_text):
                return True
                
        return False
    except Exception as e:
        print(f"Error checking theme change: {e}")
        return False