# src/routes/leaderboard.py
from flask import Blueprint, jsonify, session, render_template, redirect, url_for, request
from utils.db import db, redis_client
from services.market_data import fetch_stock_data, fetch_crypto_data
from firebase_admin import firestore
import json

leaderboard_bp = Blueprint('leaderboard', __name__)

def calculate_portfolio_value(user_id):
    try:
        total_value = 0
        # Get user's balance
        user_ref = db.collection('users').document(user_id)
        user_data = user_ref.get().to_dict()
        total_value += user_data.get('balance', 0)

        # Get user's portfolio holdings
        portfolio_items = db.collection('portfolios').where('user_id', '==', user_id).stream()
        
        for item in portfolio_items:
            item_data = item.to_dict()
            current_price = 0
            
            if item_data['asset_type'] == 'stock':
                stock_data = fetch_stock_data(item_data['symbol'])
                if stock_data and 'close' in stock_data:
                    current_price = stock_data['close']
            elif item_data['asset_type'] == 'crypto':
                crypto_data = fetch_crypto_data(item_data['symbol'])
                if crypto_data and 'price' in crypto_data:
                    current_price = crypto_data['price']
                    
            total_value += item_data.get('shares', 0) * current_price
            
        return round(total_value, 2)
    except Exception as e:
        print(f"Error calculating portfolio value: {e}")
        return 0.0

def calculate_win_rate(user_id):
    try:
        # Get user's transactions
        transactions = db.collection('transactions')\
            .where('user_id', '==', user_id)\
            .where('transaction_type', '==', 'SELL')\
            .stream()
        
        total_trades = 0
        winning_trades = 0
        
        for trade in transactions:
            trade_data = trade.to_dict()
            if 'price' in trade_data and 'total_amount' in trade_data:
                total_trades += 1
                # Calculate if trade was profitable
                if trade_data.get('profit_loss', 0) > 0:
                    winning_trades += 1
        
        if total_trades == 0:
            return 0
            
        win_rate = (winning_trades / total_trades) * 100
        return round(win_rate, 1)
    except Exception as e:
        print(f"Error calculating win rate: {e}")
        return 0.0

@leaderboard_bp.route('/leaderboard')
def leaderboard():
    try:
        # Fetch all users
        users_query = db.collection('users').stream()
        users = []

        for user_doc in users_query:
            user_data = user_doc.to_dict()
            user_id = user_doc.id

            # Debugging: Print user data to verify
            print(f"Fetched user: {user_data}")

            # Calculate total portfolio value
            portfolio_query = db.collection('portfolios').where('user_id', '==', user_id).stream()
            total_value = user_data.get('balance', 0)
            wins, losses = 0, 0

            for portfolio_item in portfolio_query:
                item_data = portfolio_item.to_dict()
                if item_data['asset_type'] == 'stock':
                    stock_data = fetch_stock_data(item_data['symbol'])
                    if stock_data and 'close' in stock_data:
                        total_value += stock_data['close'] * item_data['shares']
                        if stock_data['close'] > item_data['purchase_price']:
                            wins += 1
                        else:
                            losses += 1
                elif item_data['asset_type'] == 'crypto':
                    crypto_data = fetch_crypto_data(item_data['symbol'])
                    if crypto_data and 'price' in crypto_data:
                        total_value += crypto_data['price'] * item_data['shares']
                        if crypto_data['price'] > item_data['purchase_price']:
                            wins += 1
                        else:
                            losses += 1

            win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

            users.append({
                'user_id': user_id,
                'username': user_data.get('username', 'Unknown'),
                'total_value': round(total_value, 2),
                'win_rate': round(win_rate, 2),
                'profile_picture': user_data.get('profile_picture', url_for('static', filename='default-profile.png'))
            })

        # Debugging: Print the list of users
        print(f"Users for leaderboard: {users}")

        # Sort users by total portfolio value in descending order
        users = sorted(users, key=lambda x: x['total_value'], reverse=True)

        return render_template('leaderboard.html.jinja2', users=users)

    except Exception as e:
        print(f"Error fetching leaderboard data: {e}")
        return "An error occurred while fetching the leaderboard.", 500

