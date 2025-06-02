# src/routes/leaderboard.py
from flask import Blueprint, render_template, session, redirect, url_for
from utils.db import db
from services.market_data import calculate_total_portfolio_value
from datetime import datetime
import traceback

leaderboard_bp = Blueprint('leaderboard', __name__)

@leaderboard_bp.route('/leaderboard')
def leaderboard():
    """Display the leaderboard of users ranked by portfolio value."""
    print("\n" + "="*50)
    print("[LEADERBOARD] Route accessed!")
    print("="*50)
    
    if 'user_id' not in session:
        print("[LEADERBOARD] No user_id in session, redirecting to login")
        return redirect(url_for('auth.login'))

    # Get the current user
    user_id = session['user_id']
    print(f"[LEADERBOARD] Processing leaderboard for user_id: {user_id}")
    
    try:
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            print(f"[LEADERBOARD] ERROR: User document not found for user_id: {user_id}")
            return redirect(url_for('auth.login'))
        
        user = user_doc.to_dict()
        print(f"[LEADERBOARD] Current user: {user.get('username', 'Unknown')}")
        
        # Get all users from database
        print("[LEADERBOARD] Fetching all users from database...")
        users = []
        user_docs = db.collection('users').stream()
        
        user_count = 0
        for user_doc in user_docs:
            user_count += 1
            try:
                user_data = user_doc.to_dict()
                username = user_data.get('username', 'Unknown')
                print(f"[LEADERBOARD] Processing user {user_count}: {username} (ID: {user_doc.id})")
                
                # Calculate portfolio value using the same method as portfolio route
                portfolio_value = calculate_total_portfolio_value(user_doc.id)
                print(f"[LEADERBOARD] Portfolio value for {username}: {portfolio_value}")
                
                # Fix avatar handling - return None if no custom profile picture
                profile_picture = user_data.get('profile_picture')
                avatar = None
                if profile_picture:
                    # Check if it's a real custom profile picture
                    if not any(default in profile_picture.lower() for default in ['default-profile', 'placeholder', user_data.get('username', '').lower()]):
                        # Only set avatar if it's not a default/placeholder image
                        avatar = profile_picture
                
                users.append({
                    'user_id': user_doc.id,
                    'username': username,
                    'avatar': avatar,  # This will be None if no custom avatar
                    'join_date': user_data.get('join_date', datetime.utcnow()),
                    'total_value': portfolio_value['total_value'],
                    'is_current_user': user_doc.id == user_id
                })
                
                print(f"[LEADERBOARD] Added user {username} to leaderboard data with avatar: {avatar}")
                
            except Exception as e:
                print(f"[LEADERBOARD] ERROR processing user {user_doc.id}: {str(e)}")
                print(f"[LEADERBOARD] Traceback: {traceback.format_exc()}")
                continue
        
        print(f"[LEADERBOARD] Total users processed: {len(users)}")
        
        # Sort users by total portfolio value
        users = sorted(users, key=lambda x: x['total_value'], reverse=True)
        
        # Add rank to each user
        for i, user_item in enumerate(users):
            user_item['rank'] = i + 1
        
        print(f"[LEADERBOARD] Final leaderboard data:")
        for i, u in enumerate(users[:5]):  # Show top 5 in debug
            print(f"[LEADERBOARD]   {i+1}. {u['username']}: ${u['total_value']:.2f}")
        
        print(f"[LEADERBOARD] Rendering template with {len(users)} users")
        
        return render_template('leaderboard.html.jinja2', 
                              user=user,
                              users=users)
                              
    except Exception as e:
        print(f"[LEADERBOARD] CRITICAL ERROR in leaderboard route: {str(e)}")
        print(f"[LEADERBOARD] Full traceback: {traceback.format_exc()}")
        
        # Return template with empty data on error
        return render_template('leaderboard.html.jinja2', 
                              user=user if 'user' in locals() else {'username': 'Error'},
                              users=[])
