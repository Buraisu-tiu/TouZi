import logging
import traceback
from flask import Blueprint, render_template, session, redirect, url_for, request, current_app, g
from utils.db import db
from utils.auth import allowed_file
from werkzeug.utils import secure_filename
import os
from google.cloud import firestore
from services.market_data import fetch_recent_orders, fetch_user_portfolio

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

user_bp = Blueprint('user', __name__)

@user_bp.route('/dashboard')
def dashboard():
    """Enhanced dashboard route with better error handling."""
    logger.info("[DASHBOARD] Starting dashboard request")
    
    if 'user_id' not in session:
        logger.warning("[DASHBOARD] No user_id in session, redirecting to login")
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = None
    portfolio_data = None
    recent_orders = None
    error_message = None

    try:
        # Fetch user data
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            logger.error(f"[DASHBOARD] User document not found for ID: {user_id}")
            return redirect(url_for('auth.login'))
        
        user = user_doc.to_dict()
        logger.info(f"[DASHBOARD] Successfully fetched user data for {user.get('username', 'unknown')}")
        
        # Get portfolio data with timeout handling
        try:
            portfolio_data = fetch_user_portfolio(user_id)
            if not portfolio_data:
                logger.warning("[DASHBOARD] No portfolio data returned")
                portfolio_data = {
                    'summary': {
                        'total_value_raw': 0,
                        'invested_value_raw': 0,
                        'available_cash_raw': user.get('balance', 0),
                        'Active Positions': 0,
                        'day_change_raw': 0,
                        "Today's P/L": '$0.00'
                    }
                }
        except Exception as e:
            logger.error(f"[DASHBOARD] Portfolio fetch error: {str(e)}")
            logger.error(traceback.format_exc())
            portfolio_data = {
                'summary': {
                    'total_value_raw': 0,
                    'invested_value_raw': 0,
                    'available_cash_raw': user.get('balance', 0),
                    'Active Positions': 0,
                    'day_change_raw': 0,
                    "Today's P/L": '$0.00'
                }
            }
        
        # Get recent orders with fallback
        try:
            recent_orders = fetch_recent_orders(user_id, limit=5)
        except Exception as e:
            logger.error(f"[DASHBOARD] Recent orders fetch error: {str(e)}")
            recent_orders = []

        # Create user portfolio summary
        user_portfolio = {
            'total_value': portfolio_data['summary'].get('total_value_raw', 0),
            'invested_value': portfolio_data['summary'].get('invested_value_raw', 0),
            'available_cash': portfolio_data['summary'].get('available_cash_raw', 0),
            'active_positions': portfolio_data['summary'].get('Active Positions', 0),
            'today_pl_str': portfolio_data['summary'].get("Today's P/L", "$0.00"),
            'today_pl_raw': portfolio_data['summary'].get('day_change_raw', 0)
        }

        logger.info("[DASHBOARD] Successfully prepared dashboard data")
        
        return render_template('dashboard.html.jinja2',
                             user=user,
                             user_portfolio=user_portfolio,
                             recent_orders=recent_orders,
                             error_message=error_message)

    except Exception as e:
        logger.error(f"[DASHBOARD] Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template('error.html.jinja2',
                             error_message="An error occurred while loading the dashboard",
                             error_details=str(e))

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

        # Update other user settings
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