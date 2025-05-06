# src/routes/user.py
from flask import Blueprint, render_template, session, redirect, url_for, request, current_app
from utils.db import db
from utils.auth import allowed_file
from werkzeug.utils import secure_filename
import os
from google.cloud import firestore
from services.market_data import fetch_recent_orders, calculate_total_portfolio_value

user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    
    # Get portfolio data including total value and positions
    portfolio_data = calculate_total_portfolio_value(user_id)
    
    # Create user portfolio object with needed values
    user_portfolio = {
        'total_value': portfolio_data['total_value'],
        'invested_value': portfolio_data['invested_value'],
        'available_cash': portfolio_data['available_cash'],
        'Active Positions': portfolio_data['active_positions']
    }
    
    # Get recent orders
    recent_orders = fetch_recent_orders(user_id, limit=5)
    
    return render_template('dashboard.html.jinja2', 
                         user=user,
                         user_portfolio=user_portfolio,
                         recent_orders=recent_orders)

@user_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    
    if request.method == 'POST':
        # Handle profile picture upload
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Use current_app to access config
                upload_folder = current_app.config['UPLOAD_FOLDER']
                # Ensure upload directory exists
                os.makedirs(upload_folder, exist_ok=True)
                file_path = os.path.join(upload_folder, filename)
                file.save(file_path)
                
                # Update Firestore with the profile picture path
                user_ref.update({'profile_picture': f'/static/uploads/{filename}'})

        # Update other user settings
        user_ref.update({
            'background_color': request.form.get('background_color', '#ffffff'),
            'text_color': request.form.get('text_color', '#000000'),
            'accent_color': request.form.get('accent_color', '#007bff'),
            'gradient_color': request.form.get('gradient_color', "#000000")
        })

        # For changes to theme/color, check for theme_change badge
        if 'background_color' in request.form or 'text_color' in request.form or 'accent_color' in request.form:
            from services.badge_services import check_and_award_badges
            check_and_award_badges(user_id)

        return redirect(url_for('user.dashboard'))
    
    user = user_ref.get().to_dict()
    return render_template('settings.html.jinja2', user=user)


@user_bp.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('auth.xlogin'))

    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)

    # Delete user's portfolio
    portfolio_query = db.collection('portfolios').where('user_id', '==', user_id)
    for doc in portfolio_query.stream():
        doc.reference.delete()

    # Delete user's transactions
    transaction_query = db.collection('transactions').where('user_id', '==', user_id)
    for doc in transaction_query.stream():
        doc.reference.delete()

    # Delete user's badges
    user_badges_query = db.collection('user_badges').where('user_id', '==', user_id)
    for doc in user_badges_query.stream():
        doc.reference.delete()

    # Delete the user document
    user_ref.delete()

    # Clear the session
    session.clear()

    return redirect(url_for('home'))