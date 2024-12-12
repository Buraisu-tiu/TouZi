import os
import sqlite3
import pandas as pd
import requests
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database setup
def init_db():
    conn = sqlite3.connect('trading_simulator.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            symbol TEXT,
            shares INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('trading_simulator.db')
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('trading_simulator.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            return 'Invalid credentials'
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = sqlite3.connect('trading_simulator.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM portfolios WHERE user_id = ?', (user_id,))
    portfolio = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', portfolio=portfolio)

@app.route('/buy', methods=['GET', 'POST'])
def buy():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        symbol = request.form['symbol']
        df = fetch_stock_data(symbol)
        if df is not None:
            latest_price = df.iloc[0]['c']
            shares = int(request.form['shares'])
            user_id = session['user_id']
            conn = sqlite3.connect('trading_simulator.db')
            cursor = conn.cursor()
            cursor.execute('SELECT shares FROM portfolios WHERE user_id = ? AND symbol = ?', (user_id, symbol))
            result = cursor.fetchone()
            if result:
                total_shares = result[0] + shares
                cursor.execute('UPDATE portfolios SET shares = ? WHERE user_id = ? AND symbol = ?', (total_shares, user_id, symbol))
            else:
                cursor.execute('INSERT INTO portfolios (user_id, symbol, shares) VALUES (?, ?, ?)', (user_id, symbol, shares))
            conn.commit()
            conn.close()
            return redirect(url_for('dashboard'))
        else:
            return "Failed to fetch stock data."
    return render_template('buy.html')


@app.route('/sell', methods=['GET', 'POST'])
def sell():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        symbol = request.form['symbol']
        df = fetch_stock_data(symbol)
        if df is not None:
            latest_price = df.iloc[0]['c']
            shares_to_sell = int(request.form['shares'])
            user_id = session['user_id']
            conn = sqlite3.connect('trading_simulator.db')
            cursor = conn.cursor()
            cursor.execute('SELECT shares FROM portfolios WHERE user_id = ? AND symbol = ?', (user_id, symbol))
            result = cursor.fetchone()
            if result and result[0] >= shares_to_sell:
                remaining_shares = result[0] - shares_to_sell
                if remaining_shares > 0:
                    cursor.execute('UPDATE portfolios SET shares = ? WHERE user_id = ? AND symbol = ?', (remaining_shares, user_id, symbol))
                else:
                    cursor.execute('DELETE FROM portfolios WHERE user_id = ? AND symbol = ?', (user_id, symbol))
                conn.commit()
                conn.close()
                return redirect(url_for('dashboard'))
            else:
                conn.close()
                return "Insufficient shares to sell."
        else:
            return "Failed to fetch stock data."
    return render_template('sell.html')


@app.route('/portfolio')
def view_portfolio():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conn = sqlite3.connect('trading_simulator.db')
    cursor = conn.cursor()
    cursor.execute('SELECT symbol, SUM(shares) FROM portfolios WHERE user_id = ? GROUP BY symbol', (user_id,))
    portfolio = cursor.fetchall()
    conn.close()
    portfolio_data = []
    total_value = 0
    for entry in portfolio:
        symbol = entry[0]
        shares = entry[1]
        print(f"Symbol: {symbol}, Shares: {shares}")
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
    return render_template('portfolio.html', portfolio=portfolio_data, total_value=round(total_value, 2))



@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

def fetch_stock_data(symbol):
    api_key = 'ctcvajhr01qlc0uvn08gctcvajhr01qlc0uvn090'
    url = f'https://finnhub.io/api/v1/quote?symbol={symbol}&token={api_key}'
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an HTTPError for bad responses
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

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
