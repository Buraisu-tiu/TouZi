# src/routes/dev.py
from flask import Blueprint, jsonify, session, request
from utils.db import db
from firebase_admin import firestore

dev_bp = Blueprint('dev', __name__)

@dev_bp.route('/api/dev/add-stock', methods=['POST'])
def dev_add_stock():
    print("Add stock route called")
    if session.get('user_id') != 'xiao':  # Replace with actual user_id for 'xiao'
        print(f"Unauthorized attempt to add stock. Session user_id: {session.get('user_id')}")
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    user_id = data.get('user_id')
    symbol = data.get('symbol')
    quantity = float(data.get('quantity', 0))
    
    print(f"Adding stock: {symbol} for user_id: {user_id}")
    
    if not all([user_id, symbol, quantity]):
        print("Missing required fields")
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Add stock to portfolio
    db.collection('portfolios').add({
        'user_id': user_id,
        'symbol': symbol.upper(),
        'shares': quantity,
        'purchase_price': 0,
    })
    
    print(f"Successfully added {quantity} shares of {symbol} for {user_id}")
    return jsonify({'message': 'Stock added successfully'})

@dev_bp.route('/api/dev/update-balance', methods=['POST'])
def dev_update_balance():
    print("DEBUG: Update balance route triggered")
    print(f"Session user_id: {session.get('user_id')}")
    
    if session.get('user_id') != 'xiao':
        print("ERROR: Unauthorized attempt to update balance")
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    print(f"Received data: {data}")

    user_id = data.get('user_id')
    balance = float(data.get('balance', 0))

    if not user_id:
        print("ERROR: Missing user_id")
        return jsonify({'error': 'Invalid user_id'}), 400

    print(f"Processing balance update for user {user_id} to {balance}")
    
    try:
        user_ref = db.collection('users').where('user_id', '==', user_id).limit(1).get()
        if not user_ref:
            print("ERROR: User not found")
            return jsonify({'error': 'User not found'}), 404

        user_ref[0].reference.update({'balance': balance})
        print("SUCCESS: Balance updated")
        return jsonify({'message': 'Balance updated successfully'})
    except Exception as e:
        print(f"ERROR: Failed to update balance - {str(e)}")
        return jsonify({'error': f'Failed to update balance: {str(e)}'}), 500


@dev_bp.route('/api/dev/add-badge', methods=['POST'])
def dev_add_badge():
    print("DEBUG: Add badge route triggered")
    print(f"Session user_id: {session.get('user_id')}")

    if session.get('user_id') != 'xiao':
        print("ERROR: Unauthorized attempt to add badge")
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    print(f"Received data: {data}")

    user_id = data.get('user_id')
    badge_name = data.get('badge')

    if not all([user_id, badge_name]):
        print("ERROR: Missing required fields")
        return jsonify({'error': 'Missing required fields'}), 400

    print(f"Processing badge addition: {badge_name} for user {user_id}")

    try:
        badge_query = db.collection('badges').where('name', '==', badge_name).limit(1).get()
        if not badge_query:
            print("ERROR: Badge not found")
            return jsonify({'error': 'Badge not found'}), 404

        badge_id = badge_query[0].id
        db.collection('user_badges').add({
            'user_id': user_id,
            'badge_id': badge_id,
            'date_earned': firestore.SERVER_TIMESTAMP
        })
        print("SUCCESS: Badge added")
        return jsonify({'message': 'Badge added successfully'})
    except Exception as e:
        print(f"ERROR: Failed to add badge - {str(e)}")
        return jsonify({'error': f'Failed to add badge: {str(e)}'}), 500
