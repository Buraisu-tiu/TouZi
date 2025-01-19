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
from datetime import datetime, timedelta
import finnhub
import plotly.express as px
import pandas as pd
from coinbase.wallet.client import Client
from google.cloud import firestore
import google.oauth2.service_account
import firebase_admin
from firebase_admin import credentials


cred = credentials.Certificate("stock-trading-simulator-b6e27-firebase-adminsdk-mcs36-88724709f0.json")
options = {
    'projectId': 'stock-trading-simulator-b6e27'
}
firebase_admin.initialize_app(cred, options=options)
db = firestore.Client()

app = Flask(__name__)
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
app.logger.addHandler(file_handler)

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
        {"name": "Precision Destitution", "description": "Have exactly $0"},
    ]
    
    badges_ref = db.collection('badges')
    for badge in badges:
        if not badges_ref.where('name', '==', badge['name']).stream():
            badges_ref.add(badge)


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
            'background_color': '#ffffff',
            'text_color': '#000000',
            'accent_color': '#007bff'
        })
        return redirect(url_for('login'))
    return render_template('register.html.jinja2')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.collection('users').where('username', '==', username).where('password', '==', password).limit(1).get()
        if user:
            session['user_id'] = user[0].id
            return redirect(url_for('dashboard'))
        else:
            return 'Invalid credentials'
    return render_template('login.html.jinja2')



@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    portfolio = db.collection('portfolios').where('user_id', '==', user_id).get()
    return render_template('dashboard.html.jinja2', user=user, portfolio=portfolio)


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    
    if request.method == 'POST':
        user_ref.update({
            'background_color': request.form.get('background_color', '#ffffff'),
            'text_color': request.form.get('text_color', '#000000'),
            'accent_color': request.form.get('accent_color', '#007bff')
        })
        return redirect(url_for('dashboard'))
    
    user = user_ref.get().to_dict()
    return render_template('settings.html.jinja2', user=user)

@app.route('/leaderboard')
def leaderboard():
    users = db.collection('users').stream()
    leaderboard_data = []

    for user in users:
        user_data = user.to_dict()
        portfolio_query = db.collection('portfolios').where('user_id', '==', user.id).stream()
        account_value = user_data['balance']

        for item in portfolio_query:
            item_data = item.to_dict()
            account_value += item_data['shares'] * item_data['purchase_price']

        leaderboard_data.append({
            'id': user.id,
            'username': user_data['username'],
            'account_value': round(account_value, 2)
        })

    leaderboard_data.sort(key=lambda x: x['account_value'], reverse=True)
    
    if leaderboard_data:
        award_badge(leaderboard_data[0]['id'], "1st Place")
        if len(leaderboard_data) >= 2:
            award_badge(leaderboard_data[1]['id'], "2nd Place")
        award_badge(leaderboard_data[-1]['id'], "Greatest Loser")
    
    return render_template('leaderboard.html.jinja2', leaderboard=leaderboard_data)


