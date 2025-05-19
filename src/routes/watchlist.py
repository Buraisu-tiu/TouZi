# src/routes/watchlist.py
from flask import Blueprint, jsonify, session, request
from utils.db import db
from services.market_data import fetch_stock_data, fetch_crypto_data, calculate_price_change
from datetime import datetime

watchlist_bp = Blueprint('watchlist', __name__)

@watchlist_bp.route('/api/add_to_watchlist', methods=['POST'])
def add_to_watchlist():
    if 'user_id' not in session:
        return jsonify({'error': 'User not authenticated'}), 401

    user_id = session['user_id']
    data = request.json
    symbol = data.get('symbol')

    if not symbol:
        return jsonify({'error': 'Missing symbol'}), 400

    # Remove special prefixes that might have been used before
    symbol = symbol.replace('CRYPTO:', '')

    watchlist_ref = db.collection('watchlists').document(user_id)
    watchlist_doc = watchlist_ref.get()

    if watchlist_doc.exists:
        watchlist = watchlist_doc.to_dict()
        symbols = watchlist.get('symbols', [])
        if symbol not in symbols:
            symbols.append(symbol)
            watchlist_ref.update({'symbols': symbols})
    else:
        watchlist_ref.set({'symbols': [symbol]})

    return jsonify({'success': True, 'message': 'Added to watchlist'})

@watchlist_bp.route('/api/set_alert', methods=['POST'])
def set_price_alert():
    if 'user_id' not in session:
        return jsonify({'error': 'User not authenticated'}), 401

    data = request.json
    symbol = data.get('symbol')
    target_price = float(data.get('target_price', 0))
    
    if not symbol or target_price <= 0:
        return jsonify({'error': 'Invalid parameters'}), 400

    watchlist_ref = db.collection('watchlists').document(session['user_id'])
    watchlist_doc = watchlist_ref.get()

    if not watchlist_doc.exists:
        return jsonify({'error': 'Watchlist not found'}), 404

    alerts = watchlist_doc.get('price_alerts', {})
    alerts[symbol] = target_price
    
    watchlist_ref.update({
        'price_alerts': alerts
    })

    return jsonify({'success': True, 'message': 'Price alert set'})

def fetch_watchlist(user_id: str) -> list[dict]:
    try:
        watchlist_ref = db.collection('watchlists').document(user_id)
        watchlist_doc = watchlist_ref.get()

        if not watchlist_doc.exists:
            return []

        watchlist_data = watchlist_doc.to_dict()
        symbols = watchlist_data.get('symbols', [])
        processed_items = []

        for symbol in symbols:
            # Remove special prefixes if they still exist in older data
            clean_symbol = symbol.replace('CRYPTO:', '')
            
            try:
                # Fetch price data using the unified method
                price_data = fetch_stock_data(clean_symbol)

                if not price_data or 'error' in price_data:
                    continue

                current_price = price_data.get('close', 0)
                prev_price = price_data.get('prev_close', current_price)
                monthly_price = price_data.get('monthly_price', current_price)

                # Calculate 24h change
                change_pct, change_str = calculate_price_change(current_price, prev_price)
                
                # Calculate 30d change
                monthly_change, monthly_change_str = calculate_price_change(current_price, monthly_price)

                processed_items.append({
                    'symbol': clean_symbol,
                    'current_price': f"${current_price:.2f}",
                    'price_change': change_str,
                    'change_percentage': change_pct,
                    'monthly_change': monthly_change,
                    'monthly_change_str': monthly_change_str,
                    'added_date': watchlist_data.get('added_date', datetime.utcnow()),
                    'notes': watchlist_data.get('notes', ''),
                    'alert_price': watchlist_data.get('alert_price')
                })

            except Exception as e:
                continue

        return sorted(processed_items, 
                     key=lambda x: abs(x['change_percentage']), 
                     reverse=True)

    except Exception as e:
        return []

def check_price_alerts(user_id: str, symbol: str, current_price: float) -> list:
    """Check if any price alerts have been triggered"""
    watchlist_ref = db.collection('watchlists').document(user_id)
    watchlist_doc = watchlist_ref.get()
    
    if not watchlist_doc.exists:
        return []

    alerts = watchlist_doc.get('price_alerts', {})
    triggered_alerts = []
    
    if symbol in alerts and abs(current_price - alerts[symbol]) < 0.01:
        triggered_alerts.append({
            'symbol': symbol,
            'target_price': alerts[symbol],
            'current_price': current_price
        })
        
        # Remove triggered alert
        del alerts[symbol]
        watchlist_ref.update({'price_alerts': alerts})
    
    return triggered_alerts