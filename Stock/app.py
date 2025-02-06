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


# Enable Google Cloud logging
client = Client()
client.setup_logging()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
HTMLMIN(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
celery = Celery(app.name, broker='redis://localhost:6379/0')
celery.conf.update(app.config)

# Setup detailed logging
file_handler = FileHandler('errorlog.txt')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
print(file_handler)

# Add this to your app initialization or before first request
@app.before_request
def register_template_filters():
    app.jinja_env.filters['hex_to_rgb'] = hex_to_rgb
    app.jinja_env.filters['lighten_color'] = lighten_color
    
    
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
        {"name": "1st Place", "description": "Reached 1st place on the leaderboard"},
        {"name": "2nd Place", "description": "Reached 2nd place on the leaderboard"},
        {"name": "Greatest Loser", "description": "Reached last place on the leaderboard"},
        {"name": "Exactly $1000", "description": "Had exactly $1000 in account balance"},
        {"name": "All in on red", "description": "Buy at least 10 of any stock"},
        {"name": "All in on black!", "description": "Buy at least 25 of any stock"},
        {"name": "All IN!!!", "description": "Buy at least 100 of any stock"},
        {"name": "How", "description": "Buy at least 10000 of any stock"},
        {"name": "Precision Destitution", "description": "Have exactly $0"},
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

@app.route('/leaderboard')
def leaderboard():
    print("Retrieving user data...")
    users = db.collection('users').stream()
    print("Retrieved user data:", users)

    leaderboard_data = []
    all_users = list(users)  # Convert to list so we can reuse it
    
    # First pass: Calculate account values and build leaderboard
    for user in all_users:
        user_data = user.to_dict()
        print(f"Retrieving portfolio data for user: {user_data['username']}")
        portfolio_query = db.collection('portfolios').where('user_id', '==', user.id).stream()
        print("Retrieved portfolio data:", portfolio_query)

        account_value = user_data['balance']
        for item in portfolio_query:
            item_data = item.to_dict()
            # Get the current price of the shares
            if item_data['asset_type'] == 'stock':
                stock_data = fetch_stock_data(item_data['symbol'])
                if 'error' in stock_data:
                    print(f"Error fetching stock data for {item_data['symbol']}: {stock_data['error']}")
                    continue
                current_price = stock_data['close']
            elif item_data['asset_type'] == 'crypto':
                crypto_data = fetch_crypto_data(item_data['symbol'])
                if 'error' in crypto_data:
                    print(f"Error fetching crypto data for {item_data['symbol']}: {crypto_data['error']}")
                    continue
                current_price = crypto_data['price']
            # Calculate the current value of the shares
            share_value = item_data['shares'] * current_price
            # Add the share value to the account value
            account_value += share_value

        profile_picture = user_data.get('profile_picture', '')

        leaderboard_data.append({
            'id': user.id,
            'username': user_data['username'],
            'account_value': round(account_value, 2),
            'accent_color': user_data['accent_color'],
            'background_color': user_data['background_color'],
            'text_color': user_data['text_color'],
            'profile_picture': profile_picture
        })

    print("Sorting leaderboard data...")
    leaderboard_data.sort(key=lambda x: x['account_value'], reverse=True)
    print("Sorted leaderboard data:", leaderboard_data)

    # Update the leaderboard document
    leaderboard_ref = db.collection('leaderboard')
    leaderboard_ref.document('leaderboard').set({'leaderboard': leaderboard_data})

    # Second pass: Check badges for all users now that we have the sorted leaderboard
    print("Checking badges for all users...")
    for user in all_users:
        try:
            user_id = user.id
            print(f"Checking badges for user: {user_id}")
            check_and_award_badges(user_id)
        except Exception as e:
            print(f"Error checking badges for user {user_id}: {str(e)}")
            continue

    # Get the current user's data for template rendering
    user_data = None
    if 'user_id' in session:
        user_id = session['user_id']
        user_ref = db.collection('users').document(user_id)
        user_data = user_ref.get().to_dict()

    return render_template('leaderboard.html.jinja2', leaderboard=leaderboard_data, user=user_data)





def fetch_crypto_data(symbol):
    url = f'https://api.coinbase.com/v2/prices/{symbol}-USD/spot'
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return {'price': float(data['data']['amount'])}




def check_and_award_badges(user_id):
    """Check and award badges based on user's actions and achievements"""
    try:
        # Get user data
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get().to_dict()
        if not user:
            print(f"User  {user_id} not found")
            return

        # Get user's portfolio
        portfolio_refs = db.collection('portfolios').where('user_id', '==', user_id).stream()
        portfolio_items = [item.to_dict() for item in portfolio_refs]

        # Get leaderboard data
        leaderboard_ref = db.collection('leaderboard').document('leaderboard').get()
        if leaderboard_ref.exists:
            leaderboard_data = leaderboard_ref.to_dict().get('leaderboard', [])
            # Find user's position
            user_position = next((i + 1 for i, entry in enumerate(leaderboard_data) 
                                if entry['id'] == user_id), None)
        else:
            user_position = None
            leaderboard_data = []

        # Get existing badges for the user
        existing_badges_query = db.collection('user_badges').where('user_id', '==', user_id).stream()
        existing_badges = {badge.to_dict()['badge_id'] for badge in existing_badges_query}

        # Check balance-based badges
        print(f"Checking balance badges for user {user_id}")
        print(f"Current balance: {user['balance']}")
        
        # Exact $1000 badge
        if abs(float(user['balance']) - 1000.00) < 0.01 and "Exactly $1000" not in existing_badges:
            print("Awarding Exactly $1000 badge")
            award_badge(user_id, "Exactly $1000")
        
        # Precision Destitution badge
        if abs(float(user['balance'])) < 0.01 and "Precision Destitution" not in existing_badges:
            print("Awarding Precision Destitution badge")
            award_badge(user_id, "Precision Destitution")

        # Check leaderboard position badges
        if user_position is not None:
            print(f"User  position on leaderboard: {user_position}")
            if user_position == 1 and "1st Place" not in existing_badges:
                print("Awarding 1st Place badge")
                award_badge(user_id, "1st Place")
            elif user_position == 2 and "2nd Place" not in existing_badges:
                print("Awarding 2nd Place badge")
                award_badge(user_id, "2nd Place")
            elif user_position == len(leaderboard_data) and "Greatest Loser" not in existing_badges:
                print("Awarding Greatest Loser badge")
                award_badge(user_id, "Greatest Loser")

        # Check stock quantity badges
        for portfolio in portfolio_items:
            shares = float(portfolio.get('shares', 0))
            print(f"Checking shares quantity badges. Current shares: {shares}")
            
            # Check for the "How" badge first
            if shares >= 10000 and "How" not in existing_badges:
                print("Awarding How badge")
                award_badge(user_id, "How")
            
            # Then check for the "All IN!!!" badge
            if shares >= 100 and "All IN!!!" not in existing_badges:
                print("Awarding All IN!!! badge")
                award_badge(user_id, "All IN!!!")
            
            # Continue with the other badges
            if shares >= 25 and "All in on black!" not in existing_badges:
                print("Awarding All in on black! badge")
                award_badge(user_id, "All in on black!")
            
            if shares >= 10 and "All in on red" not in existing_badges:
                print("Awarding All in on red badge")
                award_badge(user_id, "All in on red")

    except Exception as e:
        print(f"Error in check_and_award_badges: {str(e)}")
        return False
def award_badge(user_id, badge_name):
    """Award a badge to a user if they don't already have it"""
    try:
        print(f"Attempting to award {badge_name} badge to user {user_id}")
        
        # Get the badge document
        badge_query = db.collection('badges').where('name', '==', badge_name).limit(1).get()
        if not badge_query:
            print(f"Badge {badge_name} not found in Firestore")
        else:
            print(f"Badge {badge_name} found: {badge_query[0].to_dict()}")

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
            
            print(f"Successfully awarded {badge_name} badge to user {user_id}")
            return True
        else:
            print(f"User  {user_id} already has the {badge_name} badge")
            return False
            
    except Exception as e:
        print(f"Error awarding badge: {str(e)}")
        return False


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

@app.route('/buy', methods=['GET', 'POST'])
def buy():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    user = user_ref.get().to_dict()

    if request.method == 'POST':
        # Get form inputs
        symbol = request.form.get('symbol', '').upper().strip()
        shares = request.form.get('shares')
        asset_type = request.form.get('asset_type')

        # Validate inputs
        try:
            # Convert shares to float and validate
            shares = float(shares)
            if shares <= 0:
                flash('Quantity must be a positive number', 'error')
                return redirect(url_for('buy'))

            # Validate symbol 
            if not symbol or len(symbol) > 10:
                flash('Invalid symbol', 'error')
                return redirect(url_for('buy'))

            # Fetch current price based on asset type
            try:
                if asset_type == 'stock':
                    stock_data = fetch_stock_data(symbol)
                    if 'error' in stock_data:
                        flash(f"Error fetching stock data: {stock_data['error']}", 'error')
                        return redirect(url_for('buy'))
                    price = stock_data['close']
                elif asset_type == 'crypto':
                    crypto_data = fetch_crypto_data(symbol)
                    if 'error' in crypto_data:
                        flash(f"Error fetching crypto data: {crypto_data['error']}", 'error')
                        return redirect(url_for('buy'))
                    price = crypto_data['price']
                else:
                    flash('Invalid asset type', 'error')
                    return redirect(url_for('buy'))

            except Exception as price_error:
                flash(f'Error fetching price: {str(price_error)}', 'error')
                return redirect(url_for('buy'))

            # Calculate total cost
            total_cost = round(price * shares, 2)

            # Check if user has enough funds
            if total_cost > user['balance']:
                flash(f'Insufficient funds. You need ${total_cost:.2f}, but have ${user["balance"]:.2f}', 'error')
                return redirect(url_for('buy'))

            # Perform the purchase
            try:
                # Check if portfolio entry exists
                portfolio_query = db.collection('portfolios').where('user_id', '==', user_id).where('symbol', '==', symbol).limit(1).get()
                
                if portfolio_query:
                    # Update existing portfolio entry
                    portfolio_doc = portfolio_query[0]
                    portfolio_ref = portfolio_doc.reference
                    portfolio_data = portfolio_doc.to_dict()
                    
                    new_shares = portfolio_data['shares'] + shares
                    new_total_cost = portfolio_data.get('total_cost', 0) + total_cost
                    
                    portfolio_ref.update({
                        'shares': new_shares,
                        'total_cost': new_total_cost,
                        'purchase_price': price
                    })
                else:
                    # Create new portfolio entry
                    db.collection('portfolios').add({
                        'user_id': user_id,
                        'symbol': symbol,
                        'shares': shares,
                        'asset_type': asset_type,
                        'total_cost': total_cost,
                        'purchase_price': price
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

                # Flash success message
                check_and_award_badges(user_id)
                flash(f'Successfully purchased {shares} {symbol} for ${total_cost:.2f}', 'success')
                return redirect(url_for('buy', success=True))

            except Exception as purchase_error:
                flash(f'Purchase failed: {str(purchase_error)}', 'error')
                return redirect(url_for('buy'))

        except ValueError:
            flash('Invalid quantity. Please enter a valid number.', 'error')
            return redirect(url_for('buy'))

    # GET request - render buy page
    success = request.args.get('success')
    return render_template('buy.html.jinja2', user=user, success=success)



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




@app.route('/portfolio/<string:user_id>')
def view_portfolio(user_id):
    user = db.collection('users').document(user_id).get()
    if not user.exists:
        return "User not found", 404

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

    return render_template('portfolio.html.jinja2', user=user.to_dict(), profile_picture=profile_picture, portfolio=portfolio_data, total_value=round(total_value, 2), badges=badge_data)

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
    app.run(debug=True)