import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
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
import pandas as pd
from werkzeug.utils import secure_filename
import google.auth
import google.cloud.logging
from google.cloud.logging import Client
import asyncio
import aiohttp

# Initialize timezone and current time
tz = timezone.utc
now = datetime.now(tz)

# Load Google credentials
credentials, project_id = google.auth.load_credentials_from_file(
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'],
    scopes=['https://www.googleapis.com/auth/firestore']
)

project_id = "stock-trading-simulator-b6e27"
client = google.cloud.logging.Client(credentials=credentials, project=project_id)

# Setup logging
logging.basicConfig(level=logging.INFO)
db = firestore.Client(project=project_id)
client.setup_logging()

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key')
HTMLMIN(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
celery = Celery(app.name, broker='redis://localhost:6379/0')
celery.conf.update(app.config)

# Configure logging
file_handler = FileHandler('errorlog.txt')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
app.logger.addHandler(file_handler)

# Constants
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
API_KEYS = [
    'ctitlv1r01qgfbsvh1dgctitlv1r01qgfbsvh1e0',
    'ctitnthr01qgfbsvh59gctitnthr01qgfbsvh5a0',
    'ctjgjm1r01quipmu2qi0ctjgjm1r01quipmu2qig'
]

# Utility functions
def get_random_api_key():
    return random.choice(API_KEYS)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_badges():
    badges = [
        {"name": "1st Place", "description": "Reached 1st place on the leaderboard"},
        {"name": "2nd Place", "description": "Reached 2nd place on the leaderboard"},
        {"name": "Greatest Loser", "description": "Reached last place on the leaderboard"},
        {"name": "Exactly $1000", "description": "Had exactly $1000 in account balance"},
        {"name": "All in on red", "description": "Buy at least 10 of any stock"},
        {"name": "All in on black!", "description": "Buy at least 25 of any stock"},
        {"name": "All IN!!!", "description": "Buy at least 100 of any stock"},
        {"name": "Precision Destitution", "description": "Have exactly $0"}
    ]
    
    badges_ref = db.collection('badges')
    for badge in badges:
        if not badges_ref.where('name', '==', badge['name']).stream():
            badges_ref.add(badge)

def award_badge(user_id, badge_name):
    badge_ref = db.collection('badges').where('name', '==', badge_name).limit(1).get()
    if not badge_ref:
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

# API functions
async def fetch_stock_data_async(symbol):
    try:
        finnhub_client = finnhub.Client(api_key=get_random_api_key())
        quote = finnhub_client.quote(symbol)
        if quote:
            return {
                'symbol': symbol,
                'open': quote.get('o', 0),
                'high': quote.get('h', 0),
                'low': quote.get('l', 0),
                'prev_close': quote.get('pc', 0),
                'close': quote.get('c', 0)
            }
        return {'error': 'Empty response from Finnhub API'}
    except Exception as e:
        return {'error': f'Error fetching stock data: {str(e)}'}

async def fetch_crypto_data_async(symbol):
    try:
        async with aiohttp.ClientSession() as session:
            url = f'https://api.coinbase.com/v2/prices/{symbol}-USD/spot'
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                return {'price': float(data['data']['amount'])}
    except Exception as e:
        return {'error': f'Error fetching crypto data: {str(e)}'}

async def fetch_stock_data_bulk_async(symbols):
    tasks = [fetch_stock_data_async(symbol) for symbol in symbols]
    results = await asyncio.gather(*tasks)
    return {symbol: result for symbol, result in zip(symbols, results)}

async def fetch_crypto_data_bulk_async(symbols):
    tasks = [fetch_crypto_data_async(symbol) for symbol in symbols]
    results = await asyncio.gather(*tasks)
    return {symbol: result for symbol, result in zip(symbols, results)}

def fetch_stock_data(symbol):
    try:
        finnhub_client = finnhub.Client(api_key=get_random_api_key())
        data = finnhub_client.quote(symbol)
        
        if not data:
            return {'error': 'Empty response from Finnhub API'}
        
        required_keys = ['o', 'h', 'l', 'pc', 'c']
        missing_keys = [key for key in required_keys if key not in data]
        
        if missing_keys:
            return {'error': f'Missing keys {", ".join(missing_keys)} in response from Finnhub API'}
        
        return {
            'symbol': symbol,
            'open': data.get('o', 0),
            'high': data.get('h', 0),
            'low': data.get('l', 0),
            'prev_close': data.get('pc', 0),
            'close': data.get('c', 0)
        }
    except Exception as e:
        return {'error': f'Error fetching stock data: {str(e)}'}

# Routes
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
            'balance': 999.99,
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
        
        try:
            users_ref = db.collection('users').where('username', '==', username).get()
            
            if not users_ref:
                flash('Invalid credentials', 'error')
                return redirect(url_for('login'))

            for user in users_ref:
                user_data = user.to_dict()
                if user_data.get('password') == password:
                    session['user_id'] = user.id
                    return redirect(url_for('dashboard'))
            
            flash('Invalid credentials', 'error')
            return redirect(url_for('login'))
            
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            flash('An error occurred during login', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html.jinja2')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    
    # Get recent transactions
    transactions_ref = db.collection('transactions')\
        .where('user_id', '==', user_id)\
        .where('transaction_type', '==', 'SELL')\
        .where('profit_loss', '!=', 0)\
        .order_by('timestamp', direction=firestore.Query.DESCENDING)\
        .limit(5)
    
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
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                user_ref.update({
                    'profile_picture': url_for('static', filename=f'uploads/{filename}')
                })

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
async def leaderboard():
    users = db.collection('users').stream()
    portfolios = db.collection('portfolios').stream()
    
    portfolios_by_user = {}
    for portfolio in portfolios:
        portfolio_data = portfolio.to_dict()
        user_id = portfolio_data['user_id']
        if user_id not in portfolios_by_user:
            portfolios_by_user[user_id] = []
        portfolios_by_user[user_id].append(portfolio_data)

    # Separate symbols based on asset type
    stock_symbols = []
    crypto_symbols = []
    
    for user_portfolios in portfolios_by_user.values():
        for portfolio in user_portfolios:
            symbol = portfolio['symbol']
            if portfolio['asset_type'] == 'stock':
                stock_symbols.append(symbol)
            elif portfolio['asset_type'] == 'crypto':
                crypto_symbols.append(symbol)

    # Remove duplicates
    stock_symbols = list(set(stock_symbols))
    crypto_symbols = list(set(crypto_symbols))

    # Fetch prices
    stock_prices = await fetch_stock_data_bulk_async(stock_symbols)
    crypto_prices = await fetch_crypto_data_bulk_async(crypto_symbols)

    leaderboard_data = []
    for user in users:
        user_data = user.to_dict()
        user_id = user.id
        account_value = user_data['balance']

        if user_id in portfolios_by_user:
            for portfolio in portfolios_by_user[user_id]:
                symbol = portfolio['symbol']
                asset_type = portfolio['asset_type']
                current_price = 0
                
                if asset_type == 'stock':
                    current_price = stock_prices.get(symbol, {}).get('close', 0)
                elif asset_type == 'crypto':
                    current_price = crypto_prices.get(symbol, {}).get('price', 0)
                
                share_value = portfolio['shares'] * current_price
                account_value += share_value

        leaderboard_data.append({
            'id': user_id,
            'username': user_data['username'],
            'account_value': round(account_value, 2),
            'accent_color': user_data['accent_color'],
            'background_color': user_data['background_color'],
            'text_color': user_data['text_color'],
            'profile_picture': user_data.get('profile_picture', '')
        })

    leaderboard_data.sort(key=lambda x: x['account_value'], reverse=True)
    
    # Update leaderboard in database
    db.collection('leaderboard').document('leaderboard').set({
        'leaderboard': leaderboard_data
    })

    # Get current user's data
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





def award_badge(user_id, badge_name):
    badge_query = db.collection('badges').where('name', '==', badge_name).limit(1).get()
    if not badge_query:
        print(f"Badge {badge_name} not found.")
        return
    badge_id = badge_query[0].id

    user_ref = db.collection('users').document(user_id)
    badge_ref = db.collection('badges').where('name', '==', badge_name).get()[0]
    user_badges_ref = db.collection('user_badges')
    if not user_badges_ref.where('user_id', '==', user_id).where('badge_id', '==', badge_ref.id).get():
        user_badges_ref.add({
            'user_id': user_id,
            'badge_id': badge_ref.id,
            'date_earned': datetime.utcnow()
        })

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
                        'purchase_price': price  # Ensure this is the correct price based on asset type
                    })
                else:
                    # Create new portfolio entry
                    db.collection('portfolios').add({
                        'user_id': user_id,
                        'symbol': symbol,
                        'shares': shares,
                        'asset_type': asset_type,
                        'total_cost': total_cost,
                        'purchase_price': price  # Ensure this is the correct price based on asset type
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
    


if __name__ == '__main__':
    app.run(debug=True)