# src/routes/trading.py
from flask import Blueprint, request, session, redirect, url_for, render_template, flash, current_app
from utils.db import db
from services.market_data import fetch_stock_data, fetch_crypto_data, fetch_user_portfolio, fetch_recent_orders
from services.badge_services import check_and_award_badges
from routes.watchlist import fetch_watchlist
from datetime import datetime
import requests
import traceback
import sys
import json
import time
from google.cloud import firestore
from functools import wraps

trading_bp = Blueprint('trading', __name__)

# Add a retry decorator for API operations
def retry_operation(max_attempts=3, delay=1):
    """Retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            last_exception = None
            request_id = kwargs.get('request_id', 'UNKNOWN')

            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    last_exception = e
                    wait_time = delay * (2 ** (attempts - 1))  # Exponential backoff
                    
                    print(f"[BUY-{request_id}] ⚠️ Attempt {attempts}/{max_attempts} failed: {str(e)}")
                    if attempts < max_attempts:
                        print(f"[BUY-{request_id}] 🔄 Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        print(f"[BUY-{request_id}] ❌ All {max_attempts} attempts failed. Last error: {str(e)}")
                        traceback.print_exc()
            
            # If we got here, all attempts failed
            raise last_exception
        return wrapper
    return decorator

@trading_bp.route('/buy', methods=['GET', 'POST'])
@trading_bp.route('/buy/', methods=['GET', 'POST'])
def buy():
    """Handle buy transactions with extensive logging and validation"""
    start_time = time.time()
    request_id = f"{int(start_time * 1000)}"
    
    # ====== INITIAL REQUEST LOGGING ======
    print(f"\n\n[BUY-{request_id}] ========== NEW BUY REQUEST ==========")
    print(f"[BUY-{request_id}] Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")
    print(f"[BUY-{request_id}] Request method: {request.method}")
    print(f"[BUY-{request_id}] Request path: {request.path}")
    print(f"[BUY-{request_id}] Content-Type: {request.content_type}")
    print(f"[BUY-{request_id}] Form data: {request.form}")
    print(f"[BUY-{request_id}] Args: {request.args}")
    print(f"[BUY-{request_id}] JSON: {request.get_json(silent=True)}")
    
    # ====== SESSION VALIDATION ======
    if 'user_id' not in session:
        print(f"[BUY-{request_id}] ERROR: No user_id in session. User not authenticated.")
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    print(f"[BUY-{request_id}] Authenticated user_id: {user_id}")
    
    # ====== USER DATA RETRIEVAL ======
    try:
        user_ref = db.collection('users').document(user_id)
        user_data = user_ref.get().to_dict()
        print(f"[BUY-{request_id}] Retrieved user data for {user_data.get('username', 'unknown')}")
        print(f"[BUY-{request_id}] Current balance: ${user_data.get('balance', 0)}")
    except Exception as e:
        print(f"[BUY-{request_id}] ERROR: Failed to retrieve user data: {str(e)}")
        traceback.print_exc()
        flash("System error: Unable to retrieve your account information", "error")
        return redirect(url_for('portfolio.portfolio'))
    
    # Initialize API key info variable with more details
    api_key_info = {
        'provider': 'Unknown',
        'key': 'None',
        'using_mock': False
    }
    
    # ====== POST REQUEST HANDLING ======
    if request.method == 'POST':
        print(f"[BUY-{request_id}] Processing POST request...")
        
        # Check if form data is present
        if not request.form:
            print(f"[BUY-{request_id}] CRITICAL ERROR: No form data received in POST request")
            flash("No data received. Please try again.", "error")
            return redirect(url_for('trading.buy'))
        
        # Triple validation of essential parameters with detailed logging
        
        # VALIDATION 1: Check if parameters exist
        print(f"[BUY-{request_id}] Validation phase 1: Checking if all required parameters exist")
        if 'symbol' not in request.form or 'shares' not in request.form:
            print(f"[BUY-{request_id}] ERROR: Missing required parameters in form data")
            for param in ['symbol', 'shares']:
                print(f"[BUY-{request_id}]   - Parameter '{param}' present: {'Yes' if param in request.form else 'No'}")
            flash("Missing required information. Please fill all fields.", "error")
            return redirect(url_for('trading.buy'))
        
        # Extract parameters
        symbol_raw = request.form.get('symbol', '')
        shares_raw = request.form.get('shares', '')
        
        # VALIDATION 2: Format and type checking
        print(f"[BUY-{request_id}] Validation phase 2: Format and type checking")
        
        # Symbol validation
        symbol = symbol_raw.upper().strip()
        if not symbol or not symbol.isalnum():
            print(f"[BUY-{request_id}] ERROR: Invalid symbol format: '{symbol_raw}'")
            flash("Invalid symbol format. Please enter a valid stock symbol.", "error")
            return redirect(url_for('trading.buy'))
        
        # Shares validation
        try:
            shares = float(shares_raw)
            if shares <= 0:
                print(f"[BUY-{request_id}] ERROR: Invalid shares value (must be positive): {shares}")
                flash("Quantity must be greater than zero.", "error")
                return redirect(url_for('trading.buy'))
        except ValueError:
            print(f"[BUY-{request_id}] ERROR: Shares value is not a valid number: '{shares_raw}'")
            flash("Invalid quantity. Please enter a valid number.", "error")
            return redirect(url_for('trading.buy'))
        
        # VALIDATION 3: Business rules and limits
        print(f"[BUY-{request_id}] Validation phase 3: Business rules and limits")
        
        # Validate maximum shares
        max_shares = 1000000
        if shares > max_shares:
            print(f"[BUY-{request_id}] ERROR: Shares quantity exceeds maximum limit ({max_shares}): {shares}")
            flash(f"Maximum allowed quantity is {max_shares}.", "error")
            return redirect(url_for('trading.buy'))
        
        print(f"[BUY-{request_id}] All validations passed. Processing order for {shares} shares of {symbol}")
        
        # Define a function to fetch price data with retry
        @retry_operation(max_attempts=3, delay=1)
        def fetch_price_with_retry(symbol, request_id):
            # Get API key information before calling fetch_stock_data
            from services.market_data import get_random_api_key, get_api_key_index
            
            # Get a random API key
            api_key = get_random_api_key()
            # Get the index of the selected API key (which key was used)
            api_key_index = get_api_key_index(api_key)
            
            # Log API key information prominently in terminal
            print(f"\n[BUY-{request_id}] ====== API KEY INFORMATION ======")
            print(f"[BUY-{request_id}] USING API KEY #{api_key_index + 1} for this purchase")
            if api_key:
                masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
                print(f"[BUY-{request_id}] Selected API key: {masked_key}")
                print(f"[BUY-{request_id}] Full API key: {api_key}")  # Log the full key for debugging
            else:
                print(f"[BUY-{request_id}] No valid API key available - using mock data!")
            print(f"[BUY-{request_id}] ================================\n")
            
            # Store API key info for display
            api_info = {}
            if api_key:
                api_info = {
                    'provider': 'Finnhub',
                    'key': masked_key,
                    'key_index': api_key_index + 1,
                    'using_mock': False,
                    'api_key': api_key  # Store the full key for later use
                }
            else:
                api_info = {
                    'provider': 'Mock Data',
                    'key': 'None (No API keys configured)',
                    'key_index': -1,
                    'using_mock': True,
                    'api_key': None
                }
            
            # Now fetch stock data using the selected API key
            from services.market_data import fetch_stock_data
            price_data = fetch_stock_data(symbol, api_key)
            print(f"[BUY-{request_id}] Stock price data for {symbol}: {price_data}")
            
            # Check if we're using mock data (API fallback)
            using_mock_data = price_data.get('mock_data', False)
            
            if not price_data or 'close' not in price_data or price_data['close'] <= 0:
                raise ValueError(f"Invalid stock price data for {symbol}")
                    
            current_price = price_data['close']
            
            # Update API key info if using mock data
            if using_mock_data:
                api_info = {
                    'provider': 'Mock Data',
                    'key': 'N/A - Using estimated prices',
                    'using_mock': True,
                    'api_key': None
                }
                print(f"[BUY-{request_id}] WARNING: Using mock data for {symbol} (API key invalid or missing)")
                print(f"[BUY-{request_id}] Mock price: ${current_price:.2f}")
            
            return current_price, api_info
        
        # ====== PRICE DATA RETRIEVAL ======
        try:
            # Use the retry wrapper for price fetching
            current_price, api_key_info = fetch_price_with_retry(symbol, request_id=request_id)
            
            print(f"[BUY-{request_id}] Data source: {api_key_info['provider']}")
            print(f"[BUY-{request_id}] Current price for {symbol}: ${current_price}")
        
            if api_key_info['using_mock']:
                flash(f"Warning: Using estimated price data for {symbol} due to market data service issues.", "warning")
                
        except Exception as e:
            print(f"[BUY-{request_id}] ERROR: Failed to fetch price data after multiple attempts: {str(e)}")
            traceback.print_exc()
            flash(f"Error fetching price data: {str(e)}", "error")
            return redirect(url_for('trading.buy'))
        
        # ====== COST CALCULATION ======
        total_cost = shares * current_price
        trading_fee = total_cost * 0.001  # 0.1% fee
        total_amount = total_cost + trading_fee
        
        print(f"[BUY-{request_id}] Cost calculation:")
        print(f"[BUY-{request_id}]   - Base cost: ${total_cost:.2f} ({shares} × ${current_price:.2f})")
        print(f"[BUY-{request_id}]   - Trading fee: ${trading_fee:.2f} (0.1% of ${total_cost:.2f})")
        print(f"[BUY-{request_id}]   - Total amount: ${total_amount:.2f}")
        
        # ====== BALANCE CHECK ======
        balance = user_data.get('balance', 0)
        if balance < total_amount:
            print(f"[BUY-{request_id}] ERROR: Insufficient funds. Required: ${total_amount:.2f}, Available: ${balance:.2f}")
            flash(f"Insufficient funds. You need ${total_amount:.2f} but have ${balance:.2f}", "error")
            return redirect(url_for('trading.buy'))
        
        print(f"[BUY-{request_id}] Funds check passed. Available: ${balance:.2f}")
        
        # ====== TRANSACTION EXECUTION ======
        transaction_id = f"{user_id}-{int(time.time() * 1000)}"
        print(f"[BUY-{request_id}] Beginning transaction execution. Transaction ID: {transaction_id}")
        
        try:
            # 1. Update user's balance
            new_balance = balance - total_amount
            print(f"[BUY-{request_id}] Updating balance: ${balance:.2f} → ${new_balance:.2f}")
            user_ref.update({'balance': new_balance})
            
            # 2. Update portfolio - only include essential fields for better compatibility
            print(f"[BUY-{request_id}] Checking for existing position of {symbol}")
            portfolio_query = db.collection('portfolios')\
                .where('user_id', '==', user_id)\
                .where('symbol', '==', symbol)\
                .limit(1)\
                .get()
            
            portfolio_items = list(portfolio_query)
            position_exists = len(portfolio_items) > 0
            
            if position_exists:
                # Update existing position
                position = portfolio_items[0]
                position_ref = position.reference
                position_data = position.to_dict()
                
                old_shares = position_data.get('shares', 0)
                old_price = position_data.get('purchase_price', 0)
                new_total_shares = old_shares + shares
                new_avg_price = ((old_shares * old_price) + (shares * current_price)) / new_total_shares
                
                print(f"[BUY-{request_id}] Updating existing position:")
                print(f"[BUY-{request_id}]   - Current: {old_shares} shares @ ${old_price:.2f}")
                print(f"[BUY-{request_id}]   - Adding: {shares} shares @ ${current_price:.2f}")
                print(f"[BUY-{request_id}]   - New: {new_total_shares} shares @ ${new_avg_price:.2f} (average)")
                
                position_ref.update({
                    'shares': new_total_shares,
                    'purchase_price': new_avg_price,
                    'latest_price': current_price,
                    'last_updated': firestore.SERVER_TIMESTAMP
                })
            else:
                # Create new position with only essential fields
                print(f"[BUY-{request_id}] Creating new position: {shares} shares of {symbol} @ ${current_price:.2f}")
                new_position = {
                    'user_id': user_id,
                    'symbol': symbol,
                    'shares': shares,
                    'purchase_price': current_price,
                    'latest_price': current_price,
                    'last_updated': firestore.SERVER_TIMESTAMP
                }
                print(f"[BUY-{request_id}] Portfolio fields being saved: {list(new_position.keys())}")
                db.collection('portfolios').add(new_position)
            
            # 3. Record transaction
            print(f"[BUY-{request_id}] Recording transaction using API key #{api_key_info.get('key_index', 'N/A')}")
            transaction_data = {
                'transaction_id': transaction_id,
                'user_id': user_id,
                'symbol': symbol,
                'shares': shares,
                'price': current_price,
                'total_amount': total_amount,
                'trading_fee': trading_fee,
                'transaction_type': 'BUY',
                'timestamp': firestore.SERVER_TIMESTAMP,
                'status': 'completed',
                'request_id': request_id,
                'api_provider': api_key_info['provider'],
                'api_key_index': api_key_info.get('key_index', 'N/A'),
                'data_source': 'Mock Data' if api_key_info['using_mock'] else 'Real-time API'
            }
            db.collection('transactions').add(transaction_data)
            
            # 4. Award badges
            try:
                print(f"[BUY-{request_id}] Checking for badge achievements")
                check_and_award_badges(user_id)
            except Exception as e:
                # Non-fatal error, just log it
                print(f"[BUY-{request_id}] WARNING: Badge check failed: {str(e)}")
                traceback.print_exc()
            
            # ====== SUCCESS HANDLING ======
            print(f"[BUY-{request_id}] Transaction completed successfully in {time.time() - start_time:.2f}s")
            data_source = "mock data" if api_key_info['using_mock'] else f"{api_key_info['provider']} API"
            print(f"[BUY-{request_id}] Purchase successful using {data_source}")
            flash(f"Successfully purchased {shares} shares of {symbol} for ${total_amount:.2f} using {data_source}", 'success')
            
            # Stay on buy page
            return redirect(url_for('trading.buy'))
            
        except Exception as e:
            print(f"[BUY-{request_id}] ❌ CRITICAL ERROR during transaction: {str(e)}")
            traceback.print_exc(file=sys.stdout)  # Print full traceback to terminal
            
            # ====== ERROR RECOVERY ======
            print(f"[BUY-{request_id}] Attempting recovery...")
            try:
                # Check if balance was deducted but position wasn't updated
                user_after = db.collection('users').document(user_id).get().to_dict()
                if user_after.get('balance') < balance:
                    print(f"[BUY-{request_id}] Balance was deducted. Restoring original balance: ${balance:.2f}")
                    user_ref.update({'balance': balance})
            except Exception as recovery_error:
                print(f"[BUY-{request_id}] ERROR during recovery: {str(recovery_error)}")
                traceback.print_exc(file=sys.stdout)
            
            flash(f"Transaction failed: {str(e)}", 'error')
            return redirect(url_for('trading.buy'))
    
    # ====== GET REQUEST HANDLING ======
    print(f"[BUY-{request_id}] Processing GET request - rendering buy form")
    try:
        # Get portfolio data
        portfolio_data = fetch_user_portfolio(user_id)
        
        # Create a fully populated user_portfolio object with proper defaults
        user_portfolio = {
            'total_value': float(portfolio_data.get('total_value', 0)),
            'invested_value': float(portfolio_data.get('invested_value', 0)),
            'available_cash': float(portfolio_data.get('available_cash', 0)),
            'todays_pl_str': portfolio_data.get("Today's P/L", '$0.00'),
            'todays_pl': float(portfolio_data.get("Today's P/L", '0').strip('$').replace(',', '')) 
                if isinstance(portfolio_data.get("Today's P/L"), str) else 0,
            'active_positions': portfolio_data.get('Active Positions', 0)  
        }
        
        # Log the portfolio data to help with debugging
        print(f"[BUY-{request_id}] User portfolio data:")
        print(f"[BUY-{request_id}]   - Total value: ${user_portfolio['total_value']:.2f}")
        print(f"[BUY-{request_id}]   - Invested value: ${user_portfolio['invested_value']:.2f}")
        print(f"[BUY-{request_id}]   - Cash balance: ${user_portfolio['available_cash']:.2f}")
        print(f"[BUY-{request_id}]   - Today's P/L: {user_portfolio['todays_pl_str']}")
        print(f"[BUY-{request_id}]   - Active positions: {user_portfolio['active_positions']}")
        
        # Get watchlist and recent orders
        user_watchlist_data = fetch_watchlist(user_id)
        user_recent_orders = fetch_recent_orders(user_id)
        
        # Get API keys status with more detail for display in the UI
        from services.market_data import get_api_keys_status
        api_keys_status = get_api_keys_status()
        
        # Print API status to terminal
        print(f"[BUY-{request_id}] API Keys Status:")
        print(f"[BUY-{request_id}]   - Finnhub: {'Available' if api_keys_status['finnhub']['available'] else 'Not configured'}")
        if not api_keys_status['finnhub']['available']:
            print(f"[BUY-{request_id}]   - USING MOCK PRICE DATA (no valid API keys)")
        print(f"[BUY-{request_id}]   - Coinbase: {api_keys_status['coinbase']['status']}")
        print(f"[BUY-{request_id}]   - YFinance: {api_keys_status['yfinance']['status']}")
        
        print(f"[BUY-{request_id}] Buy form rendered successfully in {time.time() - start_time:.2f}s")
        return render_template('buy.html.jinja2', 
                             user=user_data, 
                             user_portfolio=user_portfolio, 
                             watchlist=user_watchlist_data, 
                             recent_orders=user_recent_orders,
                             api_keys_status=api_keys_status)  # Add API keys status
    except Exception as e:
        print(f"[BUY-{request_id}] ERROR during GET processing: {str(e)}")
        traceback.print_exc()
        flash("Error loading page data", "error")
        return redirect(url_for('portfolio.portfolio'))


@trading_bp.route('/sell', methods=['GET', 'POST'])
def sell():
    """Handle sell transactions with extensive logging and validation"""
    start_time = time.time()
    request_id = f"{int(start_time * 1000)}"
    
    # ====== INITIAL REQUEST LOGGING ======
    print(f"\n\n[SELL-{request_id}] ========== NEW SELL REQUEST ==========")
    print(f"[SELL-{request_id}] Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}")
    print(f"[SELL-{request_id}] Request method: {request.method}")
    print(f"[SELL-{request_id}] Request path: {request.path}")
    print(f"[SELL-{request_id}] Content-Type: {request.content_type}")
    print(f"[SELL-{request_id}] Form data: {request.form}")
    print(f"[SELL-{request_id}] Args: {request.args}")
    print(f"[SELL-{request_id}] JSON: {request.get_json(silent=True)}")
    
    # ====== SESSION VALIDATION ======
    if 'user_id' not in session:
        print(f"[SELL-{request_id}] ERROR: No user_id in session. User not authenticated.")
        return redirect(url_for('auth.login'))
        
    user_id = session['user_id']
    print(f"[SELL-{request_id}] Authenticated user_id: {user_id}")
    
    # ====== USER DATA RETRIEVAL ======
    try:
        user_ref = db.collection('users').document(user_id)
        user_data = user_ref.get().to_dict()
        print(f"[SELL-{request_id}] Retrieved user data for {user_data.get('username', 'unknown')}")
    except Exception as e:
        print(f"[SELL-{request_id}] ERROR: Failed to retrieve user data: {str(e)}")
        traceback.print_exc()
        flash("System error: Unable to retrieve your account information", "error")
        return redirect(url_for('portfolio.portfolio'))

    # ====== POST REQUEST HANDLING ======
    if request.method == 'POST':
        print(f"[SELL-{request_id}] Processing POST request...")
        
        # Check if form data is present
        if not request.form:
            print(f"[SELL-{request_id}] CRITICAL ERROR: No form data received in POST request")
            flash("No data received. Please try again.", "error")
            return redirect(url_for('trading.sell'))
        
        # Triple validation of essential parameters with detailed logging
        
        # VALIDATION 1: Check if parameters exist
        print(f"[SELL-{request_id}] Validation phase 1: Checking if all required parameters exist")
        if 'symbol' not in request.form or 'shares' not in request.form:
            print(f"[SELL-{request_id}] ERROR: Missing required parameters in form data")
            for param in ['symbol', 'shares']:
                print(f"[SELL-{request_id}]   - Parameter '{param}' present: {'Yes' if param in request.form else 'No'}")
            flash("Missing required information. Please fill all fields.", "error")
            return redirect(url_for('trading.sell'))
        
        # Extract parameters
        symbol_raw = request.form.get('symbol', '')
        shares_raw = request.form.get('shares', '')
        
        # VALIDATION 2: Format and type checking
        print(f"[SELL-{request_id}] Validation phase 2: Format and type checking")
        
        # Symbol validation
        symbol = symbol_raw.upper().strip()
        if not symbol or not symbol.isalnum():
            print(f"[SELL-{request_id}] ERROR: Invalid symbol format: '{symbol_raw}'")
            flash("Invalid symbol format. Please select a valid position.", "error")
            return redirect(url_for('trading.sell'))
        
        # Shares validation
        try:
            shares_to_sell = float(shares_raw)
            if shares_to_sell <= 0:
                print(f"[SELL-{request_id}] ERROR: Invalid shares value (must be positive): {shares_to_sell}")
                flash("Quantity must be greater than zero.", "error")
                return redirect(url_for('trading.sell'))
        except ValueError:
            print(f"[SELL-{request_id}] ERROR: Shares value is not a valid number: '{shares_raw}'")
            flash("Invalid quantity. Please enter a valid number.", "error")
            return redirect(url_for('trading.sell'))
        
        # ====== PORTFOLIO POSITION CHECK ======
        try:
            print(f"[SELL-{request_id}] Finding position for {symbol}")
            portfolio_query = db.collection('portfolios')\
                .where('user_id', '==', user_id)\
                .where('symbol', '==', symbol)\
                .limit(1)\
                .get()
                
            portfolio_items = list(portfolio_query)
            if not portfolio_items:
                print(f"[SELL-{request_id}] ERROR: No position found for {symbol}")
                flash(f"You don't own any shares of {symbol}.", "error")
                return redirect(url_for('trading.sell'))
                
            position = portfolio_items[0]
            position_data = position.to_dict()
            
            # VALIDATION 3: Sufficient shares check
            owned_shares = position_data.get('shares', 0)
            print(f"[SELL-{request_id}] Position found: {owned_shares} shares of {symbol}")
            if owned_shares < shares_to_sell:
                print(f"[SELL-{request_id}] ERROR: Insufficient shares. Has: {owned_shares}, Wants to sell: {shares_to_sell}")
                flash(f"You can't sell {shares_to_sell} shares when you only own {owned_shares}.", "error")
                return redirect(url_for('trading.sell'))
        
        except Exception as e:
            print(f"[SELL-{request_id}] ERROR checking portfolio: {str(e)}")
            traceback.print_exc()
            flash("Error validating your portfolio position", "error")
            return redirect(url_for('trading.sell'))
        
        # ====== PRICE DATA RETRIEVAL ======
        try:
            # Simplified to only fetch stock data
            price_data = fetch_stock_data(symbol)
            print(f"[SELL-{request_id}] Stock price data for {symbol}: {price_data}")
            if not price_data or 'close' not in price_data:
                print(f"[SELL-{request_id}] ERROR: Invalid stock price data for {symbol}")
                flash(f"Unable to fetch current price for {symbol}. Please try again.", "error")
                return redirect(url_for('trading.sell'))
            current_price = price_data['close']
                
            print(f"[SELL-{request_id}] Current price for {symbol}: ${current_price}")
        
        except Exception as e:
            print(f"[SELL-{request_id}] ERROR: Failed to fetch price data: {str(e)}")
            traceback.print_exc()
            flash(f"Error fetching price data: {str(e)}", "error")
            return redirect(url_for('trading.sell'))
        
        # ====== TRANSACTION AMOUNT CALCULATION ======
        sale_amount = shares_to_sell * current_price
        trading_fee = sale_amount * 0.001
        net_amount = sale_amount - trading_fee
        purchase_price = position_data['purchase_price']
        profit_loss = (current_price - purchase_price) * shares_to_sell
        
        print(f"[SELL-{request_id}] Transaction calculation:")
        print(f"[SELL-{request_id}]   - Sale amount: ${sale_amount:.2f} ({shares_to_sell} × ${current_price:.2f})")
        print(f"[SELL-{request_id}]   - Trading fee: ${trading_fee:.2f} (0.1% of ${sale_amount:.2f})")
        print(f"[SELL-{request_id}]   - Net amount: ${net_amount:.2f}")
        print(f"[SELL-{request_id}]   - Profit/Loss: ${profit_loss:.2f}")
        
        # ====== TRANSACTION EXECUTION ======
        transaction_id = f"{user_id}-{int(time.time() * 1000)}"
        print(f"[SELL-{request_id}] Beginning transaction execution. Transaction ID: {transaction_id}")
        
        try:
            # Get current balance
            user_current = user_ref.get().to_dict()
            current_balance = user_current.get('balance', 0)
            
            # Direct updates instead of transaction
            # 1. Update user balance
            new_balance = current_balance + net_amount
            print(f"[SELL-{request_id}] Updating balance: ${current_balance:.2f} → ${new_balance:.2f}")
            user_ref.update({'balance': new_balance})
            
            # 2. Update portfolio
            remaining_shares = position_data['shares'] - shares_to_sell
            if remaining_shares > 0:
                print(f"[SELL-{request_id}] Updating position: {position_data['shares']} → {remaining_shares} shares")
                position.reference.update({
                    'shares': remaining_shares,
                    'latest_price': current_price,
                    'last_updated': firestore.SERVER_TIMESTAMP
                })
            else:
                print(f"[SELL-{request_id}] Removing position (all shares sold)")
                position.reference.delete()

            # 3. Record transaction - remove asset_type field
            print(f"[SELL-{request_id}] Recording transaction in database")
            transaction_data = {
                'transaction_id': transaction_id,
                'user_id': user_id,
                'symbol': symbol,
                'shares': shares_to_sell,
                'price': current_price,
                'total_amount': sale_amount,
                'net_amount': net_amount,
                'transaction_type': 'SELL',
                'timestamp': firestore.SERVER_TIMESTAMP,
                'trading_fee': trading_fee,
                'profit_loss': profit_loss,
                'purchase_price': purchase_price,
                'status': 'completed',
                'request_id': request_id
            }
            db.collection('transactions').add(transaction_data)
            
            # ====== SUCCESS HANDLING ======
            print(f"[SELL-{request_id}] Transaction completed successfully in {time.time() - start_time:.2f}s")
            flash(f"Successfully sold {shares_to_sell} shares of {symbol} for ${sale_amount:.2f}", 'success')
            return redirect(url_for('trading.sell'))
            
        except Exception as e:
            print(f"[SELL-{request_id}] CRITICAL ERROR during transaction: {str(e)}")
            traceback.print_exc()
            
            # No need for error recovery here as failure during sell doesn't deduct balance first
            flash(f"Transaction failed: {str(e)}", 'error')
            return redirect(url_for('trading.sell'))
    
    # ====== GET REQUEST HANDLING ======
    print(f"[SELL-{request_id}] Processing GET request - rendering sell form")
    try:
        # Get user's portfolio for the dropdown
        portfolio_query = db.collection('portfolios').where('user_id', '==', user_id).get()
        print(f"[SELL-{request_id}] Retrieved {len(list(portfolio_query))} portfolio items")
        
        portfolio_items = []
        for item in portfolio_query:
            item_data = item.to_dict()
            portfolio_items.append({
                'symbol': item_data.get('symbol', ''),
                'shares': item_data.get('shares', 0),
                'purchase_price': item_data.get('purchase_price', 0)
            })
            
        print(f"[SELL-{request_id}] Sell form rendered successfully in {time.time() - start_time:.2f}s")
        return render_template('sell.html.jinja2', 
                             portfolio_items=portfolio_items, 
                             user=user_data)
                             
    except Exception as e:
        print(f"[SELL-{request_id}] ERROR during GET processing: {str(e)}")
        traceback.print_exc()
        flash("Error loading your portfolio data", "error")
        return redirect(url_for('portfolio.portfolio'))


# Helper function to manually check if a POST request is valid
def is_valid_post_request(req, required_fields=[]):
    """Triple-check if a request is a valid POST with required fields"""
    
    # Check method
    if req.method != 'POST':
        print("POST check failed: Wrong method")
        return False
        
    # Check if form data exists
    if not req.form and not req.json:
        print("POST check failed: No form or JSON data")
        return False
        
    # Check required fields
    for field in required_fields:
        if field not in req.form and (not req.json or field not in req.json):
            print(f"POST check failed: Missing required field '{field}'")
            return False
            
    return True