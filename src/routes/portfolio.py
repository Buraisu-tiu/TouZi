# src/routes/portfolio.py
from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from utils.db import db
from services.market_data import fetch_stock_data, fetch_crypto_data
from services.badge_services import check_and_award_badges
from google.cloud import firestore
from datetime import datetime

portfolio_bp = Blueprint('portfolio', __name__)

@portfolio_bp.route('/portfolio')
@portfolio_bp.route('/portfolio/')
def portfolio():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    return view_portfolio(session['user_id'])

@portfolio_bp.route('/portfolio/<user_id>')
def view_portfolio(user_id):
    try:
        user = db.collection('users').document(user_id).get()
        if not user.exists:
            return "User not found", 404

        # Check and award any new badges
        check_and_award_badges(user_id)
        
        # Get portfolio data
        portfolios = db.collection('portfolios').where('user_id', '==', user_id).get()
        portfolio_data = []
        total_value = 0

        for entry in portfolios:
            entry_data = entry.to_dict()
            symbol, shares, purchase_price, asset_type = entry_data['symbol'], entry_data['shares'], entry_data['purchase_price'], entry_data['asset_type']
            latest_price = fetch_asset_price(symbol, asset_type, purchase_price)
            asset_value = round(shares * latest_price, 2)
            profit_loss = calculate_profit_loss(latest_price, purchase_price)

            portfolio_data.append({
                'symbol': symbol,
                'asset_type': asset_type,
                'shares': shares,
                'purchase_price': purchase_price,
                'latest_price': latest_price,
                'value': asset_value,
                'profit_loss': profit_loss
            })
            total_value += asset_value

        # Fetch badges with proper error handling
        try:
            user_badges = fetch_user_badges(user_id)
            print(f"Successfully fetched {len(user_badges)} badges for user {user_id}")
        except Exception as e:
            print(f"Error fetching badges: {e}")
            user_badges = []

        profile_picture = user.to_dict().get('profile_picture', url_for('static', filename='default-profile.png'))
        is_developer = user.to_dict().get('username') == 'xiao'

        return render_template('portfolio.html.jinja2', 
                           user=user.to_dict(), 
                           profile_picture=profile_picture, 
                           portfolio=portfolio_data, 
                           total_value=round(total_value, 2), 
                           badges=user_badges, 
                           is_developer=is_developer)

    except Exception as e:
        print(f"Error in view_portfolio: {e}")
        return "An error occurred", 500

@portfolio_bp.route('/history')
def transaction_history():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    transactions = db.collection('transactions').where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).get()
    history = [format_transaction(t.to_dict()) for t in transactions]

    return render_template('history.html.jinja2', history=history)

