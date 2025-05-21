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
    print(f"[TRADING] /buy route accessed. Method: {request.method}")
    user_id = session['user_id']
    timestamp = int(time.time())  # Define timestamp for transaction ID
    user_ref = db.collection('users').document(user_id)
    user_data = user_ref.get().to_dict()
    
    # Fetch watchlist items
    watchlist_items = fetch_watchlist(user_id) # Fetch watchlist data here
    
    # Fetch recent orders (assuming this logic is correct)
    recent_orders_query = db.collection('orders').where('user_id', '==', user_id).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(10)
    recent_orders_docs = recent_orders_query.stream()
    recent_orders = []
    for order_doc in recent_orders_docs:
        order_data = order_doc.to_dict()
        recent_orders.append({
            'Date': order_data.get('timestamp', 'N/A').strftime('%Y-%m-%d %H:%M') if isinstance(order_data.get('timestamp'), datetime) else 'N/A',
            'Symbol': order_data.get('symbol', 'N/A'),
            'Type': order_data.get('type', 'N/A').upper(),
            'Quantity': order_data.get('quantity', 0),
            'Status': order_data.get('status', 'N/A').capitalize()
        })

    if request.method == 'POST':
        # Extract form data
        symbol = request.form.get('symbol', '').strip().upper()
        try:
            quantity = float(request.form.get('quantity', 0))
        except ValueError:
            flash('Invalid quantity.', 'error')
            return redirect(url_for('trading.buy'))  # Changed from buy_stock to buy
            
        if not symbol or quantity <= 0:
            flash('Please provide a valid symbol and quantity.', 'error')
            return redirect(url_for('trading.buy'))  # Changed from buy_stock to buy
            
        # Fetch stock price
        try:
            price_data = fetch_stock_data(symbol)
            if not price_data or 'close' not in price_data or price_data['close'] <= 0:
                flash(f"Could not fetch price for {symbol}", 'error')
                return redirect(url_for('trading.buy', symbol=symbol))
                
            current_price = price_data['close']
        except Exception as e:
            flash(f"Error fetching price: {str(e)}", 'error')
            return redirect(url_for('trading.buy', symbol=symbol))
        
        # Calculate costs
        total_cost = quantity * current_price
        trading_fee = total_cost * TRANSACTION_FEE_RATE
        final_cost = total_cost + trading_fee
        
        # Check user balance
        user_ref = db.collection('users').document(user_id)
        user_data = user_ref.get().to_dict()
        balance = user_data.get('balance', 0)
        
        if balance < final_cost:
            flash(f"Insufficient funds. Need ${final_cost:.2f}, have ${balance:.2f}", 'error')
            return redirect(url_for('trading.buy', symbol=symbol))  # Changed from buy_stock to buy
            
        # Execute transaction
        try:
            # 1. Update user balance
            new_balance = balance - final_cost
            user_ref.update({'balance': new_balance})
            
            # 2. Update portfolio
            portfolio_ref = db.collection('portfolios').document(f"{user_id}_{symbol}")
            portfolio_doc = portfolio_ref.get()
            
            if portfolio_doc.exists:
                # Update existing position
                portfolio_data = portfolio_doc.to_dict()
                old_shares = portfolio_data.get('shares', 0)
                old_price = portfolio_data.get('purchase_price', 0)
                new_shares = old_shares + quantity
                
                # Calculate weighted average purchase price
                new_price = ((old_shares * old_price) + (quantity * current_price)) / new_shares
                
                portfolio_ref.update({
                    'shares': new_shares,
                    'purchase_price': new_price,
                    'latest_price': current_price,
                    'last_updated': firestore.SERVER_TIMESTAMP
                })
            else:
                # Create new position
                portfolio_ref.set({
                    'user_id': user_id,
                    'symbol': symbol,
                    'shares': quantity,
                    'purchase_price': current_price,
                    'latest_price': current_price,
                    'last_updated': firestore.SERVER_TIMESTAMP
                })
            
            # 3. Record transaction
            db.collection('transactions').add({
                'transaction_id': f"{user_id}_{timestamp}",
                'user_id': user_id,
                'symbol': symbol,
                'shares': quantity,
                'price': current_price,
                'total_amount': final_cost,
                'trading_fee': trading_fee,
                'transaction_type': 'BUY',
                'timestamp': firestore.SERVER_TIMESTAMP,
                'status': 'completed'
            })
            
            flash(f"Successfully bought {quantity} shares of {symbol} for ${final_cost:.2f}", 'success')
            return redirect(url_for('trading.buy'))  # This is correct - should redirect to buy page
            
        except Exception as e:
            # Attempt to restore balance if it was already deducted
            try:
                user_ref.update({'balance': balance})
            except:
                pass
                
            flash(f"Transaction failed: {str(e)}", 'error')
            return redirect(url_for('trading.buy', symbol=symbol))  # Changed from buy_stock to buy
    
    # GET request - show buy form
    try:
        print(f"[DEBUG] Executing GET request handler for buy page")
        user = db.collection('users').document(user_id).get().to_dict()
        recent_orders = fetch_recent_orders(user_id, limit=5)
        watchlist_items = fetch_watchlist(user_id)
        
        # CRITICAL: Force direct template rendering without redirection
        print(f"[DEBUG] About to render buy.html.jinja2 template directly")
        response = render_template(
            'buy.html.jinja2',  # Use the actual file name, not 'trading.buy'
            user=user,
            watchlist_items=watchlist_items,
            recent_orders=recent_orders,
            symbol=request.args.get('symbol', '')
        )
        print(f"[DEBUG] Template rendered successfully, returning response")
        return response
    except Exception as e:
        print(f"[DEBUG] Error loading buy page: {e}")
        traceback.print_exc()
        flash(f"Error loading the buy page: {str(e)}", 'error')
        error_message = f"Failed to load data: {str(e)}"
        # Use the direct endpoint name
        return render_template('error.html.jinja2', 
                          error_message=error_message,
                          error_details=traceback.format_exc(),
                          return_url=url_for('trading.buy'))

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