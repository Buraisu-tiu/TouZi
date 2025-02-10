import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_caching import Cache
from celery import Celery
from flask_htmlmin import HTMLMIN
import logging
from logging import FileHandler, Formatter
import random
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta, timezone
import finnhub
import plotly.express as px
import pandas as pd
from coinbase.wallet.client import Client
from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials
import google.cloud.logging
from google.cloud.logging import Client
import google.auth
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import flash, session, redirect, url_for
import logging
from flask import jsonify, render_template, session
import yfinance as yf
from pycoingecko import CoinGeckoAPI as cg
# Specify the time zone
tz = timezone.utc

# Get the current time in the specified time zone
now = datetime.now(tz)
# Load the service account key file

credentials, project_id = google.auth.load_credentials_from_file(
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'],
    scopes=['https://www.googleapis.com/auth/firestore']
)

project_id = "stock-trading-simulator-b6e27"
client = google.cloud.logging.Client(credentials=credentials, project=project_id)



logging.basicConfig(level=logging.INFO)
# Create Firestore client
db = firestore.Client(project='stock-trading-simulator-b6e27')
print("Firestore client created:", db)
cg = cg()

# Enable Google Cloud logging
client = Client()
client.setup_logging()


    
app = Flask(__name__, static_folder='static')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
HTMLMIN(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
celery = Celery(app.name, broker='redis://localhost:6379/0')

celery.conf.update(app.config)
def hex_to_rgb(hex_color):
    """Convert hex color to RGB string"""
    try:
        hex_color = hex_color.lstrip('#')
        return f"{int(hex_color[:2], 16)}, {int(hex_color[2:4], 16)}, {int(hex_color[4:], 16)}"
    except:
        return "0, 0, 0"  # Default to black if conversion fails

def lighten_color(hex_color, amount=10):
    """Lighten a hex color by a specified amount"""
    try:
        hex_color = hex_color.lstrip('#')
        rgb = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
        
        # Lighten each component
        lightened = [min(255, int(component + amount)) for component in rgb]
        
        return f"#{lightened[0]:02x}{lightened[1]:02x}{lightened[2]:02x}"
    except:
        return hex_color  # Return original color if conversion fails
    
    
# Add this to your app initialization or before first request

def register_template_filters():
    app.jinja_env.filters['hex_to_rgb'] = hex_to_rgb
    app.jinja_env.filters['lighten_color'] = lighten_color
    
    
register_template_filters()
# Setup detailed logging
file_handler = FileHandler('errorlog.txt')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
print(file_handler)


    
# List of API keys
api_keys = [
    'ctitlv1r01qgfbsvh1dgctitlv1r01qgfbsvh1e0',
    'ctitnthr01qgfbsvh59gctitnthr01qgfbsvh5a0',
    'ctjgjm1r01quipmu2qi0ctjgjm1r01quipmu2qig'
]

# Coinbase configuration
coinbase_api_key = 'your_coinbase_api_key'
coinbase_api_secret = 'your_coinbase_api_secret'

app.secret_key = 'your_secret_key'

def get_random_api_key():
    return random.choice(api_keys)
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
        portfolio_refs = db.collection('portfolios').where('user_id', '==', user_id).stream()
        portfolio_items = [item.to_dict() for item in portfolio_refs]
        
        # Get transaction history
        transactions = db.collection('transactions').where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
        
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


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/')
def home():
    create_badges()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db.collection('users').add({
            'username': username,
            'password': password,
            'balance': 990.00,
            'background_color': '#000000',
            'text_color': '#ffffff',
            'accent_color': '#007bff',
            'gradient_color': "#000000"
        
        })
        return redirect(url_for('login'))
    return render_template('register.html.jinja2')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"Login attempt: Username: {username}, Password: {password}")

        try:
            print("Attempting to test firestore test query")
            test_query = db.collection('users').limit(1).get()
            print(f"Firestore test query succeeded. Found {len(test_query)} document(s).")
        except Exception as e:
            print(f"Firestore test query failed: {e}")


        try:
            # Query Firestore for the username
            print("Attempting to query Firestore...")
            users_ref = db.collection('users').where('username', '==', username).get()
            print(f"Query executed. Retrieved {len(users_ref)} document(s).")

            if not users_ref:
                print(f"No user found with username: {username}")
                return 'Invalid credentials'

            # Validate the password
            for user in users_ref:
                user_data = user.to_dict()
                print(f"User data: {user_data}")
                if user_data.get('password') == password:
                    print(f"User {username} authenticated successfully.")
                    session['user_id'] = user.id
                    return redirect(url_for('dashboard'))
                else:
                    print(f"Invalid password for username: {username}")
                    return 'Invalid credentials'
        except Exception as e:
            print(f"Error during login: {e}")
            return 'An error occurred'
    
    return render_template('login.html.jinja2')



