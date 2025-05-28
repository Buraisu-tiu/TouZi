# src/routes/trading.py
"""
Trading module for handling buy and sell operations.
Completely reworked for reliability.
"""

# CRITICAL IMPORTS
from datetime import datetime
from functools import wraps
import time
import traceback

# Flask imports
from flask import Blueprint, render_template, request, redirect
from flask import url_for, flash, session, jsonify

# Firebase imports
from google.cloud import firestore

# Local imports
from services.market_data import fetch_stock_data, fetch_user_portfolio
from utils.db import db
from routes.watchlist import fetch_watchlist

print("\n\n!!!!!!!!!! --- LOADING trading.py - COMPLETE REWORK --- !!!!!!!!!!\n\n")

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

def fetch_recent_orders(user_id, limit=10):
    """Fetch recent orders for a user."""
    try:
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
        return orders
    except Exception as e:
        print(f"Error fetching recent orders: {e}")
        return []

@trading_bp.route('/buy', methods=['GET', 'POST'])
@login_required
def buy():
    print(f"[TRADING] /buy route accessed. Method: {request.method}")
    user_id = session['user_id']
    
    if request.method == 'POST':
        symbol = request.form.get('symbol', '').strip().upper()
        try:
            quantity = float(request.form.get('quantity', 0))
        except ValueError:
            flash('Invalid quantity.', 'error')
            return redirect(url_for('trading.buy'))
            
        if not symbol or quantity <= 0:
            flash('Please provide a valid symbol and quantity.', 'error')
            return redirect(url_for('trading.buy'))
            
        # Fetch stock price
        try:
            price_data = fetch_stock_data(symbol)
            if not price_data or 'close' not in price_data or price_data['close'] <= 0:
                flash(f"Unable to fetch valid price for {symbol}", 'error')
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
            return redirect(url_for('trading.buy', symbol=symbol))
            
        # Execute transaction
        try:
            # 1. Update user balance
            new_balance = balance - final_cost
            user_ref.update({'balance': new_balance})
            
            # 2. Update portfolio
            portfolio_ref = db.collection('portfolios').document(f"{user_id}_{symbol}")
            portfolio_doc = portfolio_ref.get()
            
            if portfolio_doc.exists:
                existing_data = portfolio_doc.to_dict()
                existing_shares = float(existing_data.get('shares', 0))
                new_shares = existing_shares + quantity
                portfolio_ref.update({'shares': new_shares})
            else:
                portfolio_ref.set({
                    'user_id': user_id,
                    'symbol': symbol,
                    'shares': quantity,
                    'purchase_price': current_price,
                    'purchase_date': datetime.now()
                })
            
            # 3. Record transaction
            db.collection('transactions').add({
                'user_id': user_id,
                'symbol': symbol,
                'shares': quantity,
                'price': current_price,
                'total_amount': final_cost,
                'trading_fee': trading_fee,
                'transaction_type': 'BUY',
                'timestamp': datetime.now(),
                'status': 'COMPLETED'
            })
            
            flash(f"Successfully bought {quantity} shares of {symbol} for ${final_cost:.2f}", 'success')
            return redirect(url_for('trading.buy'))
            
        except Exception as e:
            flash(f"Error processing purchase: {str(e)}", 'error')
            return redirect(url_for('trading.buy'))
    
    # GET request - show buy form
    try:
        user = db.collection('users').document(user_id).get().to_dict()
        recent_orders = fetch_recent_orders(user_id, limit=5)
        watchlist_items = fetch_watchlist(user_id)
        
        response = render_template(
            'buy.html.jinja2',
            user=user,
            watchlist_items=watchlist_items,
            recent_orders=recent_orders,
            symbol=request.args.get('symbol', '')
        )
        return response
    except Exception as e:
        print(f"Error loading buy page: {e}")
        flash(f"Error loading the buy page: {str(e)}", 'error')
        return render_template('error.html.jinja2', 
                          error_message=f"Failed to load data: {str(e)}",
                          return_url=url_for('trading.buy'))

