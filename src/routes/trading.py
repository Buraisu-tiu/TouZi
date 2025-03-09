# src/routes/trading.py
from flask import Blueprint, request, session, redirect, url_for, render_template, flash, current_app
from utils.db import db
from services.market_data import fetch_stock_data, fetch_crypto_data, fetch_user_portfolio, fetch_recent_orders
from services.badge_services import check_and_award_badges
from routes.watchlist import fetch_watchlist
from datetime import datetime
import requests


trading_bp = Blueprint('trading', __name__)

@trading_bp.route('/buy', methods=['GET', 'POST'])
def buy():
    print("Received request to /buy")
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_identifier = session['user_id']
    user_reference = db.collection('users').document(user_identifier)
    user_data = user_reference.get().to_dict()
    
    if request.method == 'POST':
        try:
            stock_symbol = request.form.get('symbol', '').upper().strip()
            number_of_shares = float(request.form.get('shares'))
            asset_category = request.form.get('asset_type')

            print("Received purchase request for:", number_of_shares, stock_symbol, asset_category)  # Debugging

            if number_of_shares <= 0 or not stock_symbol or len(stock_symbol) > 10:
                flash('Invalid input', 'error')
                return redirect(url_for('trading.buy'))

            # Fetch current price before logging it
            if asset_category == 'stock':
                stock_price_data = fetch_stock_data(stock_symbol)
                if not stock_price_data or 'error' in stock_price_data:
                    flash(stock_price_data.get('error', 'Could not fetch stock price.'), 'error')
                    return redirect(url_for('trading.buy'))
                print(stock_price_data)
                if 'close' not in stock_price_data: 
                    flash(stock_price_data.get('error', 'Could not fetch stock price because close not in stock_price_data'), 'error')
                    print("Close not in stock price data")
                    return redirect(url_for('trading.buy'))
                stock_price = stock_price_data['close']
            elif asset_category == 'crypto':
                cryptocurrency_price_data = fetch_crypto_data(stock_symbol)
                if 'error' in cryptocurrency_price_data:
                    flash(cryptocurrency_price_data['error'], 'error')
                    return redirect(url_for('trading.buy'))
                stock_price = cryptocurrency_price_data['price']
            else:
                flash('Invalid asset type', 'error')
                return redirect(url_for('trading.buy'))

            total_purchase_cost = round(stock_price * number_of_shares, 2)

            print(f"Buying {number_of_shares} {stock_symbol} at {stock_price} each. Total cost: {total_purchase_cost}")  # Debugging

            # Check if user has enough funds
            if total_purchase_cost > user_data['balance']:
                flash(f'Insufficient funds. Need ${total_purchase_cost:.2f}, have ${user_data["balance"]:.2f}', 'error')
                return redirect(url_for('trading.buy'))

            # Process purchase
            portfolio_query_result = db.collection('portfolios').where('user_id', '==', user_identifier).where('symbol', '==', stock_symbol).limit(1).get()
            print("Portfolio Query Result:", portfolio_query_result)
            if portfolio_query_result:
                print("Stock found in portfolio, updating...")
            else:
                print("Stock not found in portfolio, creating new entry...")

            if portfolio_query_result:
                portfolio_document = portfolio_query_result[0]
                portfolio_data = portfolio_document.to_dict()
                updated_shares = portfolio_data['shares'] + number_of_shares
                updated_total_cost = portfolio_data.get('total_cost', 0) + total_purchase_cost
                
                portfolio_document.reference.update({
                    'shares': updated_shares,
                    'total_cost': updated_total_cost,
                    'last_updated': datetime.utcnow()
                })
            else:
                db.collection('portfolios').add({
                    'user_id': user_identifier,
                    'symbol': stock_symbol,
                    'shares': number_of_shares,
                    'asset_type': asset_category,
                    'total_cost': total_purchase_cost,
                    'purchase_price': stock_price,
                    'last_updated': datetime.utcnow()
                })

            # Update user balance
            updated_user_balance = round(user_data['balance'] - total_purchase_cost, 2)
            user_reference.update({'balance': updated_user_balance})
            user_data = user_reference.get().to_dict()
            print("User balance after purchase:", user_data["balance"])

            # Record transaction
            db.collection('transactions').add({
                'user_id': user_identifier,
                'symbol': stock_symbol,
                'shares': number_of_shares,
                'price': stock_price,
                'total_amount': total_purchase_cost,
                'transaction_type': 'BUY',
                'asset_type': asset_category,
                'timestamp': datetime.utcnow()
            })
            transaction_records = db.collection("transactions").where("user_id", "==", user_identifier).stream()
            for transaction in transaction_records:
                print(transaction.to_dict())

            # Check for badges
            check_and_award_badges(user_identifier)

            flash(f'Successfully purchased {number_of_shares} {stock_symbol} for ${total_purchase_cost:.2f}', 'success')
            return redirect(url_for('trading.buy'))

        except ValueError as value_error_exception:
            flash(f'Invalid input: {str(value_error_exception)}', 'error')
            return redirect(url_for('trading.buy'))
        except Exception as generic_exception:
            flash(f'Transaction failed: {str(generic_exception)}', 'error')
            return redirect(url_for('trading.buy'))

    # Fetch additional data for the enhanced buy page
    user_portfolio_data = fetch_user_portfolio(user_identifier)
    user_watchlist_data = fetch_watchlist(user_identifier)
    print("Watchlist data:", user_watchlist_data)  # Debugging line
    user_recent_orders = fetch_recent_orders(user_identifier)
    
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
        return redirect(url_for('login'))

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