@app.route('/dashboard')
def dashboard():
    
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    transactions_ref = db.collection('transactions').where('user_id', '==', user_id).where('transaction_type', '==', 'SELL').where('profit_loss', '!=', 0).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(5)
    transactions = transactions_ref.stream()
    history = []
    for t in transactions:
        t_data = t.to_dict()
        history.append({
            'date': t_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
            'type': t_data['transaction_type'],
            'symbol': t_data['symbol'],
            'shares': t_data['shares'],
            'price': t_data['price'],
            'total': t_data['total_amount'],
            'profit_loss': round(t_data.get('profit_loss', 0.0), 2)
        })
    success = request.args.get('success')
    return render_template('dashboard.html.jinja2', user=user, transactions=history, success=success)
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    
    if request.method == 'POST':
        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # Update Firestore with the profile picture path
                user_ref.update({'profile_picture': url_for('static', filename=f'uploads/{filename}')})

        # Update other user settings
        user_ref.update({
            'background_color': request.form.get('background_color', '#ffffff'),
            'text_color': request.form.get('text_color', '#000000'),
            'accent_color': request.form.get('accent_color', '#007bff'),
            'gradient_color': request.form.get('gradient_color', "#000000")
        })
        return redirect(url_for('dashboard'))
    
    user = user_ref.get().to_dict()
    return render_template('settings.html.jinja2', user=user)

from flask import jsonify, request, session, render_template
from firebase_admin import firestore

@app.route('/leaderboard')
def leaderboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    user_data = user_ref.get().to_dict()
    
    # Fetch group leaderboards where user is a member
    group_refs = db.collection('group_leaderboards')\
        .where('member_ids', 'array_contains', user_id)\
        .stream()
    
    group_leaderboards = []
    for group in group_refs:
        group_data = group.to_dict()
        group_data['id'] = group.id
        group_leaderboards.append(group_data)

    return render_template('leaderboard.html.jinja2', 
                         user=user_data, 
                         group_leaderboards=group_leaderboards)

