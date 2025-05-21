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

# Buy route - IMPORTANT: Function name must match the route name in the Flask template
@trading_bp.route('/buy', methods=['GET', 'POST'])
@login_required
def buy():
    print(f"[TRADING] /buy route accessed. Method: {request.method}")
    user_id = session['user_id']
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

# Completely redesigned sell route
@trading_bp.route('/sell', methods=['GET', 'POST'])
@login_required
def sell():
    """Handle selling stocks with improved reliability and error handling."""
    print("\n" + "="*80)
    print("🔄 SELL ROUTE - COMPLETELY REDESIGNED")
    print("="*80)
    
    # Extract user ID from session
    user_id = session['user_id']
    request_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"📊 Request Time: {request_timestamp}")
    print(f"👤 User ID: {user_id}")
    
    # ===== GET request - Display sell form =====
    if request.method == 'GET':
        try:
            # Get user details for displaying balance
            user_ref = db.collection('users').document(user_id)
            user = user_ref.get().to_dict()
            
            # Fetch portfolio data directly from Firestore
            portfolio_query = db.collection('portfolios').where('user_id', '==', user_id).stream()
            positions = []
            
            print(f"🔍 Fetching portfolio positions directly from Firestore")
            for doc in portfolio_query:
                data = doc.to_dict()
                symbol = data.get('symbol', '')
                shares = float(data.get('shares', 0))
                
                if shares <= 0:
                    print(f"⚠️ Skipping {symbol}: zero or negative shares ({shares})")
                    continue
                    
                # Get current market price
                try:
                    price_data = fetch_stock_data(symbol)
                    current_price = price_data.get('close', 0) if price_data else 0
                except Exception as e:
                    print(f"⚠️ Error fetching price for {symbol}: {str(e)}")
                    current_price = 0
                
                position = {
                    'symbol': symbol,
                    'shares': shares,
                    'purchase_price': data.get('purchase_price', 0),
                    'current_price': current_price,
                    'value': shares * current_price,
                    'document_id': doc.id
                }
                positions.append(position)
                print(f"✅ Added position: {symbol} - {shares} shares")
            
            # Calculate portfolio summary
            total_value = sum(p.get('value', 0) for p in positions)
            portfolio_summary = {
                'positions_count': len(positions),
                'total_value': total_value
            }
            
            print(f"📊 Rendering sell template with {len(positions)} positions")
            return render_template('sell.html.jinja2',
                                user=user,
                                positions=positions,
                                user_portfolio=portfolio_summary)
                                
        except Exception as e:
            print(f"❌ Error loading sell form: {str(e)}")
            traceback.print_exc()
            flash("Unable to load your portfolio. Please try again.", "error")
            return redirect(url_for('dashboard.dashboard'))
    
    # ===== POST request - Process sell order =====
    elif request.method == 'POST':
        print("\n🔴 Processing SELL POST request")
        print(f"📦 Form data: {request.form}")
        
        # Extract sell parameters from form
        symbol = request.form.get('symbol', '').strip().upper()
        shares_str = request.form.get('shares', '').strip()
        
        print(f"📉 Selling - Symbol: {symbol} | Shares: {shares_str}")
        
        # Validate inputs
        if not symbol:
            flash("Please select a stock to sell", "error")
            return redirect(url_for('trading.sell'))
        
        try:
            shares = float(shares_str)
            if shares <= 0:
                flash("Please enter a positive number of shares", "error")
                return redirect(url_for('trading.sell'))
        except ValueError:
            flash("Please enter a valid number of shares", "error")
            return redirect(url_for('trading.sell'))
        
        # Start the sell process
        sale_id = f"SALE_{user_id}_{int(time.time())}"
        print(f"🆔 Sale ID: {sale_id}")
        
        # Create an atomic transaction
        transaction = db.transaction()
        
        @firestore.transactional
        def sell_stock_transaction(transaction, user_id, symbol, shares, sale_id):
            """Execute stock sale as a single atomic transaction"""
            print(f"🔄 Starting transaction for {sale_id}")
            
            # 1. Check position exists and has enough shares
            portfolio_ref = db.collection('portfolios').document(f"{user_id}_{symbol}")
            portfolio_doc = portfolio_ref.get(transaction=transaction)
            
            if not portfolio_doc.exists:
                raise ValueError(f"You don't own any shares of {symbol}")
            
            portfolio_data = portfolio_doc.to_dict()
            current_shares = float(portfolio_data.get('shares', 0))
            
            if current_shares < shares:
                raise ValueError(f"You only have {current_shares} shares of {symbol}")
            
            # 2. Get current market price
            price_data = fetch_stock_data(symbol)
            if not price_data or 'close' not in price_data or price_data['close'] <= 0:
                raise ValueError(f"Unable to get current price for {symbol}")
            
            current_price = float(price_data['close'])
            print(f"💲 Current price: ${current_price:.2f}")
            
            # 3. Calculate sale values
            sale_value = current_price * shares
            fee = sale_value * TRANSACTION_FEE_RATE
            net_proceeds = sale_value - fee
            
            print(f"💰 Sale value: ${sale_value:.2f}")
            print(f"📊 Fee: ${fee:.2f}")
            print(f"💵 Net proceeds: ${net_proceeds:.2f}")
            
            # 4. Update user balance
            user_ref = db.collection('users').document(user_id)
            user_doc = user_ref.get(transaction=transaction)
            
            if not user_doc.exists:
                raise ValueError("User account not found")
            
            current_balance = float(user_doc.get('balance', 0))
            new_balance = current_balance + net_proceeds
            
            print(f"💵 Updating balance: ${current_balance:.2f} → ${new_balance:.2f}")
            transaction.update(user_ref, {'balance': new_balance})
            
            # 5. Update or delete portfolio position
            remaining_shares = current_shares - shares
            if remaining_shares > 0.0001:  # Account for floating point precision
                print(f"📝 Updating position: {current_shares} → {remaining_shares} shares")
                transaction.update(portfolio_ref, {
                    'shares': remaining_shares,
                    'last_updated': firestore.SERVER_TIMESTAMP
                })
            else:
                print(f"🗑️ Deleting position: All shares sold")
                transaction.delete(portfolio_ref)
            
            # 6. Record transaction
            transaction_ref = db.collection('transactions').document(sale_id)
            transaction_data = {
                'transaction_id': sale_id,
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
            }
            
            print(f"📝 Recording transaction: {sale_id}")
            transaction.set(transaction_ref, transaction_data)
            
            return {
                'success': True,
                'sale_id': sale_id,
                'symbol': symbol,
                'shares': shares,
                'price': current_price,
                'total': net_proceeds,
                'balance': new_balance
            }
        
        # Execute the transaction with exception handling
        try:
            result = sell_stock_transaction(transaction, user_id, symbol, shares, sale_id)
            print(f"✅ Transaction successful: {result}")
            flash(f"Successfully sold {shares} shares of {symbol} for ${result['total']:.2f}", "success")
            return redirect(url_for('portfolio.portfolio'))
            
        except ValueError as ve:
            print(f"⚠️ Validation error: {str(ve)}")
            flash(str(ve), "error")
            return redirect(url_for('trading.sell'))
            
        except Exception as e:
            print(f"❌ Transaction failed: {str(e)}")
            traceback.print_exc()
            flash(f"Sale failed: {str(e)}", "error")
            return redirect(url_for('trading.sell'))
    
    # Invalid request method
    return redirect(url_for('trading.sell'))

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