def award_badge(user_id, badge_name):
    badge_query = db.collection('badges').where('name', '==', badge_name).limit(1).get()
    if not badge_query:
        app.logger.debug(f"Badge {badge_name} not found.")
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
        app.logger.debug("User not logged in.")
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    user = user_ref.get().to_dict()

    if not user:
        app.logger.debug("User not found in Firestore.")
        return "User not found."

    if request.method == 'POST':
        symbol = request.form['symbol']
        try:
            shares = float(request.form['shares'])
        except ValueError:
            app.logger.debug("Invalid number of shares.")
            return "Invalid number of shares."

        if shares <= 0:
            app.logger.debug("Number of shares must be positive.")
            return "Number of shares must be positive."

        asset_type = request.form['asset_type']
        app.logger.debug(f"Attempting to buy {shares} of {symbol} ({asset_type})")

        if asset_type == 'stock':
            stock_data = fetch_stock_data(symbol)
            if stock_data is not None:
                latest_price = stock_data['close']
                cost = latest_price * shares

                if user['balance'] >= cost:
                    portfolio_query = db.collection('portfolios') \
                        .where('user_id', '==', user_id) \
                        .where('symbol', '==', symbol) \
                        .limit(1).get()

                    if portfolio_query:
                        portfolio = portfolio_query[0]
                        portfolio.reference.update({
                            'shares': portfolio.to_dict()['shares'] + shares
                        })
                    else:
                        db.collection('portfolios').add({
                            'user_id': user_id,
                            'symbol': symbol,
                            'shares': shares,
                            'purchase_price': latest_price,
                            'asset_type': 'stock'
                        })
                    # Award badges based on shares purchased
                    if shares >= 100:
                        award_badge(user_id, "All IN!!!")
                    if shares >= 50:
                        award_badge(user_id, "All in on black!")
                    if shares >= 25:
                        award_badge(user_id, "All in on red")

                    # Update user's balance
                    new_balance = round(user['balance'] - cost, 2)
                    user_ref.update({'balance': new_balance})

                    # Record the transaction
                    db.collection('transactions').add({
                        'user_id': user_id,
                        'symbol': symbol,
                        'shares': shares,
                        'price': latest_price,
                        'total_amount': cost,
                        'transaction_type': 'BUY',
                        'timestamp': datetime.utcnow()
                    })

                    app.logger.debug("Stock purchase successful.")
                    return redirect(url_for('dashboard'))
                else:
                    app.logger.debug("Insufficient balance to buy shares.")
                    return "Insufficient balance to buy shares."
            else:
                app.logger.debug("Failed to fetch stock data.")
                return "Failed to fetch stock data."
        elif asset_type == 'crypto':
            try:
                response = requests.get(f'https://api.coinbase.com/v2/prices/{symbol}-USD/spot')
                response.raise_for_status()
                data = response.json()
                price = float(data['data']['amount'])
                cost = price * shares

                app.logger.debug(f"Crypto price: {price}, cost: {cost}")

                if user['balance'] >= cost:
                    portfolio_query = db.collection('portfolios') \
                        .where('user_id', '==', user_id) \
                        .where('symbol', '==', symbol) \
                        .limit(1).get()

                    if portfolio_query:
                        portfolio = portfolio_query[0]
                        portfolio.reference.update({
                            'shares': portfolio.to_dict()['shares'] + shares
                        })
                    else:
                        db.collection('portfolios').add({
                            'user_id': user_id,
                            'symbol': symbol,
                            'shares': shares,
                            'purchase_price': price,
                            'asset_type': 'crypto'
                        })

                    # Update user's balance
                    new_balance = round(user['balance'] - cost, 2)
                    user_ref.update({'balance': new_balance})

                    # Record the transaction
                    db.collection('transactions').add({
                        'user_id': user_id,
                        'symbol': symbol,
                        'shares': shares,
                        'price': price,
                        'total_amount': cost,
                        'transaction_type': 'BUY',
                        'timestamp': datetime.utcnow()
                    })

                    app.logger.debug("Crypto purchase successful.")
                    return redirect(url_for('dashboard'))
                else:
                    app.logger.debug("Insufficient balance to buy cryptocurrency.")
                    return "Insufficient balance to buy cryptocurrency."
            except requests.exceptions.RequestException as e:
                app.logger.debug(f"Crypto API request failed: {e}")
                return f"Failed to fetch cryptocurrency data: {e}"
    return render_template('buy.html.jinja2', user=user)


@app.route('/sell', methods=['GET', 'POST'])
def sell():
    if request.method == 'POST':
        symbol = request.form['symbol']
        try:
            quantity = int(request.form['quantity'])
        except ValueError:
            return 'Invalid quantity. Please enter a positive integer.'
        if quantity <= 0:
            return 'Invalid quantity. Please enter a positive integer.'
        user_id = session['user_id']
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get().to_dict()
        portfolio_ref = db.collection('portfolios').where('user_id', '==', user_id).where('symbol', '==', symbol).get()
        if not portfolio_ref:
            return 'You don\'t own this stock.'
        portfolio = portfolio_ref[0]
        portfolio_data = portfolio.to_dict()
        if quantity > portfolio_data['shares']:
            return 'You don\'t have enough shares to sell.'
        df = fetch_stock_data(symbol)
        if df is None:
            return 'Failed to fetch stock data.'
        current_price = float(df.iloc[0]['open'])
        sale_amount = current_price * quantity
        profit_loss = (current_price - portfolio_data['purchase_price']) * quantity
        new_shares = portfolio_data['shares'] - quantity
        if new_shares == 0:
            portfolio.reference.delete()
        else:
            portfolio.reference.update({'shares': new_shares})
        new_balance = user['balance'] + sale_amount
        user_ref.update({'balance': new_balance})
        db.collection('transactions').add({
            'user_id': user_id,
            'symbol': symbol,
            'shares': quantity,
            'price': current_price,
            'total_amount': sale_amount,
            'transaction_type': 'SELL',
            'timestamp': datetime.utcnow(),
            'profit_loss': profit_loss
        })
        return redirect(url_for('dashboard'))

