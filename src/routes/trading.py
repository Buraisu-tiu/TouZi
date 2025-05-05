# src/routes/trading.py
from flask import Blueprint, request, session, redirect, url_for, render_template, flash, current_app
from utils.db import db
from services.market_data import fetch_stock_data, fetch_crypto_data, fetch_user_portfolio, fetch_recent_orders
from services.badge_services import check_and_award_badges
from routes.watchlist import fetch_watchlist
from datetime import datetime
import requests
from google.cloud import firestore

trading_bp = Blueprint('trading', __name__)

@trading_bp.route('/buy', methods=['GET', 'POST'])
def buy():
    print("Received request to /buy")
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    user_data = user_ref.get().to_dict()
    
    if request.method == 'POST':
        try:
            stock_symbol = request.form.get('symbol', '').upper().strip()
            number_of_shares = float(request.form.get('shares'))
            asset_category = request.form.get('asset_type')

            print("Received purchase request for:", number_of_shares, stock_symbol, asset_category)  # Debugging

            if number_of_shares <= 0 or not stock_symbol or len(stock_symbol) > 10:
                flash('Invalid input: Symbol or quantity is missing or incorrect', 'error')
                return redirect(url_for('trading.buy'))

            # Add daily transaction limit check
            today = datetime.utcnow().date()
            start_of_day = datetime(today.year, today.month, today.day)
            transactions = db.collection('transactions')\
                .where(filter=firestore.FieldFilter('user_id', '==', user_id))\
                .where(filter=firestore.FieldFilter('timestamp', '>=', start_of_day))\
                .get()
            
            if len(transactions) >= 10:  # Limit to 10 transactions per day
                flash('Daily transaction limit reached', 'error')
                return redirect(url_for('trading.buy'))

            # Fetch current price before logging it
            if asset_category == 'stock':
                stock_price_data = fetch_stock_data(stock_symbol)
                if not stock_price_data or 'error' in stock_price_data:
                    flash(stock_price_data.get('error', 'Could not fetch stock price.'), 'error')
                    return redirect(url_for('trading.buy'))
                if 'close' not in stock_price_data: 
                    flash('Error: Close price not found in stock data', 'error')
                    return redirect(url_for('trading.buy'))
                stock_price = stock_price_data['close']
            elif asset_category == 'crypto':
                cryptocurrency_price_data = fetch_crypto_data(stock_symbol)
                if 'error' in cryptocurrency_price_data:
                    flash(cryptocurrency_price_data['error'], 'error')
                    return redirect(url_for('trading.buy'))
                if 'price' not in cryptocurrency_price_data:
                    flash('Error: Price not found in crypto data', 'error')
                    return redirect(url_for('trading.buy'))
                stock_price = cryptocurrency_price_data['price']
            else:
                flash('Invalid asset type', 'error')
                return redirect(url_for('trading.buy'))

            total_purchase_cost = round(stock_price * number_of_shares, 2)

            print(f"Buying {number_of_shares} {stock_symbol} at {stock_price} each. Total cost: {total_purchase_cost}")  # Debugging

            # Add trading fee calculation (0.1% of transaction)
            trading_fee = round(total_purchase_cost * 0.001, 2)
            total_cost_with_fee = total_purchase_cost + trading_fee

            # Check if user has enough funds
            if total_cost_with_fee > user_data['balance']:
                flash(f'Insufficient funds. Need ${total_cost_with_fee:.2f} (including ${trading_fee:.2f} fee)', 'error')
                return redirect(url_for('trading.buy'))

            # Start Firestore transaction
            @firestore.transactional
            def perform_purchase(transaction, user_ref, portfolio_ref, user_data, stock_symbol, number_of_shares, asset_category, stock_price, total_purchase_cost, trading_fee, total_cost_with_fee):
                # Get portfolio data within transaction
                portfolio_doc = portfolio_ref.get(transaction=transaction)
                if portfolio_doc.exists:
                    portfolio_data = portfolio_doc.to_dict()
                    updated_shares = portfolio_data['shares'] + number_of_shares
                    updated_total_cost = portfolio_data.get('total_cost', 0) + total_purchase_cost
                    transaction.update(portfolio_ref, {
                        'shares': updated_shares,
                        'total_cost': updated_total_cost,
                        'purchase_price': stock_price,
                        'last_updated': datetime.utcnow()
                    })
                else:
                    transaction.set(portfolio_ref, {
                        'user_id': user_id,
                        'symbol': stock_symbol,
                        'shares': number_of_shares,
                        'asset_type': asset_category,
                        'total_cost': total_purchase_cost,
                        'purchase_price': stock_price,
                        'last_updated': datetime.utcnow()
                    })

                # Update user balance within transaction
                updated_user_balance = round(user_data['balance'] - total_cost_with_fee, 2)
                transaction.update(user_ref, {'balance': updated_user_balance})

                # Record transaction within transaction
                transaction_data = {
                    'user_id': user_id,
                    'symbol': stock_symbol,
                    'shares': number_of_shares,
                    'price': stock_price,
                    'total_amount': total_purchase_cost,
                    'transaction_type': 'BUY',
                    'asset_type': asset_category,
                    'fee': trading_fee,
                    'timestamp': datetime.utcnow()
                }
                transaction_ref = db.collection('transactions').document()
                transaction.set(transaction_ref, transaction_data)

                return updated_user_balance

            # Execute transaction
            transaction = db.transaction()
            portfolio_ref = db.collection('portfolios').document(f'{user_id}_{stock_symbol}')
            updated_balance = perform_purchase(transaction, user_ref, portfolio_ref, user_data, stock_symbol, number_of_shares, asset_category, stock_price, total_purchase_cost, trading_fee, total_cost_with_fee)

            # Update session and check badges after successful transaction
            session['balance'] = updated_balance
            check_and_award_badges(user_id)

            flash(f'Successfully purchased {number_of_shares} {stock_symbol} for ${total_cost_with_fee:.2f} (including ${trading_fee:.2f} fee)', 'success')
            return redirect(url_for('trading.buy'))

        except ValueError as value_error_exception:
            flash(f'Invalid input: {str(value_error_exception)}', 'error')
            return redirect(url_for('trading.buy'))
        except Exception as generic_exception:
            flash(f'Transaction failed: {str(generic_exception)}', 'error')
            return redirect(url_for('trading.buy'))

    # Fetch additional data for the enhanced buy page
    user_portfolio_data = fetch_user_portfolio(user_id)
    user_watchlist_data = fetch_watchlist(user_id)
    user_recent_orders = fetch_recent_orders(user_id)
    
    return render_template('buy.html.jinja2', 
                           user=user_data, 
                           user_portfolio=user_portfolio_data,
                           watchlist=user_watchlist_data,
                           recent_orders=user_recent_orders)


