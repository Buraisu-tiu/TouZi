# src/routes/portfolio.py
from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from utils.db import db
from services.market_data import fetch_stock_data, fetch_crypto_data
from services.badge_services import check_and_award_badges
from google.cloud import firestore

portfolio_bp = Blueprint('portfolio', __name__)

@portfolio_bp.route('/portfolio/<string:user_id>')
def view_portfolio(user_id):
    user = db.collection('users').document(user_id).get()
    if not user.exists:
        return "User not found", 404

    try:
        check_and_award_badges(user_id)
    except Exception as e:
        print(f"Error checking badges for user {user_id}: {str(e)}")

    portfolios = db.collection('portfolios').where('user_id', '==', user_id).get()
    portfolio_data, total_value = [], 0

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

    badges = fetch_user_badges(user_id)
    profile_picture = user.to_dict().get('profile_picture', url_for('static', filename='default-profile.png'))
    is_developer = user.to_dict().get('username') == 'xiao'

    return render_template('portfolio.html.jinja2', 
                           user=user.to_dict(), 
                           profile_picture=profile_picture, 
                           portfolio=portfolio_data, 
                           total_value=round(total_value, 2), 
                           badges=badges, 
                           is_developer=is_developer)

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
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    user = user_ref.get().to_dict()

    if user.get('username') != 'xiao':
        return "Access denied", 403

    if request.method == 'POST':
        handle_developer_action(request.form, user_id, user_ref)

    return render_template('developer_tools.html.jinja2', user=user)

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
    badges = db.collection('user_badges').where('user_id', '==', user_id).get()
    badge_data = []
    for badge in badges:
        badge_ref = db.collection('badges').document(badge.to_dict()['badge_id']).get()
        badge_data.append({
            'name': badge_ref.to_dict()['name'],
            'description': badge_ref.to_dict()['description']
        })
    return badge_data

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