@app.route('/api/leaderboard-data')
def leaderboard_data():
    try:
        # Get current user's ID for group leaderboard filtering
        current_user_id = session.get('user_id')
        
        # Fetch all users for global leaderboard
        users = db.collection('users').stream()
        global_leaderboard = []
        
        for user in users:
            user_data = user.to_dict()
            portfolio_query = db.collection('portfolios')\
                .where('user_id', '==', user.id)\
                .stream()
            
            # Calculate total account value
            account_value = user_data.get('balance', 0)
            for item in portfolio_query:
                item_data = item.to_dict()
                current_price = 0
                
                if item_data['asset_type'] == 'stock':
                    stock_data = fetch_stock_data(item_data['symbol'])
                    current_price = stock_data.get('close', 0)
                elif item_data['asset_type'] == 'crypto':
                    crypto_data = fetch_crypto_data(item_data['symbol'])
                    current_price = crypto_data.get('price', 0)
                
                share_value = item_data.get('shares', 0) * current_price
                account_value += share_value

            global_leaderboard.append({
                'id': user.id,
                'username': user_data.get('username', 'Unknown'),
                'account_value': round(account_value, 2),
                'profile_picture': user_data.get('profile_picture', ''),
                'accent_color': user_data.get('accent_color', '#007bff'),
                'text_color': user_data.get('text_color', '#ffffff')
            })

        # Sort global leaderboard by account value
        global_leaderboard.sort(key=lambda x: x['account_value'], reverse=True)
        
        # Fetch group leaderboards for current user
        group_leaderboards = []
        if current_user_id:
            group_refs = db.collection('group_leaderboards')\
                .where('member_ids', 'array_contains', current_user_id)\
                .stream()
            
            for group in group_refs:
                group_data = group.to_dict()
                member_data = []
                
                # Fetch data for each member in the group
                for member_id in group_data.get('member_ids', []):
                    member = next((u for u in global_leaderboard if u['id'] == member_id), None)
                    if member:
                        member_data.append(member)
                
                # Sort group members by account value
                member_data.sort(key=lambda x: x['account_value'], reverse=True)
                
                group_leaderboards.append({
                    'id': group.id,
                    'name': group_data.get('name', 'Unnamed Group'),
                    'members': member_data,
                    'created_by': group_data.get('created_by')
                })

        return jsonify({
            'status': 'success',
            'global_leaderboard': global_leaderboard,
            'group_leaderboards': group_leaderboards
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/create_group_leaderboard', methods=['POST'])
def create_group_leaderboard():
    if 'user_id' not in session:
        return jsonify({'error': 'User not authenticated'}), 401

    user_id = session['user_id']
    data = request.json
    
    if not data.get('name'):
        return jsonify({'error': 'Group name is required'}), 400

    try:
        new_group = {
            'name': data['name'],
            'created_by': user_id,
            'member_ids': [user_id],  # Start with creator as only member
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        # Create new group leaderboard
        group_ref = db.collection('group_leaderboards').add(new_group)
        
        return jsonify({
            'success': True,
            'message': 'Group leaderboard created',
            'id': group_ref[1].id
        })

    except Exception as e:
        return jsonify({
            'error': f'Failed to create group leaderboard: {str(e)}'
        }), 500

@app.route('/group_leaderboard/<group_id>/leave', methods=['POST'])
def leave_group(group_id):
    if 'user_id' not in session:
        return jsonify({'error': 'User not authenticated'}), 401

    user_id = session['user_id']

    try:
        group_ref = db.collection('group_leaderboards').document(group_id)
        group = group_ref.get()

        if not group.exists:
            return jsonify({'error': 'Group not found'}), 404

        group_data = group.to_dict()
        member_ids = group_data.get('member_ids', [])

        if user_id not in member_ids:
            return jsonify({'error': 'You are not a member of this group'}), 400

        # Remove the user from the group
        group_ref.update({
            'member_ids': firestore.ArrayRemove([user_id])
        })

        return jsonify({
            'success': True,
            'message': 'Successfully left the group'
        })

    except Exception as e:
        return jsonify({
            'error': f'Failed to leave group: {str(e)}'
        }), 500
        
        
@app.route('/group_leaderboard/<group_id>/add_member', methods=['POST'])
def add_group_member(group_id):
    if 'user_id' not in session:
        return jsonify({'error': 'User not authenticated'}), 401

    current_user_id = session['user_id']
    data = request.json
    member_username = data.get('username')

    if not member_username:
        return jsonify({'error': 'Username is required'}), 400

    try:
        # Get the group and verify the current user is the creator
        group_ref = db.collection('group_leaderboards').document(group_id)
        group = group_ref.get()
        
        if not group.exists:
            return jsonify({'error': 'Group not found'}), 404
            
        group_data = group.to_dict()
        if group_data['created_by'] != current_user_id:
            return jsonify({'error': 'Only the group creator can add members'}), 403

        # Find user by username
        user_query = db.collection('users')\
            .where('username', '==', member_username)\
            .limit(1)\
            .get()

        if not user_query:
            return jsonify({'error': 'User not found'}), 404

        new_member_id = user_query[0].id
        
        # Check if user is already a member
        if new_member_id in group_data.get('member_ids', []):
            return jsonify({'error': 'User is already a member'}), 400

        # Add the new member
        group_ref.update({
            'member_ids': firestore.ArrayUnion([new_member_id])
        })

        return jsonify({
            'success': True,
            'message': f'Added {member_username} to the group'
        })

    except Exception as e:
        return jsonify({
            'error': f'Failed to add member: {str(e)}'
        }), 500
        
def fetch_stock_data(symbol):
    try:
        finnhub_client = finnhub.Client(api_key=get_random_api_key())
        data = finnhub_client.quote(symbol)
        
        # Ensure the response contains valid data
        if not data:
            return {'error': 'Empty response from Finnhub API'}
        
        # Ensure all necessary keys are in the response
        required_keys = ['o', 'h', 'l', 'pc', 'c']  # Added 'c' for closing price
        missing_keys = [key for key in required_keys if key not in data]
        
        if missing_keys:
            return {'error': f'Missing keys {", ".join(missing_keys)} in response from Finnhub API'}
        
        # Return data with the required keys
        return {
            'symbol': symbol,
            'open': data.get('o', 0),          # Open price
            'high': data.get('h', 0),          # High price
            'low': data.get('l', 0),           # Low price
            'prev_close': data.get('pc', 0),   # Previous close price
            'close': data.get('c', 0)          # Closing price
        }
    
    except finnhub.exceptions.FinnhubAPIException as e:
        return {'error': f'Finnhub API error: {str(e)}'}
    except Exception as e:
        return {'error': f'Error fetching stock data: {str(e)}'}

@app.route('/sell', methods=['GET', 'POST'])
def sell():
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please log in to sell assets', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    user = user_ref.get().to_dict() or {}  # Provide a default empty dict if user is None

    # Handle GET request
    if request.method == 'GET':
        success = request.args.get('success', False)
        
        # Fetch user's portfolio
        portfolio_query = db.collection('portfolios').where('user_id', '==', user_id).get()
        
        # Prepare portfolio items for the dropdown
        portfolio_items = [
            {
                'symbol': item.to_dict()['symbol'], 
                'shares': item.to_dict()['shares'], 
                'asset_type': item.to_dict()['asset_type']
            } 
            for item in portfolio_query
        ]

        return render_template('sell.html.jinja2', 
                               portfolio_items=portfolio_items, 
                               success=success, 
                               user=user)

    # Handle POST request
    if request.method == 'POST':
        try:
            # Validate form inputs
            symbol = request.form['symbol'].upper()
            shares_to_sell = float(request.form['shares'])
            
            # Validate inputs
            if not symbol or shares_to_sell <= 0:
                flash('Invalid symbol or quantity', 'error')
                return redirect(url_for('sell'))

            # Get current user
            user_id = session['user_id']
            user_ref = db.collection('users').document(user_id)
            user = user_ref.get().to_dict()

            if not user:
                flash('User not found', 'error')
                return redirect(url_for('login'))

            # Find the portfolio entry for this symbol
            portfolio_query = db.collection('portfolios').where('user_id', '==', user_id).where('symbol', '==', symbol).limit(1).get()
            
            if not portfolio_query:
                flash(f'You do not own any {symbol}', 'error')
                return redirect(url_for('sell'))

            # Get portfolio details
            portfolio = portfolio_query[0]
            portfolio_data = portfolio.to_dict()
            
            # Check if user has enough shares
            if portfolio_data['shares'] < shares_to_sell:
                flash(f'Insufficient shares. You only have {portfolio_data["shares"]} {symbol}', 'error')
                return redirect(url_for('sell'))

            # Fetch current market price
            if portfolio_data['asset_type'] == 'stock':
                stock_data = fetch_stock_data(symbol)
                if 'error' in stock_data:
                    flash(f"Error fetching stock data: {stock_data['error']}", 'error')
                    return redirect(url_for('sell'))
                
                current_price = stock_data['close']

            elif portfolio_data['asset_type'] == 'crypto':
                try:
                    response = requests.get(f'https://api.coinbase.com/v2/prices/{symbol}-USD/spot')
                    response.raise_for_status()
                    data = response.json()
                    current_price = float(data['data']['amount'])
                except requests.exceptions.RequestException as e:
                    flash(f"Failed to fetch cryptocurrency data: {e}", 'error')
                    return redirect(url_for('sell'))
            else:
                flash('Invalid asset type', 'error')
                return redirect(url_for('sell'))

            # Calculate sale details
            sale_amount = current_price * shares_to_sell
            remaining_shares = portfolio_data['shares'] - shares_to_sell

            # Update portfolio
            if remaining_shares > 0:
                portfolio.reference.update({
                    'shares': remaining_shares
                })
            else:
                # Remove the portfolio entry if no shares left
                portfolio.reference.delete()

            # Update user balance
            new_balance = round(user['balance'] + sale_amount, 2)
            user_ref.update({'balance': new_balance})

            # Record transaction
            db.collection('transactions').add({
                'user_id': user_id,
                'symbol': symbol,
                'shares': shares_to_sell,
                'price': current_price,
                'total_amount': sale_amount,
                'transaction_type': 'SELL',
                'asset_type': portfolio_data['asset_type'],
                'timestamp': datetime.utcnow()
            })


            # Flash success message
            check_and_award_badges(user_id)
            flash(f'Successfully sold {shares_to_sell} {symbol} for ${sale_amount:.2f}', 'success')
            return redirect(url_for('sell', success=True))

        except ValueError as e:
            flash('Invalid input. Please check your entries.', 'error')
            return redirect(url_for('sell'))
        
        except Exception as e:
            # Log unexpected errors
            app.logger.error(f"Unexpected error in sell function: {e}")
            flash('An unexpected error occurred. Please try again.', 'error')
            return redirect(url_for('sell'))

    # Fallback for any other scenarios
    return render_template('sell.html.jinja2')
    
@app.route('/portfolio/<string:user_id>')
def view_portfolio(user_id):
    user = db.collection('users').document(user_id).get()
    if not user.exists:
        return "User not found", 404

    # Check badges when viewing individual portfolio
    try:
        print(f"Checking badges for user {user_id} during portfolio view")
        check_and_award_badges(user_id)
    except Exception as e:
        print(f"Error checking badges for user {user_id}: {str(e)}")

    portfolios = db.collection('portfolios').where('user_id', '==', user_id).get()
    if not portfolios:
        return render_template('portfolio.html.jinja2', user=user.to_dict(), portfolio=[], total_value=0)

    portfolio_data = []
    total_value = 0
    badges = db.collection('user_badges').where('user_id', '==', user_id).get()
    badge_data = []
    for badge in badges:
        badge_ref = db.collection('badges').document(badge.to_dict()['badge_id']).get()
        badge_data.append({
            'name': badge_ref.to_dict()['name'],
            'description': badge_ref.to_dict()['description']
        })

    profile_picture = user.to_dict().get('profile_picture', url_for('static', filename='default-profile.png'))

    for entry in portfolios:
        entry_data = entry.to_dict()
        symbol = entry_data['symbol']
        shares = round(entry_data['shares'], 2)
        purchase_price = round(entry_data['purchase_price'], 2)
        asset_type = entry_data['asset_type']
        if asset_type == 'stock':
            stock_data = fetch_stock_data(symbol)
            if 'error' in stock_data:
                return stock_data['error']
            latest_price = stock_data['close']
        elif asset_type == 'crypto':
            try:
                response = requests.get(f'https://api.coinbase.com/v2/prices/{symbol}-USD/spot')
                response.raise_for_status()
                data = response.json()
                latest_price = round(float(data['data']['amount']), 2)
            except requests.exceptions.RequestException:
                latest_price = purchase_price
        asset_value = round(shares * latest_price, 2)
        if purchase_price != 0:
            profit_loss = round((latest_price - purchase_price) / purchase_price * 100, 2)
        else:
            profit_loss = None
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
    session['loading_leaderboard'] = False
    return render_template('portfolio.html.jinja2', user=user.to_dict(), profile_picture=profile_picture, portfolio=portfolio_data, total_value=round(total_value, 2), badges=badge_data)


def fetch_crypto_data(symbol):
    url = f'https://api.coinbase.com/v2/prices/{symbol}-USD/spot'
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return {'price': float(data['data']['amount'])}




# Add this route to your Flask application
@app.route('/popular_stocks')
def popular_stocks():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    
    # List of top 50 commonly traded stocks with their company names
    popular_stocks = [
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
    
    return render_template('popular_stocks.html.jinja2', stocks=popular_stocks, user=user)

@app.route('/history')
def transaction_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    transactions = db.collection('transactions').where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).get()
    
    history = []
    for t in transactions:
        t_data = t.to_dict()
        history.append({
            'date': t_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
            'type': t_data['transaction_type'],
            'symbol': t_data['symbol'],
            'shares': t_data['shares'],
            'price': t_data['price'],
            'total': t_data['total_amount'],
            'profit_loss': round(t_data.get('profit_loss', 0.0), 2)
        })
    
    return render_template('history.html.jinja2', history=history, user=user)


def fetch_market_overview():

    try:

        # Fetch S&P 500 data

        sp500 = yf.Ticker("^GSPC")

        sp500_data = sp500.history(period="1d")

        sp500_change = ((sp500_data['Close'].iloc[-1] - sp500_data['Open'].iloc[0]) / sp500_data['Open'].iloc[0]) * 100


        # Fetch BTC/USD data

        btc_data = cg.get_price(ids='bitcoin', vs_currencies='usd', include_24hr_change=True)

        btc_change = btc_data['bitcoin']['usd_24h_change']


        # Fetch total crypto market volume

        global_data = cg.get_global()

        market_volume = global_data['total_volume']['usd'] / 1e9  # Convert to billions


        return {

            'S&P 500': f"{sp500_change:.2f}%",

            'BTC/USD': f"{btc_change:.2f}%",

            'Market Volume': f"${market_volume:.2f}B"

        }

    except Exception as e:

        print(f"Error fetching market overview: {e}")

        return {

            'S&P 500': 'N/A',

            'BTC/USD': 'N/A',

            'Market Volume': 'N/A'

        }

def fetch_user_portfolio(user_id):
    user_ref = db.collection('users').document(user_id)
    user = user_ref.get().to_dict()
    portfolio_query = db.collection('portfolios').where('user_id', '==', user_id).stream()
    
    total_value = user['balance']
    previous_day_value = user['balance']  # Start with the balance for previous day's value
    for item in portfolio_query:
        item_data = item.to_dict()
        if item_data['asset_type'] == 'stock':
            price_data = fetch_stock_data(item_data['symbol'])
            if 'error' not in price_data:
                current_price = price_data['close']
                total_value += current_price * item_data['shares']
                
                # Fetch previous day's closing price
                previous_day_data = fetch_historical_data(item_data['symbol'])
                if previous_day_data is not None and not previous_day_data.empty:
                    previous_close = previous_day_data['close'].iloc[-1]  # Get the last closing price
                    previous_day_value += previous_close * item_data['shares']
        elif item_data['asset_type'] == 'crypto':
            price_data = fetch_crypto_data(item_data['symbol'])
            if 'error' not in price_data:
                current_price = price_data['price']
                total_value += current_price * item_data['shares']
                
                # Fetch previous day's closing price for crypto
                previous_day_data = fetch_historical_data(item_data['symbol'])
                if previous_day_data is not None and not previous_day_data.empty:
                    previous_close = previous_day_data['close'].iloc[-1]  # Get the last closing price
                    previous_day_value += previous_close * item_data['shares']

    # Calculate today's change
    todays_change = total_value - previous_day_value

    return {
        'Total Value': f'${total_value:.2f}',
        "Today's Change": f'${todays_change:.2f}',  # Format today's change
        'Available Cash': f'${user["balance"]:.2f}'
    }

def calculate_price_change(current: float, previous: float) -> tuple[float, str]:
    """
    Calculate price change and percentage safely.
    Returns: (percentage_change, formatted_change_string)
    """
    try:
        if previous <= 0:
            return (0.0, "N/A")
            
        change_percentage = ((current - previous) / previous) * 100
        change_str = f"{change_percentage:+.2f}%"
        return (change_percentage, change_str)
    except (TypeError, ZeroDivisionError):
        return (0.0, "N/A")

def fetch_watchlist(user_id: str) -> list[dict]:
    """
    Fetch and process user's watchlist with safe price calculations.
    """
    try:
        # Get the watchlist document for the user
        watchlist_ref = db.collection('watchlists').document(user_id)
        watchlist_doc = watchlist_ref.get()

        if not watchlist_doc.exists:
            return []  # Return an empty list if the watchlist does not exist

        # Get the symbols from the watchlist document
        watchlist_data = watchlist_doc.to_dict()
        symbols = watchlist_data.get('symbols', [])

        processed_items = []

        for symbol in symbols:
            # Determine asset type based on the symbol format
            asset_type = 'crypto' if symbol.startswith('CRYPTO:') else 'stock'
            symbol_name = symbol.replace('CRYPTO:', '')  # Remove prefix for fetching data

            try:
                if asset_type == 'stock':
                    price_data = fetch_stock_data(symbol_name)
                else:
                    price_data = fetch_crypto_data(symbol_name)

                if not price_data or 'error' in price_data:
                    continue

                current_price = price_data.get('close') or price_data.get('price', 0)
                prev_price = price_data.get('prev_close', current_price)

                change_pct, change_str = calculate_price_change(current_price, prev_price)

                processed_items.append({
                    'symbol': symbol_name,
                    'asset_type': asset_type,
                    'current_price': f"${current_price:.2f}",
                    'price_change': change_str,
                    'change_percentage': change_pct,
                    'added_date': watchlist_data.get('added_date', datetime.utcnow()),
                    'notes': watchlist_data.get('notes', ''),
                    'alert_price': watchlist_data.get('alert_price')
                })

            except Exception as e:
                app.logger.error(f"Error processing watchlist item {symbol}: {str(e)}")
                continue

        # Sort by absolute change percentage
        return sorted(processed_items, 
                      key=lambda x: abs(x['change_percentage']), 
                      reverse=True)

    except Exception as e:
        app.logger.error(f"Error fetching watchlist: {str(e)}")
        return []

def fetch_recent_orders(user_id, limit=5):
    orders_query = db.collection('transactions').where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
    orders = []
    for order in orders_query.stream():
        order_data = order.to_dict()
        orders.append({
            'Date': order_data['timestamp'].strftime('%Y-%m-%d'),
            'Symbol': order_data['symbol'],
            'Type': order_data['asset_type'],
            'Quantity': order_data['shares'],
            'Status': 'Completed'  # You might want to add a status field to your transactions
        })
    return orders


    
    
# Modify the existing buy route to include the new data
@app.route('/buy', methods=['GET', 'POST'])
def buy():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    user = user_ref.get().to_dict()

    if request.method == 'POST':
        try:
            symbol = request.form.get('symbol', '').upper().strip()
            shares = float(request.form.get('shares'))
            asset_type = request.form.get('asset_type')

            if shares <= 0 or not symbol or len(symbol) > 10:
                flash('Invalid input', 'error')
                return redirect(url_for('buy'))

            # Fetch current price
            if asset_type == 'stock':
                price_data = fetch_stock_data(symbol)
                if 'error' in price_data:
                    flash(price_data['error'], 'error')
                    return redirect(url_for('buy'))
                price = price_data['close']
            elif asset_type == 'crypto':
                price_data = fetch_crypto_data(symbol)
                if 'error' in price_data:
                    flash(price_data['error'], 'error')
                    return redirect(url_for('buy'))
                price = price_data['price']
            else:
                flash('Invalid asset type', 'error')
                return redirect(url_for('buy'))

            total_cost = round(price * shares, 2)

            # Check funds
            if total_cost > user['balance']:
                flash(f'Insufficient funds. Need ${total_cost:.2f}, have ${user["balance"]:.2f}', 'error')
                return redirect(url_for('buy'))

            # Process purchase
            portfolio_query = db.collection('portfolios').where('user_id', '==', user_id).where('symbol', '==', symbol).limit(1).get()
            
            if portfolio_query:
                portfolio_doc = portfolio_query[0]
                portfolio_data = portfolio_doc.to_dict()
                new_shares = portfolio_data['shares'] + shares
                new_total_cost = portfolio_data.get('total_cost', 0) + total_cost
                
                portfolio_doc.reference.update({
                    'shares': new_shares,
                    'total_cost': new_total_cost,
                    'last_updated': datetime.utcnow()
                })
            else:
                db.collection('portfolios').add({
                    'user_id': user_id,
                    'symbol': symbol,
                    'shares': shares,
                    'asset_type': asset_type,
                    'total_cost': total_cost,
                    'purchase_price': price,
                    'last_updated': datetime.utcnow()
                })

            # Update user balance
            new_balance = round(user['balance'] - total_cost, 2)
            user_ref.update({'balance': new_balance})

            # Record transaction
            db.collection('transactions').add({
                'user_id': user_id,
                'symbol': symbol,
                'shares': shares,
                'price': price,
                'total_amount': total_cost,
                'transaction_type': 'BUY',
                'asset_type': asset_type,
                'timestamp': datetime.utcnow()
            })

            # Check for badges
            check_and_award_badges(user_id)

            flash(f'Successfully purchased {shares} {symbol} for ${total_cost:.2f}', 'success')
            return redirect(url_for('buy'))

        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'error')
            return redirect(url_for('buy'))
        except Exception as e:
            flash(f'Transaction failed: {str(e)}', 'error')
            return redirect(url_for('buy'))

    # Fetch additional data for the enhanced buy page
    market_overview = fetch_market_overview()
    user_portfolio = fetch_user_portfolio(user_id)
    watchlist = fetch_watchlist(user_id)
    print("Watchlist data:", watchlist)  # Debugging line
    recent_orders = fetch_recent_orders(user_id)
    
    return render_template('buy.html.jinja2', 
                           user=user, 
                           market_overview=market_overview,
                           user_portfolio=user_portfolio,
                           watchlist=watchlist,
                           recent_orders=recent_orders)
# Add a new route to handle real-time order summary updates
@app.route('/api/order_summary', methods=['POST'])
def order_summary():
    if 'user_id' not in session:
        return jsonify({'error': 'User not authenticated'}), 401

    data = request.json
    symbol = data.get('symbol')
    quantity = data.get('quantity')
    asset_type = data.get('asset_type')

    if not symbol or not quantity or not asset_type:
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        quantity = float(quantity)
    except ValueError:
        return jsonify({'error': 'Invalid quantity'}), 400

    if asset_type == 'stock':
        price_data = fetch_stock_data(symbol)
        if 'error' in price_data:
            return jsonify({'error': price_data['error']}), 400
        price = price_data['close']
    elif asset_type == 'crypto':
        price_data = fetch_crypto_data(symbol)
        if 'error' in price_data:
            return jsonify({'error': price_data['error']}), 400
        price = price_data['price']
    else:
        return jsonify({'error': 'Invalid asset type'}), 400

    estimated_price = price * quantity
    trading_fee = estimated_price * 0.01  # Assume 1% trading fee
    total = estimated_price + trading_fee

    return jsonify({
        'estimated_price': f'${estimated_price:.2f}',  # Fix syntax
        'trading_fee': f'${trading_fee:.2f}',
        'total': f'${total:.2f}'
    })








@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)

    # Delete user's portfolio
    portfolio_query = db.collection('portfolios').where('user_id', '==', user_id)
    for doc in portfolio_query.stream():
        doc.reference.delete()

    # Delete user's transactions
    transaction_query = db.collection('transactions').where('user_id', '==', user_id)
    for doc in transaction_query.stream():
        doc.reference.delete()

    # Delete user's badges
    user_badges_query = db.collection('user_badges').where('user_id', '==', user_id)
    for doc in user_badges_query.stream():
        doc.reference.delete()

    # Delete the user document
    user_ref.delete()

    # Clear the session
    session.clear()

    return redirect(url_for('home'))


def award_badge(user_id, badge_name):
    user_ref = db.collection('users').document(user_id)
    badge_ref = db.collection('badges').where('name', '==', badge_name).limit(1).get()
    
    if not badge_ref:
        print(f"Badge {badge_name} not found")
        return
    badge_id = badge_ref[0].id
    user_badges_ref = db.collection('user_badges')
    
    existing_badge = user_badges_ref.where('user_id', '==', user_id).where('badge_id', '==', badge_id).limit(1).get()
    
    if not existing_badge:
        user_badges_ref.add({
            'user_id': user_id,
            'badge_id': badge_id,
            'date_earned': datetime.utcnow()
        })
        print(f"Awarded {badge_name} badge to user {user_id}")
    else:
        print(f"User {user_id} already has the {badge_name} badge")

@app.route('/api/add_to_watchlist', methods=['POST'])
def add_to_watchlist():
    if 'user_id' not in session:
        return jsonify({'error': 'User  not authenticated'}), 401

    user_id = session['user_id']
    data = request.json
    symbol = data.get('symbol')
    asset_type = data.get('asset_type')

    if not symbol or not asset_type:
        return jsonify({'error': 'Missing symbol or asset type'}), 400

    # Modify symbol for crypto
    if asset_type == 'crypto':
        symbol = f"CRYPTO:{symbol}"

    watchlist_ref = db.collection('watchlists').document(user_id)
    watchlist_doc = watchlist_ref.get()

    if watchlist_doc.exists:
        watchlist = watchlist_doc.to_dict()
        symbols = watchlist.get('symbols', [])
        print(f"Current symbols in watchlist: {symbols}")  # Debugging line

        if symbol not in symbols:
            symbols.append(symbol)
            watchlist_ref.update({'symbols': symbols})
            print(f"Updated symbols in watchlist: {symbols}")  # Debugging line
        else:
            print(f"Symbol {symbol} already exists in watchlist.")  # Debugging line
    else:
        watchlist_ref.set({'symbols': [symbol]})
        print(f"Created new watchlist for user {user_id} with symbol: {symbol}")  # Debugging line

    return jsonify({'success': True, 'message': 'Added to watchlist'})


@app.route('/plot/<symbol>', methods=['GET'])
def plot(symbol):
    df = fetch_historical_data(symbol)
    if df is not None:
        fig = px.line(df, x=df.index, y='close', title=f'Recent Price Changes for {symbol}')
        fig.update_layout(
            xaxis_title='Date',
            yaxis_title='Close Price',
            template='plotly_dark',
            plot_bgcolor='rgba(0, 0, 0, 0)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            font=dict(color='white'),
            xaxis=dict(gridcolor='gray'),
            yaxis=dict(gridcolor='gray')
        )

        graph_html = fig.to_html(full_html=False)

        # Store the plot data in Firebase
        plot_ref = db.collection('plots').document(symbol)
        existing_plot = plot_ref.get()
        if not existing_plot.exists:
            plot_ref.set({
                'symbol': symbol,
                'graph_html': graph_html,
                'timestamp': datetime.utcnow()
            })

        return render_template('plot.html.jinja2', graph_html=graph_html, symbol=symbol)
    else:
        return "Failed to fetch stock data."
    
@app.route('/lookup', methods=['GET', 'POST'])
def lookup():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    graph_html = None
    error_message = None
    stock_data = None
    
    # Get symbol from either POST data or URL parameters
    symbol = request.form.get('symbol', request.args.get('symbol', '')).upper().strip()
    
    if symbol:
        try:
            # Fetch current stock data
            stock_data = fetch_stock_data(symbol)
            if 'error' in stock_data:
                error_message = stock_data['error']
            else:
                # Fetch historical data for the graph
                df = fetch_historical_data(symbol)
                if df is not None:
                    fig = px.line(df, x=df.index, y='close', 
                                title=f'{symbol} Price History (Last 30 Days)',
                                labels={'close': 'Price ($)', 'index': 'Date'})
                    
                    # Customize the graph appearance
                    fig.update_layout(
                        template='plotly_dark',
                        plot_bgcolor='rgba(0, 0, 0, 0)',
                        paper_bgcolor='rgba(0, 0, 0, 0)',
                        font=dict(color='white'),
                        xaxis=dict(
                            gridcolor='rgba(128, 128, 128, 0.2)',
                            title_font=dict(size=14),
                            tickfont=dict(size=12),
                            title='Date'
                        ),
                        yaxis=dict(
                            gridcolor='rgba(128, 128, 128, 0.2)',
                            title_font=dict(size=14),
                            tickfont=dict(size=12),
                            title='Price ($)'
                        ),
                        title=dict(
                            font=dict(size=16)
                        ),
                        margin=dict(t=50, l=50, r=20, b=50)
                    )
                    
                    graph_html = fig.to_html(full_html=False, config={'displayModeBar': True})
                else:
                    error_message = "Unable to fetch historical data for this symbol"
        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            error_message = f"An error occurred: {str(e)}"
    else:
        error_message = "No stock symbol provided"
    
    return render_template('lookup.html.jinja2', 
                         user=user,
                         graph_html=graph_html, 
                         error_message=error_message,
                         symbol=symbol,
                         stock_data=stock_data)


def fetch_historical_data(symbol):
    try:
        # Initialize the Finnhub client with a random API key
        finnhub_client = finnhub.Client(api_key=get_random_api_key())
        
        # Define the time range for the historical data
        end_date = int(datetime.now().timestamp())
        start_date = int((datetime.now() - timedelta(days=30)).timestamp())
        
        print(f"Fetching historical data for symbol: {symbol} from {start_date} to {end_date}")
        
        # Make the API call to fetch stock candles
        res = finnhub_client.stock_candles(symbol, 'D', start_date, end_date)
        
        # Print the raw response from the API
        print(f"Response from Finnhub for {symbol}: {res}")
        
        # Check if the response indicates success
        if res['s'] == 'ok':
            # Create a DataFrame from the response
            df = pd.DataFrame(res)
            df['t'] = pd.to_datetime(df['t'], unit='s')
            df.set_index('t', inplace=True)
            df = df.rename(columns={'c': 'close'})
            print(f"Successfully fetched historical data for {symbol}")
            return df
        else:
            print(f"Failed to fetch historical data for {symbol}: {res.get('s', 'unknown error')}")
            return None
    except Exception as e:
        print(f"An error occurred while fetching historical data for {symbol}: {str(e)}")
        return None



@celery.task(bind=True)
def update_stock_prices(self):
    try:
        portfolios = db.collection('portfolios').get()
        for portfolio in portfolios:
            symbol = portfolio.to_dict()['symbol']
            df = fetch_stock_data(symbol)
            if df is not None:
                latest_price = float(df.iloc[0]['c'])
                portfolio.reference.update({'latest_price': latest_price})
    except Exception as e:
        self.retry(exc=e)


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))



    
def fetch_historical_data(symbol):
    api_key = 'LL623C2ZURDROHZS'  # Replace with your Alpha Vantage API key
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={api_key}&outputsize=compact'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if 'Time Series (Daily)' in data:
            tsd = data['Time Series (Daily)']
            df = pd.DataFrame(tsd).T.rename(columns={
                '1. open': 'open',
                '2. high': 'high',
                '3. low': 'low',
                '4. close': 'close',
                '5. volume': 'volume'
            }).astype(float)
            df.index = pd.to_datetime(df.index)
            return df.loc[df.index > datetime.now() - timedelta(days=30)]
        else:
            print("No results found in API response.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None


if __name__ == '__main__':
    register_template_filters()
    app.run(debug=True)