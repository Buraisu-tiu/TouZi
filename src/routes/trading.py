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
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    user_data = user_ref.get().to_dict()
    
    # Get portfolio data in a cleaner format
    portfolio_data = fetch_user_portfolio(user_id)
    total_pl = portfolio_data.get('Total P/L', '$0.00')

    user_portfolio = {
        'total_value': float(portfolio_data.get('Total Assets', '0').strip('$')),
        'todays_pl_str': portfolio_data.get("Today's P/L", '$0.00'),
        'todays_pl': float(portfolio_data.get("Today's P/L", '0').strip('$')),
        'active_positions': portfolio_data.get('Active Positions', 0)  # Changed from win_rate
    }
    
    # Get watchlist and recent orders
    user_watchlist_data = fetch_watchlist(user_id)
    user_recent_orders = fetch_recent_orders(user_id)
    
    # Handle POST request for buying 
    if request.method == 'POST':
        try:
            # ...existing transaction processing code...
            
            # Check for badge unlocks after purchase
            check_and_award_badges(user_id)
            
            # ...existing code...
            
        except Exception as e:
            # ...existing error handling...
            pass

    return render_template('buy.html.jinja2',
                         user=user_data,
                         user_portfolio=user_portfolio,
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