@portfolio_bp.route('/developer_tools', methods=['GET', 'POST'])
def developer_tools():
    if 'user_id' not in session:
        print("No user_id in session, redirecting to login")
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    user = user_ref.get().to_dict()

    if user.get('username') != 'xiao':
        print(f"Access denied for user {user.get('username')}, not authorized")
        return "Access denied", 403

    print("\n=== ACCESSING DEVELOPER TOOLS ===")
    print(f"Logged in as: {user.get('username')} (ID: {user_id})")

    # Fetch all users for the dropdowns
    all_users = []
    try:
        print("Fetching all users for dropdown menus...")
        users_ref = db.collection('users').stream()
        for user_doc in users_ref:
            user_data = user_doc.to_dict()
            if user_data:  # Make sure we have valid user data
                all_users.append({
                    'id': user_doc.id,
                    'username': user_data.get('username', 'Unknown')
                })
                print(f"Found user: {user_data.get('username', 'Unknown')} with ID: {user_doc.id}")
        
        print(f"Total users found: {len(all_users)}")
        
        # Sort users alphabetically by username
        all_users.sort(key=lambda x: x['username'].lower())
        
    except Exception as e:
        print(f"Error fetching users: {e}")
        all_users = []

    if request.method == 'POST':
        print("\n=== PROCESSING FORM SUBMISSION ===")
        
        # Debug print all form data
        print("Form Data Received:")
        for key, value in request.form.items():
            print(f"  {key}: {value}")
            
        target_user_id = request.form.get('target_user_id')
        action = request.form.get('action')
        
        print(f"Action: {action}")
        print(f"Target User ID: {target_user_id}")
        
        if not target_user_id:
            print("ERROR: No target user selected")
            flash('No target user selected', 'error')
            return redirect(url_for('portfolio.developer_tools'))
            
        target_user_ref = db.collection('users').document(target_user_id)
        target_user = target_user_ref.get().to_dict()

        if not target_user:
            print(f"ERROR: Target user with ID {target_user_id} not found")
            flash('Target user not found', 'error')
            return redirect(url_for('portfolio.developer_tools'))

        print(f"Target user found: {target_user.get('username')}")

        if action == 'add_money':
            amount = float(request.form.get('amount', 0))
            new_balance = target_user.get('balance', 0) + amount
            target_user_ref.update({'balance': new_balance})
            print(f"Added ${amount} to user {target_user.get('username')}'s balance. New balance: ${new_balance}")
            flash(f"Added ${amount} to user's balance", 'success')
            
        elif action == 'remove_money':
            amount = float(request.form.get('amount', 0))
            new_balance = max(0, target_user.get('balance', 0) - amount)
            target_user_ref.update({'balance': new_balance})
            print(f"Removed ${amount} from user {target_user.get('username')}'s balance. New balance: ${new_balance}")
            flash(f"Removed ${amount} from user's balance", 'success')
            
        elif action == 'modify_property':
            property_name = request.form.get('property_name')
            property_value = request.form.get('property_value')
            target_user_ref.update({property_name: property_value})
            print(f"Modified property {property_name} to {property_value} for user {target_user.get('username')}")
            flash(f"Modified user property: {property_name}", 'success')
            
        elif action == 'add_badge':
            badge_id = request.form.get('badge_id')
            print(f"\n=== AWARDING BADGE ===")
            print(f"Badge ID: {badge_id}")
            print(f"Target User ID: {target_user_id}")
            print(f"Target Username: {target_user.get('username')}")
            
            if badge_id:
                from services.badge_services import award_badge, ACHIEVEMENTS
                
                # Verify badge exists in ACHIEVEMENTS
                print(f"Verifying badge '{badge_id}' exists in ACHIEVEMENTS dictionary...")
                if badge_id in ACHIEVEMENTS:
                    print(f"Badge '{badge_id}' found in ACHIEVEMENTS: {ACHIEVEMENTS[badge_id]}")
                else:
                    print(f"WARNING: Badge '{badge_id}' NOT FOUND in ACHIEVEMENTS dictionary!")
                
                # Attempt to award the badge
                print(f"Calling award_badge({target_user_id}, {badge_id})...")
                success = award_badge(target_user_id, badge_id)
                
                if success:
                    print(f"SUCCESS: Badge '{badge_id}' awarded to {target_user.get('username')}")
                    flash(f"Badge '{badge_id}' awarded successfully to user", 'success')
                else:
                    print(f"FAILURE: Could not award badge '{badge_id}' to {target_user.get('username')}")
                    flash(f"Failed to award badge '{badge_id}' or user already has this badge", 'error')
            else:
                print("ERROR: No badge ID selected")
                flash('No badge ID selected', 'error')
        
        elif action == 'add_stock_or_crypto':
            symbol = request.form.get('symbol', '').upper()
            shares = float(request.form.get('shares', 0))
            asset_type = request.form.get('asset_type')
            
            print(f"Adding {shares} shares of {symbol} ({asset_type}) to {target_user.get('username')}'s portfolio")
            
            if symbol and shares > 0 and asset_type:
                db.collection('portfolios').add({
                    'user_id': target_user_id,
                    'symbol': symbol,
                    'shares': shares,
                    'asset_type': asset_type,
                    'purchase_price': 0,  # Default values
                    'total_cost': 0,      # Default values
                    'last_updated': firestore.SERVER_TIMESTAMP
                })
                print(f"Successfully added {shares} shares of {symbol}")
                flash(f"Added {shares} shares of {symbol} to user's portfolio", 'success')
            else:
                print(f"ERROR: Invalid asset parameters - Symbol: {symbol}, Shares: {shares}, Type: {asset_type}")
                flash('Invalid asset parameters', 'error')
        else:
            print(f"ERROR: Unknown action type: '{action}'")
            flash(f"Unknown action: {action}", 'error')

        print("Redirecting back to developer tools page")
        return redirect(url_for('portfolio.developer_tools'))

    # Get available badge IDs from constants
    from utils.constants import ACHIEVEMENTS
    available_badges = ACHIEVEMENTS
    
    print(f"Available badges: {list(available_badges.keys())}")
    print("Rendering developer_tools template")

    return render_template('developer_tools.html.jinja2', 
                         user=user, 
                         all_users=all_users,
                         available_badges=available_badges)

