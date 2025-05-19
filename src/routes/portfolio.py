# src/routes/portfolio.py
from flask import Blueprint, render_template, session, redirect, url_for, request, current_app
from utils.db import db
# from services.market_data import fetch_stock_data # fetch_user_portfolio will use this
from services.market_data import fetch_user_portfolio # Import the enhanced function
from datetime import datetime
import traceback

portfolio_bp = Blueprint('portfolio', __name__)

@portfolio_bp.route('/portfolio')
@portfolio_bp.route('/portfolio/')
def portfolio():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        return view_portfolio_route(session['user_id'])
    except Exception as e:
        print(f"🔴 ERROR in portfolio route: {str(e)}")
        traceback.print_exc()  # Print the full stack trace to terminal
        return render_template('error.html.jinja2',
                             error_message="An error occurred loading your portfolio",
                             error_details=str(e))


@portfolio_bp.route('/portfolio/<user_id>')
def view_portfolio_route(): # Renamed to avoid conflict with the actual logic function
    """Display the user's portfolio with accurate position values"""
    print(f"🔍 VIEW PORTFOLIO REQUEST for user_id: {user_id}")
    try:
        # Get user data
        user = db.collection('users').document(user_id).get().to_dict()
        
        portfolio_data = fetch_user_portfolio(user_id) # Use the service function

        print(f"🟢 Successfully prepared portfolio view for user {user_id}")
        
        # --- DETAILED DEBUG PRINTS ---
        print("\n--- PY DEBUG: Before render_template (Portfolio Route) ---")
        print(f"DEBUG: user type: {type(user)}, is None: {user is None}, value: {user}")
        print(f"DEBUG: portfolio_data type: {type(portfolio_data)}")
        if portfolio_data:
            print(f"DEBUG: portfolio_data summary: {portfolio_data.get('summary')}")
            print(f"DEBUG: portfolio_data positions count: {len(portfolio_data.get('positions', []))}")
        else:
            print("DEBUG: portfolio_data is None or empty")
        print("--- END PY DEBUG ---\n")
        
        return render_template('portfolio.html.jinja2',
                             user=user,
                             # Pass the whole portfolio_data object which contains 'summary' and 'positions'
                             portfolio_data_obj=portfolio_data 
                             ) 
                             
    except Exception as e:
        print(f"🔴 ERROR in view_portfolio route: {str(e)}")
        traceback.print_exc()
        return render_template('error.html.jinja2',
                             error_message="Error loading portfolio",
                             error_details=str(e))

# Add a redirect for the old transaction_history route to prevent errors
@portfolio_bp.route('/history')
def transaction_history():
    return redirect(url_for('market.transaction_history'))

# Helper functions

def calculate_profit_loss(latest_price, purchase_price):
    if purchase_price > 0:
        return round((latest_price - purchase_price) / purchase_price * 100, 2)
    return None
