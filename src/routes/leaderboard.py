# src/routes/leaderboard.py
from flask import Blueprint, render_template, session, redirect, url_for
from utils.db import db
from services.market_data import calculate_total_portfolio_value
from datetime import datetime

leaderboard_bp = Blueprint('leaderboard', __name__)

@leaderboard_bp.route('/leaderboard')
def leaderboard():
    """Display the leaderboard of users ranked by portfolio value."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    # Get the current user
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    
    # Get all users from database
    users = []
    user_docs = db.collection('users').stream()
    
    for user_doc in user_docs:
        user_data = user_doc.to_dict()
        portfolio_value = calculate_total_portfolio_value(user_doc.id)
        
        users.append({
            'user_id': user_doc.id,
            'username': user_data.get('username', 'Unknown'),
            'avatar': user_data.get('profile_picture', '/static/default-profile.png'),
            'join_date': user_data.get('join_date', datetime.utcnow()),
            'total_value': portfolio_value['total_value'],
            'is_current_user': user_doc.id == user_id
        })
    
    # Sort users by total portfolio value
    users = sorted(users, key=lambda x: x['total_value'], reverse=True)
    
    # Add rank to each user
    for i, user_item in enumerate(users):
        user_item['rank'] = i + 1
    
    return render_template('leaderboard.html.jinja2', 
                          user=user,
                          users=users)
