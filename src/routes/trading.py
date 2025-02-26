# src/routes/trading.py
from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from utils.db import db
from services.market_data import fetch_stock_data, fetch_crypto_data, fetch_market_overview, fetch_user_portfolio, fetch_recent_orders
from services.badge_services import check_and_award_badges
from routes.watchlist import fetch_watchlist
import datetime
import requests


trading_bp = Blueprint('trading', __name__)

def buy():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    user = user_ref.get().to_dict()

    if request.method == 'POST':
        try:
            symbol = request.form.get('symbol', '').upper().strip()
            shares = float(request.form.get('shares'))
            asset_type = request.form.get('asset_type')

            if shares <= 0 or not symbol or len(symbol) > 10:
                flash('Invalid input', 'error')
                return redirect(url_for('buy'))

            # Fetch current price
            if asset_type == 'stock':
                price_data = fetch_stock_data(symbol)
                if 'error' in price_data:
                    flash(price_data['error'], 'error')
                    return redirect(url_for('buy'))
                price = price_data['close']
            elif asset_type == 'crypto':
                price_data = fetch_crypto_data(symbol)
                if 'error' in price_data:
                    flash(price_data['error'], 'error')
                    return redirect(url_for('buy'))
                price = price_data['price']
            else:
                flash('Invalid asset type', 'error')
                return redirect(url_for('buy'))

            total_cost = round(price * shares, 2)

            # Check funds
            if total_cost > user['balance']:
                flash(f'Insufficient funds. Need ${total_cost:.2f}, have ${user["balance"]:.2f}', 'error')
                return redirect(url_for('buy'))

            # Process purchase
            portfolio_query = db.collection('portfolios').where('user_id', '==', user_id).where('symbol', '==', symbol).limit(1).get()
            
            if portfolio_query:
                portfolio_doc = portfolio_query[0]
                portfolio_data = portfolio_doc.to_dict()
                new_shares = portfolio_data['shares'] + shares
                new_total_cost = portfolio_data.get('total_cost', 0) + total_cost
                
                portfolio_doc.reference.update({
                    'shares': new_shares,
                    'total_cost': new_total_cost,
                    'last_updated': datetime.utcnow()
                })
            else:
                db.collection('portfolios').add({
                    'user_id': user_id,
                    'symbol': symbol,
                    'shares': shares,
                    'asset_type': asset_type,
                    'total_cost': total_cost,
                    'purchase_price': price,
                    'last_updated': datetime.utcnow()
                })

            # Update user balance
            new_balance = round(user['balance'] - total_cost, 2)
            user_ref.update({'balance': new_balance})

            # Record transaction
            db.collection('transactions').add({
                'user_id': user_id,
                'symbol': symbol,
                'shares': shares,
                'price': price,
                'total_amount': total_cost,
                'transaction_type': 'BUY',
                'asset_type': asset_type,
                'timestamp': datetime.utcnow()
            })

            # Check for badges
            check_and_award_badges(user_id)

            flash(f'Successfully purchased {shares} {symbol} for ${total_cost:.2f}', 'success')
            return redirect(url_for('buy'))

        except ValueError as e:
            flash(f'Invalid input: {str(e)}', 'error')
            return redirect(url_for('buy'))
        except Exception as e:
            flash(f'Transaction failed: {str(e)}', 'error')
            return redirect(url_for('buy'))

    # Fetch additional data for the enhanced buy page
    market_overview = fetch_market_overview()
    user_portfolio = fetch_user_portfolio(user_id)
    watchlist = fetch_watchlist(user_id)
    print("Watchlist data:", watchlist)  # Debugging line
    recent_orders = fetch_recent_orders(user_id)
    
    return render_template('buy.html.jinja2', 
                           user=user, 
                           market_overview=market_overview,
                           user_portfolio=user_portfolio,
                           watchlist=watchlist,
                           recent_orders=recent_orders)

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
                return redirect(url_for('sell'))

            # Get current user
            user_id = session['user_id']
            user_ref = db.collection('users').document(user_id)
            user = user_ref.get().to_dict()

            if not user:
                flash('User not found', 'error')
                return redirect(url_for('login'))

            # Find the portfolio entry for this symbol
            portfolio_query = db.collection('portfolios').where('user_id', '==', user_id).where('symbol', '==', symbol).limit(1).get()
            
            if not portfolio_query:
                flash(f'You do not own any {symbol}', 'error')
                return redirect(url_for('sell'))

            # Get portfolio details
            portfolio = portfolio_query[0]
            portfolio_data = portfolio.to_dict()
            
            # Check if user has enough shares
            if portfolio_data['shares'] < shares_to_sell:
                flash(f'Insufficient shares. You only have {portfolio_data["shares"]} {symbol}', 'error')
                return redirect(url_for('sell'))

            # Fetch current market price
            if portfolio_data['asset_type'] == 'stock':
                stock_data = fetch_stock_data(symbol)
                if 'error' in stock_data:
                    flash(f"Error fetching stock data: {stock_data['error']}", 'error')
                    return redirect(url_for('sell'))
                
                current_price = stock_data['close']

            elif portfolio_data['asset_type'] == 'crypto':
                try:
                    response = requests.get(f'https://api.coinbase.com/v2/prices/{symbol}-USD/spot')
                    response.raise_for_status()
                    data = response.json()
                    current_price = float(data['data']['amount'])
                except requests.exceptions.RequestException as e:
                    flash(f"Failed to fetch cryptocurrency data: {e}", 'error')
                    return redirect(url_for('sell'))
            else:
                flash('Invalid asset type', 'error')
                return redirect(url_for('sell'))

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
            return redirect(url_for('sell', success=True))

        except ValueError as e:
            flash('Invalid input. Please check your entries.', 'error')
            return redirect(url_for('sell'))
        
        except Exception as e:
            # Log unexpected errors
            trading_bp.logger.error(f"Unexpected error in sell function: {e}")
            flash('An unexpected error occurred. Please try again.', 'error')
            return redirect(url_for('sell'))

    # Fallback for any other scenarios
    return render_template('sell.html.jinja2')