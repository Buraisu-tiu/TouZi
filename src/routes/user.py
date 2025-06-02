# src/routes/user.py
from flask import Blueprint, render_template, session, redirect, url_for, request, current_app
from utils.db import db
from utils.auth import allowed_file
from werkzeug.utils import secure_filename
import os
from google.cloud import firestore # Ensure firestore is imported
from services.market_data import fetch_recent_orders, fetch_user_portfolio # Changed import

user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    
    # Get portfolio data using the enhanced service function
    portfolio_full_data = fetch_user_portfolio(user_id)
    portfolio_summary = portfolio_full_data.get('summary', {})
    
    print(f"DEBUG [user.py - dashboard]: portfolio_summary from fetch_user_portfolio: {portfolio_summary}") # DEBUG PRINT

    # Create user portfolio object for the dashboard from the summary
    user_portfolio_summary = {
        'total_value': portfolio_summary.get('total_value_raw', 0),
        'invested_value': portfolio_summary.get('invested_value_raw', 0),
        'available_cash': portfolio_summary.get('available_cash_raw', 0),
        'active_positions': portfolio_summary.get('Active Positions', 0), # Ensure key matches
        # Add other summary fields if needed by dashboard, e.g., Today's P/L
        'today_pl_str': portfolio_summary.get("Today's P/L", "$0.00"),
        'today_pl_raw': portfolio_summary.get("day_change_raw", 0.0)
    }
    
    print(f"DEBUG [user.py - dashboard]: user_portfolio_summary created: {user_portfolio_summary}") # DEBUG PRINT
    
    # Get recent orders
    recent_orders = fetch_recent_orders(user_id, limit=5)
    
    return render_template('dashboard.html.jinja2', 
                         user=user,
                         user_portfolio=user_portfolio_summary, # Pass the adapted summary
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
                # Prepend user_id to filename to ensure uniqueness
                unique_filename = f"{user_id}_{filename}"
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(filepath)
                user_ref.update({'profile_picture': f'/static/uploads/{unique_filename}'})

        # Update other user settings - remove default profile picture fallback
        user_ref.update({
            'username': request.form.get('username', user_ref.get().to_dict().get('username')),
            'email': request.form.get('email', user_ref.get().to_dict().get('email')),
            'bio': request.form.get('bio', user_ref.get().to_dict().get('bio')),
            'background_color': request.form.get('background_color', user_ref.get().to_dict().get('background_color')),
            'text_color': request.form.get('text_color', user_ref.get().to_dict().get('text_color')),
            'accent_color': request.form.get('accent_color', user_ref.get().to_dict().get('accent_color')),
            'hover_color': request.form.get('hover_color', user_ref.get().to_dict().get('hover_color'))
        })
    
    user = user_ref.get().to_dict()
    return render_template('settings.html.jinja2', user=user)


@user_bp.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return redirect(url_for('auth.login')) # Added redirect for safety

    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)

    # Delete user's portfolio
    portfolio_query = db.collection('portfolios').where(filter=firestore.FieldFilter('user_id', '==', user_id)) # Corrected
    for doc in portfolio_query.stream():
        doc.reference.delete() # Corrected

    # Delete user's transactions
    transaction_query = db.collection('transactions').where(filter=firestore.FieldFilter('user_id', '==', user_id)) # Corrected
    for doc in transaction_query.stream():
        doc.reference.delete() # Corrected

    # Delete the user document
    user_ref.delete()

    # Clear the session
    session.clear()

    return redirect(url_for('home'))