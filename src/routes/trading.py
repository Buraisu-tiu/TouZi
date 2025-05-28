# src/routes/trading.py
"""
Trading module for handling buy and sell operations.
Simplified version to resolve imports and basic functionality.
"""

# CRITICAL IMPORTS - Do not remove!
import time
import traceback
from datetime import datetime
from functools import wraps

# Flask imports
from flask import Blueprint, render_template, request, redirect
from flask import url_for, flash, session, jsonify

# Firebase imports
from google.cloud import firestore
from google.cloud.firestore import Query

# Local imports
from services.market_data import fetch_stock_data, fetch_user_portfolio
from utils.db import db
from routes.watchlist import fetch_watchlist

print("\n\n!!!!!!!!!! --- LOADING trading.py - FINAL_FIX_MAY_19 --- !!!!!!!!!!\n\n")
print(f"[DEBUG] time module imported successfully: {time.__name__}")

# Create the blueprint
trading_bp = Blueprint('trading', __name__)

# Transaction fee rate
TRANSACTION_FEE_RATE = 0.001  # 0.1% fee

# Login decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('You need to be logged in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# Fix the missing fetch_recent_orders function
def fetch_recent_orders(user_id, limit=10):
    """Fetch recent orders for a user."""
    try:
        # Try transactions first
        transactions_query = db.collection('transactions').where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
        transactions_docs = transactions_query.stream()
        
        orders = []
        for doc in transactions_docs:
            data = doc.to_dict()
            orders.append({
                'Date': data.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M') if isinstance(data.get('timestamp'), datetime) else 'N/A',
                'Symbol': data.get('symbol', 'N/A'),
                'Type': data.get('transaction_type', 'UNKNOWN').upper(),
                'Quantity': data.get('shares', 0),
                'Status': data.get('status', 'Unknown').capitalize()
            })
        
        # If no transactions, try orders collection
        if not orders:
            orders_query = db.collection('orders').where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit)
            orders_docs = orders_query.stream()
            
            for doc in orders_docs:
                data = doc.to_dict()
                orders.append({
                    'Date': data.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M') if isinstance(data.get('timestamp'), datetime) else 'N/A',
                    'Symbol': data.get('symbol', 'N/A'),
                    'Type': data.get('type', 'UNKNOWN').upper(),
                    'Quantity': data.get('quantity', 0),
                    'Status': data.get('status', 'Unknown').capitalize()
                })
                
        return orders
    except Exception as e:
        print(f"Error fetching recent orders: {e}")
        return []

# Buy route - IMPORTANT: Function name must match the route name in the Flask template
@trading_bp.route('/buy', methods=['GET', 'POST'])
@login_required
def buy():
    user_id = session['user_id']
    
    try:
        # Get recent orders with proper index and error handling
        recent_orders_query = (
            db.collection('orders')
            .where('user_id', '==', user_id)
            .order_by('timestamp', direction=Query.DESCENDING)
            .limit(5)
        )
        
        try:
            recent_orders = [doc.to_dict() for doc in recent_orders_query.stream()]
        except Exception as e:
            print(f"Error fetching recent orders: {e}")
            recent_orders = []  # Fallback to empty list
            
        # Get watchlist with proper error handling
        try:
            watchlist_ref = db.collection('watchlists').document(user_id)
            watchlist_doc = watchlist_ref.get()
            watchlist_items = []
            
            if watchlist_doc.exists:
                watchlist_data = watchlist_doc.to_dict()
                symbols = watchlist_data.get('symbols', [])
                
                for symbol in symbols:
                    try:
                        # Use cached data first
                        cache_key = f"price_{symbol}"
                        cached_data = app.cache.get(cache_key) if hasattr(app, 'cache') else None
                        
                        if cached_data:
                            price_data = cached_data
                        else:
                            price_data = fetch_stock_data(symbol)
                            if hasattr(app, 'cache'):
                                app.cache.set(cache_key, price_data, timeout=300)  # Cache for 5 minutes
                        
                        if price_data and 'close' in price_data:
                            watchlist_items.append({
                                'symbol': symbol,
                                'current_price': price_data['close'],
                                'price_change': price_data['close'] - price_data['prev_close'],
                                'change_percentage': ((price_data['close'] - price_data['prev_close']) / price_data['prev_close'] * 100)
                            })
                    except Exception as e:
                        print(f"Error processing watchlist item {symbol}: {e}")
                        continue
                        
        except Exception as e:
            print(f"Error fetching watchlist: {e}")
            watchlist_items = []

        return render_template('buy.html.jinja2',
                            user=g.user,
                            watchlist_items=watchlist_items,
                            recent_orders=recent_orders)
                            
    except Exception as e:
        print(f"Error in buy route: {e}")
        traceback.print_exc()
        flash("An error occurred. Please try again.", "error")
        return redirect(url_for('portfolio.view_portfolio_route'))

