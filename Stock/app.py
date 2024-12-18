import pandas as pd
import requests
import os
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

app = Flask(__name__)
database_uri = os.environ.get("DATABASE_URL")
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
    balance = db.Column(db.Float, nullable=False, default=1000.0)  # Initial balance of $10,000

class Portfolio(db.Model):
    __tablename__ = 'portfolios'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    symbol = db.Column(db.String(10), nullable=False)
    shares = db.Column(db.Float, nullable=False)  # Should be Float
    user = db.relationship('User', backref=db.backref('portfolios', lazy=True))




def init_db():
    with app.app_context():
        db.create_all()

@app.route('/')
def home():
    return redirect(url_for('login'))

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
    user = db.session.get(User, user_id)  # Use Session.get() method
    portfolio = Portfolio.query.filter_by(user_id=user_id).all()
    return render_template('dashboard.html', user=user, portfolio=portfolio)

@app.route('/portfolio')
def view_portfolio():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    user = db.session.get(User, user_id)  # Use Session.get() method
    portfolios = Portfolio.query.filter_by(user_id=user_id).all()
    portfolio_data = []
    total_value = 0
    for entry in portfolios:
        symbol = entry.symbol
        shares = entry.shares
        df = fetch_stock_data(symbol)
        if df is not None:
            latest_price = df.iloc[0]['c']
            stock_value = shares * latest_price
            portfolio_data.append({
                'symbol': symbol,
                'shares': shares,
                'price': latest_price,
                'value': round(stock_value, 2)
            })
            total_value += stock_value
    return render_template('portfolio.html', user=user, portfolio=portfolio_data, total_value=round(total_value, 2))


@app.route('/buy', methods=['GET', 'POST'])
def buy():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    user = db.session.get(User, user_id)  # Use Session.get() method
    common_symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    common_prices = fetch_common_stock_prices(common_symbols)
    if request.method == 'POST':
        symbol = request.form['symbol']
        df = fetch_stock_data(symbol)
        if df is not None:
            latest_price = df.iloc[0]['c']
            shares = float(request.form['shares'])  # Allow fractional shares
            cost = float(latest_price * shares)
            if user.balance >= cost:
                portfolio = Portfolio.query.filter_by(user_id=user_id, symbol=symbol).first()
                if portfolio:
                    print(f"Before update: {portfolio.shares} shares")  # Debugging statement
                    portfolio.shares = float(portfolio.shares) + shares  # Ensure correct addition of fractional shares
                    print(f"After update: {portfolio.shares} shares")  # Debugging statement
                else:
                    portfolio = Portfolio(user_id=user_id, symbol=symbol, shares=shares)
                    db.session.add(portfolio)
                user.balance = float(user.balance) - cost
                db.session.commit()
                return redirect(url_for('dashboard'))
            else:
                return "Insufficient balance to buy shares."
        else:
            return "Failed to fetch stock data."
    return render_template('buy.html', user=user, common_prices=common_prices)







@app.route('/sell', methods=['GET', 'POST'])
def sell():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    user = db.session.get(User, user_id)  # Use Session.get() method
    common_symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA']
    common_prices = fetch_common_stock_prices(common_symbols)
    if request.method == 'POST':
        symbol = request.form['symbol']
        df = fetch_stock_data(symbol)
        if df is not None:
            latest_price = df.iloc[0]['c']
            shares_to_sell = float(request.form['shares'])  # Allow fractional shares
            portfolio = Portfolio.query.filter_by(user_id=user_id, symbol=symbol).first()
            if portfolio and portfolio.shares >= shares_to_sell:
                proceeds = float(latest_price * shares_to_sell)
                portfolio.shares -= shares_to_sell
                if portfolio.shares == 0:
                    db.session.delete(portfolio)
                user.balance = float(user.balance) + proceeds
                db.session.commit()
                return redirect(url_for('dashboard'))
            else:
                return "Insufficient shares to sell."
        else:
            return "Failed to fetch stock data."
    return render_template('sell.html', user=user, common_prices=common_prices)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

def fetch_stock_data(symbol):
    api_key = 'ctcvajhr01qlc0uvn08gctcvajhr01qlc0uvn090'
    url = f'https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}'
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if "c" in data:
            df = pd.DataFrame([{
                "t": pd.Timestamp.now(),
                "c": data["c"],
                "h": data["h"],
                "l": data["l"],
                "o": data["o"],
                "pc": data["pc"]
            }])
            df.set_index('t', inplace=True)
            return df
        else:
            print("No results found in API response.")
            return None
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None

def fetch_common_stock_prices(symbols):
    api_key = 'ctcvajhr01qlc0uvn08gctcvajhr01qlc0uvn090'
    prices = {}
    for symbol in symbols:
        url = f'https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}'
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if "c" in data:
                prices[symbol] = data["c"]
            else:
                prices[symbol] = "N/A"
        except requests.exceptions.RequestException as e:
            prices[symbol] = "N/A"
            print(f"API request failed for {symbol}: {e}")
    return prices


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
