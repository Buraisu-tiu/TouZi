import pandas as pd
import requests
import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
import random
import plotly.express as px
import finnhub
from coinbase.wallet.client import Client
import logging
from logging import FileHandler, Formatter
from flask_caching import Cache
from sqlalchemy.orm import joinedload
from celery import Celery
from flask_htmlmin import HTMLMIN

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
    # Add more keys as needed
]

# Add this at the top where you define API keys and other configurations
coinbase_api_key = 'your_coinbase_api_key'
coinbase_api_secret = 'your_coinbase_api_secret'
coinbase_client = Client(coinbase_api_key, coinbase_api_secret)



cache = Cache(app, config={'CACHE_TYPE': 'simple'})



# Fetch the PostgreSQL database URI from the environment variable
database_uri = os.environ.get("DATABASE_URL")
if not database_uri:
    raise ValueError("No DATABASE_URL set for Flask application")

print(f"DATABASE_URL: {database_uri}")  # Print the database URI to verify
app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 300,
    'pool_recycle': 3600,
    'connect_args': {'connect_timeout': 30}
}
app.secret_key = 'your_secret_key'
db = SQLAlchemy(app)
migrate = Migrate(app, db)



class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    balance = db.Column(db.Float, nullable=False, default=999.99)
    background_color = db.Column(db.String(7), default='#ffffff')
    text_color = db.Column(db.String(7), default='#000000')
    accent_color = db.Column(db.String(7), default='#007bff')
    badges = db.relationship('Badge', secondary='user_badges', backref='users')

    
    def total_account_value(self):
        total_value = self.balance
        for portfolio in self.portfolios:
            df = fetch_stock_data(portfolio.symbol)
            if df is not None:
                latest_price = df.iloc[0]['c']
                total_value += portfolio.shares * latest_price
        return round(total_value, 2)

class Badge(db.Model):
    __tablename__ = 'badges'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200), nullable=False)

class UserBadge(db.Model):
    __tablename__ = 'user_badges'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badges.id'), nullable=False)
    date_earned = db.Column(db.DateTime, default=datetime.utcnow)


class Portfolio(db.Model):
    __tablename__ = 'portfolios'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    shares = db.Column(db.Float, nullable=False)
    purchase_price = db.Column(db.Float, nullable=False)
    asset_type = db.Column(db.String(10), nullable=False)  # Add this line
    user = db.relationship('User', backref=db.backref('portfolios', lazy=True))


class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    shares = db.Column(db.Float, nullable=False)
    price = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(4), nullable=False)  # VARCHAR(4) to accommodate 'BUY' and 'SS'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    profit_loss = db.Column(db.Float, nullable=True)

def create_badges():
    badges = [
        {"name": "1st Place", "description": "Reached 1st place on the leaderboard"},
        {"name": "2nd Place", "description": "Reached 2nd place on the leaderboard"},
        {"name": "Greatest Loser", "description": "Reached last place on the leaderboard"},
        {"name": "Exactly $1000", "description": "Had exactly $1000 in account balance"},
        {"name": "All in on red", "description": "Buy at least 10 of any stock"},
        {"name": "All in on black!", "description": "Buy at least 25 of any stock"},
        {"name": "All IN!!!", "description": "Buy at least 100 of any stock"},
    ]
    
    with app.app_context():
        for badge_data in badges:
            if not Badge.query.filter_by(name=badge_data['name']).first():
                new_badge = Badge(**badge_data)
                db.session.add(new_badge)
        db.session.commit()
    
    db.session.commit()
    
def init_db():
    with app.app_context():
        db.create_all()
        
@app.route('/')
def home():
    create_badges() 
    return redirect(url_for('login'))

def get_random_api_key():
    return random.choice(api_keys)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            return 'Invalid credentials'
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    portfolio = Portfolio.query.filter_by(user_id=user_id).all()
    
    # Check for exactly $1000 balance
    if user.balance == 1000.0:
        award_badge(user, "Exactly $1000")
    
    return render_template('dashboard.html', user=user, portfolio=portfolio)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    user = db.session.get(User, user_id)

    if request.method == 'POST':
        # Update user's color preferences
        user.background_color = request.form.get('background_color', '#ffffff')
        user.text_color = request.form.get('text_color', '#000000')
        user.accent_color = request.form.get('accent_color', '#007bff')
        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('settings.html', user=user)

@app.route('/leaderboard')
def leaderboard():
    users = User.query.all()
    leaderboard_data = []
    for user in users:
        account_value = user.total_account_value()
        leaderboard_data.append({
            'id': user.id,
            'username': user.username,
            'account_value': account_value
        })
    leaderboard_data.sort(key=lambda x: x['account_value'], reverse=True)
    
    # Award badges for 1st and 2nd place
    if len(leaderboard_data) >= 1:
        first_place_user = db.session.get(User, leaderboard_data[0]['id'])
        print(f"Awarding 1st place badge to {first_place_user.username}")
        award_badge(first_place_user, "1st Place")
    if len(leaderboard_data) >= 2:
        second_place_user = User.query.get(leaderboard_data[1]['id'])
        print(f"Awarding 2nd place badge to {second_place_user.username}")
        award_badge(second_place_user, "2nd Place")
    
    # Award badge for last place
    if len(leaderboard_data) > 0:
        last_place_user = User.query.get(leaderboard_data[-1]['id'])
        print(f"Awarding last place badge to {last_place_user.username}")
        award_badge(last_place_user, "Greatest Loser")
    
    return render_template('leaderboard.html', leaderboard=leaderboard_data)





