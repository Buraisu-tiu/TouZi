# src/routes/leaderboard.py
from flask import Blueprint, render_template, session
from utils.db import db
from services.market_data import calculate_total_portfolio_value

leaderboard_bp = Blueprint('leaderboard', __name__)

@leaderboard_bp.route('/leaderboard')
def leaderboard():
    # Get all users
    users = db.collection('users').stream()
    leaderboard_data = []

    # Calculate portfolio values for each user
    for user in users:
        user_data = user.to_dict()
        portfolio_value = calculate_total_portfolio_value(user.id)
        
        leaderboard_data.append({
            'username': user_data.get('username', 'Unknown'),
            'profile_picture': user_data.get('profile_picture', '/static/default-profile.png'),
            'total_value': portfolio_value['total_value'],
            'user_id': user.id  # Add user_id for profile linking
        })
    
    # Sort by total value in descending order
    leaderboard_data.sort(key=lambda x: x['total_value'], reverse=True)
    
    return render_template('leaderboard.html.jinja2', 
                         leaderboard=leaderboard_data,
                         user=session.get('user'))