# Sell route - Extra debugging for form submission
@trading_bp.route('/sell', methods=['GET', 'POST'])
@login_required
def sell():
    """Handle selling stocks with direct database operations."""
    print("\n" + "="*80)
    print("🚨 SELL ROUTE - FORM FIX")
    print("="*80)
    
    user_id = session['user_id']
    print(f"User ID: {user_id}")
    print(f"Request Method: {request.method}")
    
    # Process sell request
    if request.method == 'POST':
        print("\nPOST REQUEST DETECTED!")
        print(f"Form data: {request.form}")
        print(f"Raw POST data: {request.get_data()}")
        
        # Get form data with extra validation
        symbol = request.form.get('symbol', '').strip().upper()
        shares_str = request.form.get('shares', '0').strip()
        print(f"Symbol: '{symbol}', Shares: '{shares_str}'")
        
        if not symbol:
            flash("No stock symbol provided", "error")
            return redirect(url_for('trading.sell'))
            
        try:
            shares = float(shares_str)
            if shares <= 0:
                flash("Please enter a positive number of shares", "error")
                return redirect(url_for('trading.sell'))
        except ValueError:
            flash("Invalid number of shares", "error")
            return redirect(url_for('trading.sell'))
        
        print(f"Processing sale: {shares} shares of {symbol}")
        
        # Check portfolio position
        portfolio_ref = db.collection('portfolios').document(f"{user_id}_{symbol}")
        portfolio_doc = portfolio_ref.get()
        
        if not portfolio_doc.exists:
            flash(f"You don't own any shares of {symbol}", "error")
            return redirect(url_for('trading.sell'))
        
        portfolio_data = portfolio_doc.to_dict()
        current_shares = float(portfolio_data.get('shares', 0))
        print(f"Current position: {current_shares} shares")
        
        if current_shares < shares:
            flash(f"You only have {current_shares} shares of {symbol}", "error")
            return redirect(url_for('trading.sell'))
        
        # Get current price
        try:
            price_data = fetch_stock_data(symbol)
            current_price = float(price_data.get('close', 0))
            print(f"Current price: ${current_price:.2f}")
        except Exception as e:
            flash(f"Error fetching price: {str(e)}", "error")
            return redirect(url_for('trading.sell'))
        
        # Calculate values
        sale_value = current_price * shares
        fee = sale_value * TRANSACTION_FEE_RATE
        net_proceeds = sale_value - fee
        print(f"Sale value: ${sale_value:.2f}")
        print(f"Fee: ${fee:.2f}")
        print(f"Net proceeds: ${net_proceeds:.2f}")
        
        # Update user balance
        try:
            user_ref = db.collection('users').document(user_id)
            user_doc = user_ref.get()
            current_balance = float(user_doc.get('balance', 0))
            new_balance = current_balance + net_proceeds
            
            print(f"Updating balance: ${current_balance:.2f} -> ${new_balance:.2f}")
            user_ref.update({'balance': new_balance})
            print("✅ User balance updated")
        except Exception as e:
            print(f"❌ Error updating balance: {str(e)}")
            flash(f"Error updating balance: {str(e)}", "error")
            return redirect(url_for('trading.sell'))
        
        # Update portfolio position
        try:
            remaining_shares = current_shares - shares
            print(f"Remaining shares: {remaining_shares}")
            
            if remaining_shares <= 0.01:
                print(f"🗑️ Deleting position: {portfolio_ref.id}")
                portfolio_ref.delete()
                print("✅ Position deleted")
            else:
                print(f"📝 Updating position to {remaining_shares} shares")
                portfolio_ref.update({
                    'shares': remaining_shares,
                    'last_updated': firestore.SERVER_TIMESTAMP
                })
                print("✅ Position updated")
        except Exception as e:
            print(f"❌ Error updating portfolio: {str(e)}")
            # Try to restore balance
            user_ref.update({'balance': current_balance})
            flash(f"Error updating portfolio: {str(e)}", "error")
            return redirect(url_for('trading.sell'))
        
        # Record transaction
        transaction_id = f"SELL_{user_id}_{int(time.time())}"
        try:
            print(f"📝 Recording transaction: {transaction_id}")
            db.collection('transactions').document(transaction_id).set({
                'transaction_id': transaction_id,
                'user_id': user_id,
                'symbol': symbol,
                'shares': shares,
                'price': current_price,
                'total_value': sale_value,
                'fee': fee,
                'net_proceeds': net_proceeds,
                'transaction_type': 'SELL',
                'timestamp': firestore.SERVER_TIMESTAMP,
                'status': 'completed'
            })
            print("✅ Transaction recorded")
        except Exception as e:
            print(f"⚠️ Error recording transaction: {str(e)} (non-critical)")
        
        print("\n✅✅✅ SELL COMPLETED SUCCESSFULLY")
        flash(f"Successfully sold {shares} shares of {symbol} for ${net_proceeds:.2f}", "success")
        return redirect(url_for('portfolio.portfolio'))
    
    # GET request - Display sell form
    try:
        # Get user data
        user_ref = db.collection('users').document(user_id)
        user = user_ref.get().to_dict()
        
        # Get portfolio data
        print("\nFetching portfolio positions")
        positions = []
        portfolio_docs = db.collection('portfolios').where('user_id', '==', user_id).stream()
        
        for doc in portfolio_docs:
            data = doc.to_dict()
            symbol = data.get('symbol')
            shares = float(data.get('shares', 0))
            
            if not symbol or shares <= 0:
                continue
                
            try:
                price_data = fetch_stock_data(symbol)
                current_price = price_data.get('close', 0) if price_data else 0
            except Exception as e:
                print(f"Error fetching price for {symbol}: {e}")
                current_price = 0
                
            position = {
                'symbol': symbol,
                'shares': shares,
                'current_price': current_price,
                'value': shares * current_price,
            }
            
            positions.append(position)
            print(f"Found position: {symbol} - {shares} shares @ ${current_price}")
        
        total_value = sum(p.get('value', 0) for p in positions)
        portfolio_summary = {
            'total_value': total_value
        }
        
        print(f"Rendering sell form with {len(positions)} positions")
        return render_template('sell.html.jinja2',
                            user=user,
                            positions=positions,
                            user_portfolio=portfolio_summary)
    
    except Exception as e:
        print(f"Error loading sell form: {e}")
        traceback.print_exc()
        flash(f"Error loading portfolio: {str(e)}", "error")
        # Fix the URL building error by redirecting to a known valid URL
        return redirect('/')  # Redirect to home page as fallback

# API endpoint for order summary
@trading_bp.route('/api/order_summary', methods=['POST'])
def api_order_summary():
    """Calculate order summary with estimated costs."""
    data = request.json
    symbol = data.get('symbol')
    quantity = float(data.get('quantity', 0))
    
    if not symbol or quantity <= 0:
        return jsonify({'error': 'Invalid input'})
    
    try:
        price_data = fetch_stock_data(symbol)
        if not price_data or 'error' in price_data or price_data.get('close') is None or price_data.get('close') <= 0:
            return jsonify({'error': price_data.get('error', 'Unable to fetch stock price')})
        
        price = price_data['close']
        estimated_cost = price * quantity
        trading_fee = estimated_cost * TRANSACTION_FEE_RATE
        total = estimated_cost + trading_fee
        
        return jsonify({
            'success': True,
            'estimated_price': f"${estimated_cost:.2f}",
            'trading_fee': f"${trading_fee:.2f}",
            'total': f"${total:.2f}"
        })
    except Exception as e:
        print(f"Error in order summary: {e}")
        return jsonify({'error': str(e)})