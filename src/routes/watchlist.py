# src/routes/watchlist.py
"""
Watchlist module for handling watchlist operations.
"""

import traceback
from flask import Blueprint, request, jsonify, session
from google.cloud import firestore

# Local imports
from utils.db import db
# Assuming fetch_stock_data is available, if not, this will need a fallback or proper import
try:
    from services.market_data import fetch_stock_data
except ImportError:
    print("WARNING [watchlist.py]: services.market_data.fetch_stock_data not found. Using fallback.")
    def fetch_stock_data(symbol): # Fallback
        return {'symbol': symbol, 'close': 0.0, 'prev_close': 0.0}

# Create the blueprint with explicit url_prefix to ensure routes are registered properly
watchlist_bp = Blueprint('watchlist', __name__, url_prefix='')
print(f"[WATCHLIST_PY] Blueprint '{watchlist_bp.name}' created.")

def fetch_watchlist(user_id):
    """
    Fetches watchlist items for a given user_id.
    This function is intended to be importable by other modules.
    """
    print(f"[WATCHLIST_PY] fetch_watchlist called for user_id: {user_id}")
    watchlist_items = []
    try:
        watchlist_ref = db.collection('watchlists').document(user_id)
        watchlist_doc = watchlist_ref.get()

        if watchlist_doc.exists:
            watchlist_data = watchlist_doc.to_dict()
            symbols = watchlist_data.get('symbols', [])
            print(f"[WATCHLIST_PY] User {user_id} has symbols: {symbols}")

            for symbol in symbols:
                # In a real scenario, you'd fetch current price data here
                # For now, just returning symbol
                price_data = fetch_stock_data(symbol) # Fetch real data
                current_price = price_data.get('close', 0)
                prev_close = price_data.get('prev_close', 0)
                price_change = current_price - prev_close
                change_percentage = (price_change / prev_close * 100) if prev_close else 0
                
                watchlist_items.append({
                    'symbol': symbol,
                    'current_price': f"${current_price:.2f}",
                    'price_change': f"${price_change:.2f}", # Placeholder
                    'change_percentage': change_percentage  # Placeholder
                })
        else:
            print(f"[WATCHLIST_PY] No watchlist found for user {user_id}")
    except Exception as e:
        print(f"[WATCHLIST_PY] Error in fetch_watchlist for user {user_id}: {e}")
        print(traceback.format_exc())
    return watchlist_items

@watchlist_bp.route('/api/watchlist/add', methods=['POST'])
def api_add_to_watchlist():
    """API endpoint to add a symbol to the user's watchlist."""
    print(f"[WATCHLIST] Received request to /api/watchlist/add: {request.json}")
    
    # Check authentication
    if 'user_id' not in session:
        print("[WATCHLIST] User not authenticated")
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    if not request.is_json:
        print("[WATCHLIST] Invalid request format - not JSON")
        return jsonify({'success': False, 'error': 'Invalid request format, expected JSON'}), 400
    
    data = request.get_json()
    symbol = data.get('symbol', '').strip().upper()
    
    print(f"[WATCHLIST] Adding symbol: {symbol} to watchlist for user: {session['user_id']}")
    
    if not symbol:
        return jsonify({'success': False, 'error': 'No symbol provided'}), 400
    
    user_id = session.get('user_id')
    
    try:
        # Check if watchlist exists
        watchlist_ref = db.collection('watchlists').document(user_id)
        watchlist_doc = watchlist_ref.get()
        
        if watchlist_doc.exists:
            # Update existing watchlist
            watchlist_data = watchlist_doc.to_dict()
            symbols = watchlist_data.get('symbols', [])
            
            if symbol in symbols:
                print(f"[WATCHLIST] {symbol} already in watchlist")
                return jsonify({'success': True, 'message': f'{symbol} is already in your watchlist'})
                
            symbols.append(symbol)
            watchlist_ref.update({
                'symbols': symbols,
                'last_updated': firestore.SERVER_TIMESTAMP
            })
        else:
            # Create new watchlist
            watchlist_ref.set({
                'user_id': user_id,
                'symbols': [symbol],
                'created_at': firestore.SERVER_TIMESTAMP,
                'last_updated': firestore.SERVER_TIMESTAMP
            })
        
        # Return successful response
        print(f"[WATCHLIST] Successfully added {symbol} to watchlist")
        return jsonify({
            'success': True,
            'message': f'{symbol} added to watchlist successfully'
        })
    except Exception as e:
        print(f"[WATCHLIST] Error adding to watchlist: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@watchlist_bp.route('/api/watchlist', methods=['POST'])
def api_watchlist_action():
    """API endpoint to handle watchlist actions (add/remove)."""
    print(f"[WATCHLIST] Received request to /api/watchlist: {request.json}")
    
    # Check authentication
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Invalid request format, expected JSON'}), 400
        
    data = request.get_json()
    action = data.get('action')
    symbol = data.get('symbol', '').strip().upper()
    
    if not symbol:
        return jsonify({'success': False, 'error': 'No symbol provided'}), 400
    
    if action == 'add':
        # Call the existing add function
        return api_add_to_watchlist()
    return jsonify({'success': False, 'error': 'Invalid or unimplemented action'}), 400

@watchlist_bp.route('/watchlist/add', methods=['POST'])
def watchlist_add_alias():
    """Another endpoint for adding to watchlist (for backward compatibility)."""
    print("[WATCHLIST] Received request to /watchlist/add")
    return api_add_to_watchlist()

# Print confirmation of blueprint creation
print(f"[WATCHLIST] Registered direct API endpoints on watchlist blueprint")
print(f"[WATCHLIST_PY] Routes defined for '{watchlist_bp.name}'.")