@app.route('/history')
def transaction_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    page = request.args.get('page', 1, type=int)
    per_page = 20
    transactions = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.timestamp.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    # ... rest of the function ...

    
    history = []
    for t in transactions:
        profit_loss = t.profit_loss if t.profit_loss is not None else 0.0
        history.append({
            'date': t.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'type': t.transaction_type,
            'symbol': t.symbol,
            'shares': t.shares,
            'price': t.price,
            'total': t.total_amount,
            'profit_loss': round(profit_loss, 2)
        })
    
    return render_template('history.html', history=history, user=user)

@app.route('/portfolio/<int:user_id>')
def view_portfolio(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return "User not found", 404
    
    print(f"Checking badges for user {user.username}")
    print(f"User balance: ${user.balance}")
    
    if user.balance == 1000.0:
        print("User has exactly $1000, awarding badge")
        award_badge(user, "Exactly $1000")
    else:
        print("User does not have exactly $1000")

    # Check account value for other potential badges
    account_value = user.total_account_value()
    if account_value >= 10000:
        award_badge(user, "10K Club")
    portfolios = Portfolio.query.filter_by(user_id=user_id).all()
    portfolio_data = []
    total_value = 0
    for entry in portfolios:
        symbol = entry.symbol
        shares = round(entry.shares, 2)
        purchase_price = round(entry.purchase_price, 2)
        asset_type = entry.asset_type
        if asset_type == 'stock':
            df = fetch_stock_data(symbol)
            if df is not None:
                latest_price = round(float(df.iloc[0]['c']), 2)
        elif asset_type == 'crypto':
            try:
                response = requests.get(f'https://api.coinbase.com/v2/prices/{symbol}-USD/spot')
                response.raise_for_status()
                data = response.json()
                latest_price = round(float(data['data']['amount']), 2)
            except requests.exceptions.RequestException:
                latest_price = purchase_price
        asset_value = round(shares * latest_price, 2)
        portfolio_data.append({
            'symbol': symbol,
            'asset_type': asset_type,
            'shares': shares,
            'purchase_price': purchase_price,
            'latest_price': latest_price,
            'value': asset_value
        })
        total_value += asset_value
    return render_template('portfolio.html', user=user, portfolio=portfolio_data, total_value=round(total_value, 2))


@app.route('/buy', methods=['GET', 'POST'])
def buy():
    if 'user_id' not in session:
        app.logger.debug("User not logged in.")
        return redirect(url_for('login'))
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    if request.method == 'POST':
        symbol = request.form['symbol']
        shares = float(request.form['shares'])
        asset_type = request.form['asset_type']

        if shares <= 0:
            app.logger.debug("Number of shares must be positive.")
            return "Number of shares must be positive."

        app.logger.debug(f"Attempting to buy {shares} of {symbol} ({asset_type})")

        if asset_type == 'stock':
            df = fetch_stock_data(symbol)
            if df is not None:
                latest_price = float(df.iloc[0]['c'])
                cost = latest_price * shares

                if user.balance >= cost:
                    portfolio = Portfolio.query.filter_by(user_id=user_id, symbol=symbol).first()
                    if portfolio:
                        portfolio.shares += shares
                    else:
                        portfolio = Portfolio(user_id=user_id, symbol=symbol, shares=shares, purchase_price=latest_price, asset_type='stock')
                        db.session.add(portfolio)
                        if shares >= 100:
                            award_badge(user, "All IN!!!")
                        elif shares >= 25:
                            award_badge(user, "All in on black!")
                        elif shares >= 10:
                            award_badge(user, "All in on red")
                    user.balance -= cost
                    transaction = Transaction(user_id=user_id, symbol=symbol, shares=shares, price=latest_price, total_amount=cost, transaction_type='BUY')
                    db.session.add(transaction)
                    db.session.commit()
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

                if user.balance >= cost:
                    portfolio = Portfolio.query.filter_by(user_id=user_id, symbol=symbol).first()
                    if portfolio:
                        portfolio.shares += shares
                    else:
                        portfolio = Portfolio(user_id=user_id, symbol=symbol, shares=shares, purchase_price=price, asset_type='crypto')
                        db.session.add(portfolio)
                    user.balance -= cost
                    transaction = Transaction(user_id=user_id, symbol=symbol, shares=shares, price=price, total_amount=cost, transaction_type='BUY')
                    db.session.add(transaction)
                    db.session.commit()
                    app.logger.debug("Crypto purchase successful.")
                    return redirect(url_for('dashboard'))
                else:
                    app.logger.debug("Insufficient balance to buy cryptocurrency.")
                    return "Insufficient balance to buy cryptocurrency."
            except requests.exceptions.RequestException as e:
                app.logger.debug(f"Crypto API request failed: {e}")
                return f"Failed to fetch cryptocurrency data: {e}"
    return render_template('buy.html', user=user)



@app.route('/sell', methods=['GET', 'POST'])
def sell():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    user = db.session.get(User, user_id)
    if request.method == 'POST':
        symbol = request.form['symbol']
        shares_to_sell = float(request.form['shares'])
        asset_type = request.form['asset_type']

        if shares_to_sell <= 0:
            return "Number of shares must be positive."

        if asset_type == 'stock':
            df = fetch_stock_data(symbol)
            if df is not None:
                latest_price = float(df.iloc[0]['c'])
                portfolio = Portfolio.query.filter_by(user_id=user_id, symbol=symbol).first()
                if portfolio and portfolio.shares >= shares_to_sell:
                    proceeds = latest_price * shares_to_sell
                    portfolio.shares -= shares_to_sell
                    if portfolio.shares == 0:
                        db.session.delete(portfolio)
                    user.balance += proceeds
                    profit_loss = (latest_price - portfolio.purchase_price) * shares_to_sell
                    transaction = Transaction(user_id=user_id, symbol=symbol, shares=shares_to_sell, price=latest_price, total_amount=proceeds, transaction_type='SELL', profit_loss=round(profit_loss, 2))
                    db.session.add(transaction)
                    db.session.commit()
                    return redirect(url_for('dashboard'))
                else:
                    return "Insufficient shares to sell."
            else:
                return "Failed to fetch stock data."
        elif asset_type == 'crypto':
            try:
                price = coinbase_client.get_spot_price(currency_pair=f'{symbol}-USD')['amount']
                portfolio = Portfolio.query.filter_by(user_id=user_id, symbol=symbol).first()
                if portfolio and portfolio.shares >= shares_to_sell:
                    proceeds = float(price) * shares_to_sell
                    portfolio.shares -= shares_to_sell
                    if portfolio.shares == 0:
                        db.session.delete(portfolio)
                    user.balance += proceeds
                    profit_loss = (float(price) - portfolio.purchase_price) * shares_to_sell
                    transaction = Transaction(user_id=user_id, symbol=symbol, shares=shares_to_sell, price=float(price), total_amount=proceeds, transaction_type='SELL', profit_loss=round(profit_loss, 2))
                    db.session.add(transaction)
                    db.session.commit()
                    return redirect(url_for('dashboard'))
                else:
                    return "Insufficient cryptocurrency to sell."
            except Exception as e:
                return f"Failed to fetch cryptocurrency data: {e}"
    return render_template('sell.html', user=user)


@app.route('/delete_account', methods=['GET', 'POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = db.session.get(User, user_id)  # Use Session.get() method

    if request.method == 'POST':
        # Delete user's portfolios
        Portfolio.query.filter_by(user_id=user_id).delete()
        
        # Delete user's transactions
        Transaction.query.filter_by(user_id=user_id).delete()

        # Delete user account
        db.session.delete(user)
        db.session.commit()
        
        session.pop('user_id', None)
        return redirect(url_for('home'))

    return render_template('confirm_delete.html', user=user)

def award_badge(user, badge_name):
    badge = Badge.query.filter_by(name=badge_name).first()
    if not badge:
        print(f"Badge '{badge_name}' does not exist.")
        return
    
    if badge in user.badges:
        print(f"User {user.username} already has badge '{badge_name}'.")
        return
    
    user.badges.append(badge)
    db.session.commit()
    print(f"Badge '{badge_name}' awarded to user {user.username}.")



        
@app.route('/plot/<symbol>', methods=['GET'])
def plot(symbol):
    df = fetch_historical_data(symbol)
    if df is not None:
        fig = px.line(df, x=df.index, y='close', title=f'Recent Price Changes for {symbol}')
        fig.update_layout(
            xaxis_title='Date',
            yaxis_title='Close Price',
            template='plotly_dark',  # Use Plotly's dark theme
            plot_bgcolor='rgba(0, 0, 0, 0)',  # Transparent background
            paper_bgcolor='rgba(0, 0, 0, 0)',  # Transparent background
            font=dict(color='white'),  # White font color for better visibility
            xaxis=dict(gridcolor='gray'),  # Gray grid lines
            yaxis=dict(gridcolor='gray')   # Gray grid lines
        )

        # Convert the Plotly figure to HTML
        graph_html = fig.to_html(full_html=False)

        return render_template('plot.html', graph_html=graph_html, symbol=symbol)
    else:
        return "Failed to fetch stock data."



@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@celery.task
def fetch_stock_data(symbol):
    api_key = get_random_api_key()
    finnhub_client = finnhub.Client(api_key=api_key)
    
    try:
        quote = finnhub_client.quote(symbol)
        data = {
            'c': quote['c'],
            'h': quote['h'],
            'l': quote['l'],
            'o': quote['o'],
            'pc': quote['pc']
        }
        df = pd.DataFrame([data])
        return df
    except finnhub.FinnhubAPIException as e:
        print(f"Stock API request failed: {e}")
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
    init_db()
    app.run(debug=True)