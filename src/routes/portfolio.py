# src/routes/portfolio.py
from flask import Blueprint, render_template, session, redirect, url_for, request
from utils.db import db
from services.market_data import fetch_stock_data, fetch_crypto_data
from services.badge_services import check_and_award_badges
import requests
import firestore


portfolio_bp = Blueprint('portfolio', __name__)

@portfolio_bp.route('/portfolio/<string:user_id>')
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
    is_developer = user.to_dict().get('username') == 'xiao'
    return render_template('portfolio.html.jinja2', 
                           user=user.to_dict(), 
                           profile_picture=profile_picture, 
                           portfolio=portfolio_data, 
                           total_value=round(total_value, 2), 
                           badges=badge_data, 
                           is_developer=is_developer)



@portfolio_bp.route('/history')
def transaction_history():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
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







    return render_template('history.html.jinja2', history=history, user=user)            })            'profit_loss': round(t_data.get('profit_loss', 0.0), 2)            'total': t_data['total_amount'],            'price': t_data['price'],
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
        action = request.form.get('action')
        if action == 'add_stock_or_crypto':
            symbol = request.form.get('symbol').upper()
            shares = float(request.form.get('shares'))
            asset_type = request.form.get('asset_type')
            db.collection('portfolios').add({
                'user_id': user_id,
                'symbol': symbol,
                'shares': shares,
                'asset_type': asset_type,
                'purchase_price': 0,  # Default value
                'total_cost': 0,  # Default value
                'last_updated': firestore.SERVER_TIMESTAMP
            })
        elif action == 'add_badge':
            badge_id = request.form.get('badge_id')
            db.collection('user_badges').add({
                'user_id': user_id,
                'badge_id': badge_id,
                'awarded_at': firestore.SERVER_TIMESTAMP
            })
        elif action == 'add_money':
            amount = float(request.form.get('amount'))
            new_balance = user.get('balance', 0) + amount
            user_ref.update({'balance': new_balance})

    return render_template('developer_tools.html.jinja2', user=user)