# Helper functions
def fetch_asset_price(symbol, asset_type, fallback_price):
    try:
        if asset_type == 'stock':
            stock_data = fetch_stock_data(symbol)
            return stock_data.get('close', fallback_price)
        elif asset_type == 'crypto':
            crypto_data = fetch_crypto_data(symbol)
            return crypto_data.get('price', fallback_price)
    except Exception as e:
        print(f"Error fetching price for {symbol}: {e}")
    return fallback_price

def calculate_profit_loss(latest_price, purchase_price):
    if purchase_price > 0:
        return round((latest_price - purchase_price) / purchase_price * 100, 2)
    return None

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
                # Try to get badge from badges collection
                badges_query = db.collection('badges').where('name', '==', badge_id).limit(1).stream()
                badge_found = False
                
                for badge in badges_query:
                    badge_found = True
                    badge_dict = badge.to_dict()
                    badge_data.append({
                        'name': badge_dict.get('name', badge_id),
                        'description': badge_dict.get('description', 'No description available'),
                        'awarded_at': badge_info.get('awarded_at'),
                        'badge_id': badge_id
                    })
                
                # If no matching badge found in badges collection, use default data
                if not badge_found:
                    # Check if badge exists in ACHIEVEMENTS constant
                    from utils.constants import ACHIEVEMENTS
                    if badge_id in ACHIEVEMENTS:
                        badge_data.append({
                            'name': ACHIEVEMENTS[badge_id]['name'],
                            'description': ACHIEVEMENTS[badge_id]['description'],
                            'awarded_at': badge_info.get('awarded_at'),
                            'badge_id': badge_id
                        })
                    else:
                        # Use placeholder data if nothing else is available
                        badge_data.append({
                            'name': badge_id.replace('_', ' ').title(),
                            'description': 'Achievement unlocked',
                            'awarded_at': badge_info.get('awarded_at'),
                            'badge_id': badge_id
                        })

        return sorted(badge_data, key=lambda x: x['awarded_at'] if x['awarded_at'] else datetime.now(), reverse=True)
        
    except Exception as e:
        print(f"Error fetching badges for user {user_id}: {str(e)}")
        return []

def format_transaction(transaction):
    return {
        'date': transaction['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
        'type': transaction['transaction_type'],
        'symbol': transaction['symbol'],
        'shares': transaction['shares'],
        'price': transaction['price'],
        'total': transaction['total_amount'],
        'profit_loss': round(transaction.get('profit_loss', 0.0), 2)
    }

def handle_developer_action(form, user_id, user_ref):
    action = form.get('action')
    if action == 'add_stock_or_crypto':
        db.collection('portfolios').add({
            'user_id': user_id,
            'symbol': form.get('symbol').upper(),
            'shares': float(form.get('shares')),
            'asset_type': form.get('asset_type'),
            'purchase_price': 0,
            'total_cost': 0,
            'last_updated': firestore.SERVER_TIMESTAMP
        })
    elif action == 'add_badge':
        db.collection('user_badges').add({
            'user_id': user_id,
            'badge_id': form.get('badge_id'),
            'awarded_at': firestore.SERVER_TIMESTAMP
        })
    elif action == 'add_money':
        amount = float(form.get('amount'))
        new_balance = user_ref.get().to_dict().get('balance', 0) + amount
        user_ref.update({'balance': new_balance})