@app.route('/portfolio/<user_id>')
def view_portfolio(user_id):
    user = db.collection('users').document(user_id).get()
    if not user.exists:
        return "User  not found", 404
    portfolios = db.collection('portfolios').where('user_id', '==', user_id).get()
    if not portfolios:
        return render_template('portfolio.html.jinja2', user=user.to_dict(), portfolio=[], total_value=0)
    portfolio_data = []
    total_value = 0
    for entry in portfolios:
        entry_data = entry.to_dict()
        symbol = entry_data['symbol']
        shares = round(entry_data['shares'], 2)
        purchase_price = round(entry_data['purchase_price'], 2)
        asset_type = entry_data['asset_type']
        if asset_type == 'stock':
            df = fetch_stock_data(symbol)
            if df is None:
                return "Failed to fetch stock data. Please try again later."
            current_price = float(df.iloc[0]['open'])
        elif asset_type == 'crypto':
            try:
                response = requests.get(f'https://api.coinbase.com/v2/prices/{symbol}-USD/spot')
                response.raise_for_status()
                data = response.json()
                current_price = round(float(data['data']['amount']), 2)
            except requests.exceptions.RequestException:
                current_price = purchase_price
        asset_value = round(shares * current_price, 2)
        portfolio_data.append({
            'symbol': symbol,
            'asset_type': asset_type,
            'shares': shares,
            'purchase_price': purchase_price,
            'latest_price': current_price,
            'value': asset_value
        })
        total_value += asset_value
    return render_template('portfolio.html.jinja2', user=user.to_dict(), portfolio=portfolio_data, total_value=round(total_value, 2))



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


def fetch_historical_data(symbol):
    finnhub_client = finnhub.Client(api_key=get_random_api_key())
    end_date = int(datetime.now().timestamp())
    start_date = int((datetime.now() - timedelta(days=30)).timestamp())
    
    res = finnhub_client.stock_candles(symbol, 'D', start_date, end_date)
    if res['s'] == 'ok':
        df = pd.DataFrame(res)
        df['t'] = pd.to_datetime(df['t'], unit='s')
        df.set_index('t', inplace=True)
        df = df.rename(columns={'c': 'close'})
        return df
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
        res = finnhub_client.quote(symbol)
        app.logger.debug(f"Finnhub response for {symbol}: {res}")

        # Ensure the response contains valid data
        if not res:
            app.logger.error(f"Empty response for symbol {symbol}")
            return None

        # Ensure all necessary keys are in the response (excluding 'c')
        required_keys = ['o', 'h', 'l', 'pc']  # Removed 'c' for closing price
        missing_keys = [key for key in required_keys if key not in res]

        if missing_keys:
            app.logger.error(f"Missing keys {missing_keys} in response for symbol {symbol}: {res}")
            return None

        # Return data without the 'current_price' (i.e., 'c' key)
        return {
            'symbol': symbol,
            'open': res.get('o', 0),          # Open price
            'high': res.get('h', 0),          # High price
            'low': res.get('l', 0),           # Low price
            'prev_close': res.get('pc', 0)    # Previous close price
        }
    
    except finnhub.exceptions.FinnhubAPIException as e:
        app.logger.error(f"Finnhub API error for symbol {symbol}: {e}")
        return None
    except Exception as e:
        app.logger.error(f"Error fetching stock data for symbol {symbol}: {e}")
        return None
    
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