@leaderboard_bp.route('/api/leaderboard-data')
def leaderboard_data():
    try:
        # Get current user's ID for group leaderboard filtering
        current_user_id = session.get('user_id')
        
        # Fetch all users for global leaderboard
        users = db.collection('users').stream()
        global_leaderboard = []
        
        for user in users:
            user_data = user.to_dict()
            portfolio_query = db.collection('portfolios')\
                .where('user_id', '==', user.id)\
                .stream()
            
            # Calculate total account value
            account_value = user_data.get('balance', 0)
            for item in portfolio_query:
                item_data = item.to_dict()
                current_price = 0
                
                if item_data['asset_type'] == 'stock':
                    stock_data = fetch_stock_data(item_data['symbol'])
                    current_price = stock_data.get('close', 0)
                elif item_data['asset_type'] == 'crypto':
                    crypto_data = fetch_crypto_data(item_data['symbol'])
                    current_price = crypto_data.get('price', 0)
                
                share_value = item_data.get('shares', 0) * current_price
                account_value += share_value

            global_leaderboard.append({
                'id': user.id,
                'username': user_data.get('username', 'Unknown'),
                'account_value': round(account_value, 2),
                'profile_picture': user_data.get('profile_picture', ''),
                'accent_color': user_data.get('accent_color', '#007bff'),
                'text_color': user_data.get('text_color', '#ffffff')
            })

        # Sort global leaderboard by account value
        global_leaderboard.sort(key=lambda x: x['account_value'], reverse=True)
        
        # Fetch group leaderboards for current user
        group_leaderboards = []
        if current_user_id:
            group_refs = db.collection('group_leaderboards')\
                .where('member_ids', 'array_contains', current_user_id)\
                .stream()
            
            for group in group_refs:
                group_data = group.to_dict()
                member_data = []
                
                # Fetch data for each member in the group
                for member_id in group_data.get('member_ids', []):
                    member = next((u for u in global_leaderboard if u['id'] == member_id), None)
                    if member:
                        member_data.append(member)
                
                # Sort group members by account value
                member_data.sort(key=lambda x: x['account_value'], reverse=True)
                
                group_leaderboards.append({
                    'id': group.id,
                    'name': group_data.get('name', 'Unnamed Group'),
                    'members': member_data,
                    'created_by': group_data.get('created_by')
                })

        return jsonify({
            'status': 'success',
            'global_leaderboard': global_leaderboard,
            'group_leaderboards': group_leaderboards
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


def create_group_leaderboard_helper(user_id, data):  # Renamed to avoid conflict
    if not data.get('name'):
        return jsonify({'error': 'Group name is required'}), 400

    # Initialize members with the creator's ID
    member_ids = [user_id]

    # Add other members if provided
    if data.get('members'):
        if not isinstance(data['members'], list):
            return jsonify({'error': 'Members must be an array'}), 400
        member_ids.extend(data['members'])

    # Remove duplicates while preserving order
    member_ids = list(dict.fromkeys(member_ids))

    print(f"Creating group with members: {member_ids}")

    try:
        # Verify members exist by trying to get each user document
        valid_members = []
        for member_id in member_ids:
            user_ref = db.collection('users').document(member_id)
            if user_ref.get().exists:
                valid_members.append(member_id)
            
        if not valid_members:
            return jsonify({'error': 'No valid members found'}), 400

        new_group = {
            'name': data['name'],
            'created_by': user_id,
            'member_ids': valid_members,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        # Create new group leaderboard
        group_ref = db.collection('group_leaderboards').add(new_group)
        
        return jsonify({
            'success': True,
            'message': 'Group leaderboard created',
            'id': group_ref[1].id
        })

    except Exception as e:
        print(f"Error creating group: {str(e)}")
        return jsonify({
            'error': f'Failed to create group leaderboard: {str(e)}'
        }), 500

@leaderboard_bp.route('/create_group_leaderboard', methods=['POST'])
def create_group_leaderboard():
    if 'user_id' not in session:
        return jsonify({'error': 'User not authenticated'}), 401
    
    print(f"Session user_id: {session['user_id']}")
    print(f"Request data: {request.json}")
    
    return create_group_leaderboard_helper(session['user_id'], request.json)

# And make sure your route is defined like this:
@leaderboard_bp.route('/create_group_leaderboard', methods=['POST'])
def create_group_leaderboard_route():
    if 'user_id' not in session:
        return jsonify({'error': 'User not authenticated'}), 401
    
    return create_group_leaderboard(session['user_id'], request.json)

@leaderboard_bp.route('/api/users')
def get_users():
    if 'user_id' not in session:
        return jsonify({'error': 'User not authenticated'}), 401

    try:
        # Fetch all users from Firestore
        users_ref = db.collection('users').stream()
        users = [{'id': user.id, 'username': user.to_dict().get('username')} for user in users_ref]
        
        return jsonify({
            'status': 'success',
            'users': users
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

        
@leaderboard_bp.route('/group_leaderboard/<group_id>/leave', methods=['POST'])
def leave_group(group_id):
    if 'user_id' not in session:
        return jsonify({'error': 'User not authenticated'}), 401

    user_id = session['user_id']

    try:
        group_ref = db.collection('group_leaderboards').document(group_id)
        group = group_ref.get()

        if not group.exists:
            return jsonify({'error': 'Group not found'}), 404

        group_data = group.to_dict()
        member_ids = group_data.get('member_ids', [])

        if user_id not in member_ids:
            return jsonify({'error': 'You are not a member of this group'}), 400

        # Remove the user from the group
        group_ref.update({
            'member_ids': firestore.ArrayRemove([user_id])
        })

        return jsonify({
            'success': True,
            'message': 'Successfully left the group'
        })

    except Exception as e:
        return jsonify({
            'error': f'Failed to leave group: {str(e)}'
        }), 500
        
        
@leaderboard_bp.route('/group_leaderboard/<group_id>/add_member', methods=['POST'])
def add_group_member(group_id):
    if 'user_id' not in session:
        return jsonify({'error': 'User not authenticated'}), 401

    current_user_id = session['user_id']
    data = request.json
    member_username = data.get('username')

    if not member_username:
        return jsonify({'error': 'Username is required'}), 400

    try:
        # Get the group and verify the current user is the creator
        group_ref = db.collection('group_leaderboards').document(group_id)
        group = group_ref.get()
        
        if not group.exists:
            return jsonify({'error': 'Group not found'}), 404
            
        group_data = group.to_dict()
        if group_data['created_by'] != current_user_id:
            return jsonify({'error': 'Only the group creator can add members'}), 403

        # Find user by username
        user_query = db.collection('users')\
            .where('username', '==', member_username)\
            .limit(1)\
            .get()

        if not user_query:
            return jsonify({'error': 'User not found'}), 404

        new_member_id = user_query[0].id
        
        # Check if user is already a member
        if new_member_id in group_data.get('member_ids', []):
            return jsonify({'error': 'User is already a member'}), 400

        # Add the new member
        group_ref.update({
            'member_ids': firestore.ArrayUnion([new_member_id])
        })

        return jsonify({
            'success': True,
            'message': f'Added {member_username} to the group'
        })

    except Exception as e:
        return jsonify({
            'error': f'Failed to add member: {str(e)}'
        }), 500
