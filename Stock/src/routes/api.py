# src/routes/api.py
from flask import Blueprint, jsonify, session, request
from ..services.market_data import fetch_stock_data, fetch_crypto_data
from ..utils.db import db

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/order_summary', methods=['POST'])
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



@api_bp.route('/api/add_to_watchlist', methods=['POST'])
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

@api_bp.route('/check-session')
def check_session():
    print("Current session:", dict(session))
    return jsonify({
        'session': dict(session),
        'username': session.get('username')
    })