@trading_bp.route('/sell', methods=['GET', 'POST'])
def sell():
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please log in to sell assets', 'error')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    user = user_ref.get().to_dict() or {}  # Provide a default empty dict if user is None

    # Handle GET request
    if request.method == 'GET':
        success = request.args.get('success', False)
        
        # Fetch user's portfolio
        portfolio_query = db.collection('portfolios').where('user_id', '==', user_id).get()
        
        # Prepare portfolio items for the dropdown
        portfolio_items = [
            {
                'symbol': item.to_dict()['symbol'], 
                'shares': item.to_dict()['shares'], 
                'asset_type': item.to_dict()['asset_type']
            } 
            for item in portfolio_query
        ]

        return render_template('sell.html.jinja2', 
                               portfolio_items=portfolio_items, 
                               success=success, 
                               user=user)

    # Handle POST request
    if request.method == 'POST':
        try:
            # Validate form inputs
            symbol = request.form['symbol'].upper()
            shares_to_sell = float(request.form['shares'])
            
            # Validate inputs
            if not symbol or shares_to_sell <= 0:
                flash('Invalid symbol or quantity', 'error')
                return redirect(url_for('sell.html.jinja2'))

            # Get current user
            user_id = session['user_id']
            user_ref = db.collection('users').document(user_id)
            user = user_ref.get().to_dict()

            if not user:
                flash('User not found', 'error')
                return redirect(url_for('auth.login'))

            # Find the portfolio entry for this symbol
            portfolio_query = db.collection('portfolios').where('user_id', '==', user_id).where('symbol', '==', symbol).limit(1).get()
            
            if not portfolio_query:
                flash(f'You do not own any {symbol}', 'error')
                return redirect(url_for('sell.html.jinja2'))

            # Get portfolio details
            portfolio = portfolio_query[0]
            portfolio_data = portfolio.to_dict()
            
            # Check if user has enough shares
            if portfolio_data['shares'] < shares_to_sell:
                flash(f'Insufficient shares. You only have {portfolio_data["shares"]} {symbol}', 'error')
                return redirect(url_for('sell.html.jinja2'))

            # Fetch current market price
            if portfolio_data['asset_type'] == 'stock':
                stock_data = fetch_stock_data(symbol)
                if 'error' in stock_data:
                    flash(f"Error fetching stock data: {stock_data['error']}", 'error')
                    return redirect(url_for('sell.html.jinja2'))
                
                current_price = stock_data['close']

            elif portfolio_data['asset_type'] == 'crypto':
                try:
                    response = requests.get(f'https://api.coinbase.com/v2/prices/{symbol}-USD/spot')
                    response.raise_for_status()
                    data = response.json()
                    current_price = float(data['data']['amount'])
                except requests.exceptions.RequestException as e:
                    flash(f"Failed to fetch cryptocurrency data: {e}", 'error')
                    return redirect(url_for('sell.html.jinja2'))
            else:
                flash('Invalid asset type', 'error')
                return redirect(url_for('sell.html.jinja2'))

            # Calculate sale details
            sale_amount = current_price * shares_to_sell
            remaining_shares = portfolio_data['shares'] - shares_to_sell

            # Update portfolio
            if remaining_shares > 0:
                portfolio.reference.update({
                    'shares': remaining_shares
                })
            else:
                # Remove the portfolio entry if no shares left
                portfolio.reference.delete()

            # Update user balance
            new_balance = round(user['balance'] + sale_amount, 2)
            user_ref.update({'balance': new_balance})

            # Record transaction
            db.collection('transactions').add({
                'user_id': user_id,
                'symbol': symbol,
                'shares': shares_to_sell,
                'price': current_price,
                'total_amount': sale_amount,
                'transaction_type': 'SELL',
                'asset_type': portfolio_data['asset_type'],
                'timestamp': datetime.utcnow()
            })


            # Flash success message
            check_and_award_badges(user_id)
            flash(f'Successfully sold {shares_to_sell} {symbol} for ${sale_amount:.2f}', 'success')
            return redirect(url_for('trading.sell', success=True))

        except ValueError as e:
            flash('Invalid input. Please check your entries.', 'error')
            return redirect(url_for('sell.html.jinja2'))
        
        except Exception as e:
            # Log unexpected errors
            current_app.logger.error(f"Unexpected error in sell function: {e}") 
            flash('An unexpected error occurred. Please try again.', 'error')
            return redirect(url_for('sell.html.jinja2'))

    # Fallback for any other scenarios
    return render_template('sell.html.jinja2')