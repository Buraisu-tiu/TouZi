# src/routes/api.py
from flask import Blueprint, jsonify, session, request
from utils.db import db
import requests
from utils.constants import api_keys
from google.cloud import firestore
from datetime import datetime, timedelta
from services.market_data import fetch_stock_data, fetch_crypto_data

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/price/<symbol>', methods=['GET'])
def get_price(symbol):
    price_data = fetch_stock_data(symbol)
    if price_data and 'close' in price_data:
        return jsonify({'success': True, 'price': price_data['close']})
    return jsonify({'success': False, 'error': 'Unable to fetch price'})

@api_bp.route('/api/order_summary', methods=['POST'])
def order_summary():
    if not request.is_json:
        return jsonify({'error': 'Invalid content type, expected JSON'}), 400
    data = request.json
    symbol = data.get('symbol')
    try:
        quantity = float(data.get('quantity', 0))
    except Exception:
        return jsonify({'error': 'Invalid quantity'}), 400

    if not symbol or quantity <= 0:
        return jsonify({'error': 'Invalid input parameters'}), 400

    price_data = fetch_stock_data(symbol)
    if price_data and 'close' in price_data:
        price = price_data['close']
        estimated_cost = price * quantity
        trading_fee = estimated_cost * 0.001
        total = estimated_cost + trading_fee
        return jsonify({
            'success': True,
            'estimated_price': f"${estimated_cost:.2f}",
            'trading_fee': f"${trading_fee:.2f}",
            'total': f"${total:.2f}",
            'raw_price': price,
            'raw_total': total
        })
    return jsonify({'error': 'Unable to fetch stock price'}), 400

@api_bp.route('/api/add_to_watchlist', methods=['POST'])
def add_to_watchlist():
    if 'user_id' not in session:
        return jsonify({'error': 'User not authenticated'}), 401

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

@api_bp.route('/check-session')
def check_session():
    print("Current session:", dict(session))
    return jsonify({
        'session': dict(session),
        'username': session.get('username')
    })

@api_bp.route('/api/portfolio/history')
def portfolio_history():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    user_id = session['user_id']
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    try:
        # Get transactions for last 30 days
        transactions = db.collection('transactions')\
            .where(filter=firestore.FieldFilter('user_id', '==', user_id))\
            .where(filter=firestore.FieldFilter('timestamp', '>=', start_date))\
            .order_by('timestamp')\
            .stream()

        # Create daily points
        daily_values = {}
        current_date = start_date
        
        # Get current portfolio value
        user = db.collection('users').document(user_id).get().to_dict()
        current_balance = user.get('balance', 0)
        portfolio_value = current_balance
        
        # Add value of current holdings
        portfolio_items = db.collection('portfolios')\
            .where('user_id', '==', user_id)\
            .stream()
            
        for item in portfolio_items:
            item_data = item.to_dict()
            if item_data['asset_type'] == 'stock':
                price_data = fetch_stock_data(item_data['symbol'])
                if price_data and 'close' in price_data:
                    portfolio_value += price_data['close'] * item_data['shares']
            else:  # crypto
                price_data = fetch_crypto_data(item_data['symbol'])
                if price_data and 'price' in price_data:
                    portfolio_value += price_data['price'] * item_data['shares']

        # Fill in historical points
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            daily_values[date_str] = portfolio_value
            current_date += timedelta(days=1)

        # Format for chart
        result = [
            {
                'date': date,
                'total_value': value
            }
            for date, value in sorted(daily_values.items())
        ]
        
        return jsonify(result)

    except Exception as e:
        print(f"Error fetching portfolio history: {e}")
        return jsonify({'error': str(e)}), 500