@trading_bp.route('/sell', methods=['GET', 'POST'])
@login_required
def sell():
    """Handle selling stocks with complete debugging."""
    print("\n" + "="*60)
    print("🔥 SELL ROUTE - ENHANCED DEBUG VERSION")
    print("="*60)
    
    user_id = session['user_id']
    print(f"[SELL] User ID: {user_id}")
    print(f"[SELL] Request Method: {request.method}")
    print(f"[SELL] Request URL: {request.url}")
    print(f"[SELL] Request Form: {dict(request.form)}")
    print(f"[SELL] Request Args: {dict(request.args)}")
    
    if request.method == 'POST':
        print("\n🚨 POST REQUEST DETECTED - PROCESSING SELL ORDER")
        
        # Extract form data with detailed logging
        symbol = request.form.get('symbol', '').strip().upper()
        shares_input = request.form.get('shares', '0').strip()
        
        print(f"[SELL-POST] Raw form data:")
        print(f"  - symbol: '{symbol}'")
        print(f"  - shares: '{shares_input}'")
        
        # Validate inputs
        if not symbol:
            print("[SELL-POST] ❌ No symbol provided")
            flash('Please select a stock to sell', 'error')
            return redirect(url_for('trading.sell'))
            
        try:
            shares_to_sell = float(shares_input)
            if shares_to_sell <= 0:
                print(f"[SELL-POST] ❌ Invalid shares amount: {shares_to_sell}")
                flash('Please enter a valid number of shares', 'error')
                return redirect(url_for('trading.sell'))
        except ValueError:
            print(f"[SELL-POST] ❌ Could not convert shares to float: {shares_input}")
            flash('Invalid share quantity entered', 'error')
            return redirect(url_for('trading.sell'))
        
        print(f"[SELL-POST] ✅ Validation passed - selling {shares_to_sell} shares of {symbol}")
        
        # Get current stock price
        try:
            price_data = fetch_stock_data(symbol)
            current_price = price_data['close']
            print(f"[SELL-POST] ✅ Current price: ${current_price}")
        except Exception as e:
            print(f"[SELL-POST] ❌ Price fetch error: {e}")
            flash('Unable to get current stock price', 'error')
            return redirect(url_for('trading.sell'))
        
        # Calculate sale proceeds
        gross_proceeds = shares_to_sell * current_price
        transaction_fee = gross_proceeds * TRANSACTION_FEE_RATE
        net_proceeds = gross_proceeds - transaction_fee
        
        print(f"[SELL-POST] 💰 Sale calculation:")
        print(f"  - Gross proceeds: ${gross_proceeds:.2f}")
        print(f"  - Transaction fee: ${transaction_fee:.2f}")
        print(f"  - Net proceeds: ${net_proceeds:.2f}")
        
        # Execute the sale
        try:
            print("[SELL-POST] 🔄 Starting database operations...")
            
            # Step 1: Update user balance
            user_ref = db.collection('users').document(user_id)
            user_doc = user_ref.get()
            current_balance = user_doc.to_dict().get('balance', 0)
            new_balance = current_balance + net_proceeds
            
            print(f"[SELL-POST] 💳 Balance update: ${current_balance:.2f} → ${new_balance:.2f}")
            user_ref.update({'balance': new_balance})
            print("[SELL-POST] ✅ User balance updated")
            
            # Step 2: Update portfolio position
            portfolio_ref = db.collection('portfolios').document(f"{user_id}_{symbol}")
            portfolio_doc = portfolio_ref.get()
            
            if portfolio_doc.exists:
                current_shares = float(portfolio_doc.to_dict().get('shares', 0))
                remaining_shares = current_shares - shares_to_sell
                
                print(f"[SELL-POST] 📊 Portfolio update: {current_shares} → {remaining_shares} shares")
                
                if remaining_shares > 0:
                    portfolio_ref.update({'shares': remaining_shares})
                    print("[SELL-POST] ✅ Portfolio position updated")
                else:
                    portfolio_ref.delete()
                    print("[SELL-POST] ✅ Portfolio position deleted (no remaining shares)")
            else:
                print("[SELL-POST] ⚠️ No portfolio position found - allowing sale anyway")
            
            # Step 3: Record transaction
            transaction_data = {
                'user_id': user_id,
                'symbol': symbol,
                'shares': shares_to_sell,
                'price': current_price,
                'gross_proceeds': gross_proceeds,
                'transaction_fee': transaction_fee,
                'net_proceeds': net_proceeds,
                'transaction_type': 'SELL',
                'timestamp': datetime.now(),
                'status': 'COMPLETED'
            }
            
            db.collection('transactions').add(transaction_data)
            print("[SELL-POST] ✅ Transaction recorded")
            
            # Success!
            print("[SELL-POST] 🎉 SALE COMPLETED SUCCESSFULLY!")
            flash(f'Successfully sold {shares_to_sell} shares of {symbol} for ${net_proceeds:.2f}', 'success')
            return redirect(url_for('portfolio.portfolio'))
            
        except Exception as e:
            print(f"[SELL-POST] ❌ CRITICAL ERROR during sale: {e}")
            import traceback
            print(traceback.format_exc())
            flash('An error occurred while processing your sale. Please try again.', 'error')
            return redirect(url_for('trading.sell'))
    
    # GET request - show sell form
    try:
        print("[SELL-GET] 📋 Loading sell form")
        
        user = db.collection('users').document(user_id).get().to_dict()
        positions = []
        total_value = 0
        
        # Get all portfolio positions
        portfolio_docs = db.collection('portfolios').where('user_id', '==', user_id).stream()
        
        for doc in portfolio_docs:
            position_data = doc.to_dict()
            symbol = position_data.get('symbol')
            shares = float(position_data.get('shares', 0))
            
            if shares > 0:
                try:
                    price_data = fetch_stock_data(symbol)
                    current_price = price_data.get('close', 0)
                    position_value = shares * current_price
                    total_value += position_value
                    
                    positions.append({
                        'symbol': symbol,
                        'shares': shares,
                        'current_price': current_price,
                        'value': position_value
                    })
                    print(f"[SELL-GET] 📊 Position: {symbol} - {shares} shares @ ${current_price}")
                except Exception as e:
                    print(f"[SELL-GET] ⚠️ Error loading position {symbol}: {e}")
        
        print(f"[SELL-GET] 📋 Loaded {len(positions)} positions, total value: ${total_value:.2f}")
        
        return render_template('sell.html.jinja2',
                          user=user,
                          positions=sorted(positions, key=lambda x: x['value'], reverse=True),
                          portfolio_summary={'total_value': total_value})
                          
    except Exception as e:
        print(f"[SELL-GET] ❌ Error loading sell form: {e}")
        import traceback
        print(traceback.format_exc())
        flash('Error loading your portfolio positions', 'error')
        return redirect(url_for('portfolio.portfolio'))

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
            return jsonify({'error': 'Unable to fetch stock price'})
        
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