# src/routes/portfolio.py
from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from utils.db import db
from services.market_data import fetch_stock_data
from services.badge_services import check_and_award_badges
from google.cloud import firestore
from datetime import datetime
import traceback
import sys

portfolio_bp = Blueprint('portfolio', __name__)

@portfolio_bp.route('/portfolio')
@portfolio_bp.route('/portfolio/')
def portfolio():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    try:
        return view_portfolio(session['user_id'])
    except Exception as e:
        print(f"🔴 ERROR in portfolio route: {str(e)}")
        traceback.print_exc(file=sys.stdout)  # Print the full stack trace to terminal
        return render_template('error.html.jinja2', 
                            error_message="An error occurred loading your portfolio",
                            error_details=str(e))

@portfolio_bp.route('/portfolio/<user_id>')
def view_portfolio(user_id):
    print(f"\n🔍 VIEW PORTFOLIO REQUEST for user_id: {user_id}")
    try:
        user = db.collection('users').document(user_id).get()
        if not user.exists:
            print(f"🔴 ERROR: User with ID {user_id} not found")
            return "User not found", 404

        # Check and award any new badges
        try:
            check_and_award_badges(user_id)
        except Exception as badge_error:
            print(f"⚠️ Badge check warning: {str(badge_error)}")
            # Continue despite badge error

        # Get portfolio data
        try:
            print(f"📊 Fetching portfolio data for user {user_id}")
            portfolio_query = db.collection('portfolios').where('user_id', '==', user_id).get()
            portfolio_items = list(portfolio_query)
            portfolio_data = []
            total_value = 0

            print(f"📈 Found {len(portfolio_items)} portfolio items")

            for position in portfolio_items:
                try:
                    position_data = position.to_dict()
                    print(f"🔍 Processing portfolio entry: {position_data}")
                    
                    # Make sure these fields exist - otherwise use defaults
                    symbol = position_data.get('symbol', '')
                    if not symbol:
                        print(f"⚠️ Skipping portfolio entry without symbol: {position_data}")
                        continue
                        
                    shares = position_data.get('shares', 0)
                    purchase_price = position_data.get('purchase_price', 0)
                    
                    # Fetch current price
                    print(f"💰 Fetching current price for {symbol}")
                    try:
                        price_data = fetch_stock_data(symbol)
                        latest_price = price_data.get('close', purchase_price) if price_data else purchase_price
                    except Exception as price_error:
                        print(f"⚠️ Error fetching price for {symbol}: {str(price_error)}")
                        latest_price = purchase_price
                    
                    asset_value = round(shares * latest_price, 2)
                    profit_loss = calculate_profit_loss(latest_price, purchase_price)

                    portfolio_item = {
                        'symbol': symbol,
                        'shares': shares,
                        'purchase_price': purchase_price,
                        'latest_price': latest_price,
                        'value': asset_value,
                        'profit_loss': profit_loss
                    }
                    
                    print(f"✅ Processed portfolio item: {portfolio_item}")
                    portfolio_data.append(portfolio_item)
                    total_value += asset_value
                except Exception as entry_error:
                    print(f"⚠️ Error processing portfolio entry: {str(entry_error)}")
                    print(f"Entry data: {position_data if 'position_data' in locals() else 'Unknown'}")
                    traceback.print_exc(file=sys.stdout)
                    # Continue with other entries
                    continue
        except Exception as portfolio_error:
            print(f"🔴 ERROR fetching portfolio data: {str(portfolio_error)}")
            traceback.print_exc(file=sys.stdout)
            portfolio_data = []
            total_value = 0

        # Fetch badges
        try:
            # Directly import the function from badge_services
            from services.badge_services import fetch_user_badges as get_badges
            user_badges = get_badges(user_id)
            print(f"🏆 Successfully fetched {len(user_badges)} badges for user {user_id}")
        except Exception as e:
            print(f"⚠️ Error fetching badges: {e}")
            traceback.print_exc(file=sys.stdout)
            user_badges = []

        profile_picture = user.to_dict().get('profile_picture', url_for('static', filename='default-profile.png'))
        is_developer = user.to_dict().get('username') == 'xiao'

        print(f"🟢 Successfully prepared portfolio view for user {user_id}")
        print(f"Portfolio data: {portfolio_data}")
        print(f"Total value: ${total_value:.2f}")
        
        return render_template('portfolio.html.jinja2', 
                           user=user.to_dict(), 
                           profile_picture=profile_picture, 
                           portfolio=portfolio_data, 
                           total_value=round(total_value, 2), 
                           badges=user_badges, 
                           is_developer=is_developer)

    except Exception as e:
        print(f"🔴 ERROR in view_portfolio: {e}")
        traceback.print_exc(file=sys.stdout)
        return render_template('error.html.jinja2', 
                              error_message="An error occurred loading your portfolio",
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
