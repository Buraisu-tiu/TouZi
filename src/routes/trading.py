# src/routes/trading.py
from flask import Blueprint, request, session, redirect, url_for, render_template, flash
from utils.db import db
from services.market_data import fetch_stock_data
from google.cloud import firestore

trading_bp = Blueprint('trading', __name__)

@trading_bp.route('/buy', methods=['GET', 'POST'])
@trading_bp.route('/buy/', methods=['GET', 'POST'])  # Add trailing slash route
def buy():
    print(f"[BUY] Entered buy route: path={request.path}, method={request.method}")
    if 'user_id' not in session:
        print("[BUY] No user_id in session")
        return redirect(url_for('auth.login'))
    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)

    if request.method == 'POST':
        print("[BUY] POST request received")
        print(f"[BUY] Form data: {dict(request.form)}")
        symbol = request.form.get('symbol', '').upper().strip()
        try:
            shares = float(request.form.get('shares', 0))
        except Exception:
            shares = 0
        print(f"[BUY] symbol={symbol}, shares={shares}")
        if not symbol or shares <= 0:
            print("[BUY] Invalid symbol or quantity")
            flash('Invalid symbol or quantity', 'error')
            return redirect(url_for('trading.buy'))

        price_data = fetch_stock_data(symbol)
        print(f"[BUY] price_data={price_data}")
        if not price_data or 'close' not in price_data or price_data['close'] <= 0:
            print("[BUY] Unable to fetch stock price")
            flash('Unable to fetch stock price', 'error')
            return redirect(url_for('trading.buy'))
        current_price = price_data['close']

        total_cost = shares * current_price
        trading_fee = total_cost * 0.001
        total_amount = total_cost + trading_fee
        print(f"[BUY] total_cost={total_cost}, trading_fee={trading_fee}, total_amount={total_amount}")

        from google.cloud import firestore as gcf_firestore
        firestore_client = db
        def buy_transaction(transaction):
            user_snapshot = transaction.get(user_ref)
            user_data = user_snapshot.to_dict()
            balance = user_data.get('balance', 0)
            print(f"[BUY] User balance before purchase: {balance}")
            if balance < total_amount:
                print("[BUY] Insufficient funds")
                raise Exception('Insufficient funds')
            transaction.update(user_ref, {'balance': balance - total_amount})

            # Portfolio update
            portfolio_query = firestore_client.collection('portfolios')\
                .where('user_id', '==', user_id)\
                .where('symbol', '==', symbol)\
                .where('asset_type', '==', 'stock')\
                .limit(1)\
                .get()
            portfolio_items = list(portfolio_query)
            if portfolio_items:
                position_ref = portfolio_items[0].reference
                position_data = portfolio_items[0].to_dict()
                total_shares = position_data['shares'] + shares
                total_cost_basis = (position_data['shares'] * position_data['purchase_price']) + (shares * current_price)
                new_avg_price = total_cost_basis / total_shares
                print(f"[BUY] Updating existing position: {total_shares} shares at avg price {new_avg_price}")
                transaction.update(position_ref, {
                    'shares': total_shares,
                    'purchase_price': new_avg_price,
                    'latest_price': current_price,
                    'last_updated': gcf_firestore.SERVER_TIMESTAMP
                })
            else:
                new_position = {
                    'user_id': user_id,
                    'symbol': symbol,
                    'shares': shares,
                    'asset_type': 'stock',
                    'purchase_price': current_price,
                    'latest_price': current_price,
                    'last_updated': gcf_firestore.SERVER_TIMESTAMP
                }
                print(f"[BUY] Creating new position: {new_position}")
                transaction.set(firestore_client.collection('portfolios').document(), new_position)

            # Record transaction
            transaction.set(firestore_client.collection('transactions').document(), {
                'user_id': user_id,
                'symbol': symbol,
                'shares': shares,
                'price': current_price,
                'total_amount': total_amount,
                'transaction_type': 'BUY',
                'asset_type': 'stock',
                'timestamp': gcf_firestore.SERVER_TIMESTAMP,
                'trading_fee': trading_fee,
                'status': 'completed'
            })
            print("[BUY] Transaction recorded")

        try:
            firestore_client.transaction()(buy_transaction)
            print("[BUY] Purchase successful")
            flash(f'Successfully purchased {shares} shares of {symbol}', 'success')
            return redirect(url_for('portfolio.portfolio'))
        except Exception as e:
            print(f"[BUY ERROR] {e}")
            flash(str(e), 'error')
            return redirect(url_for('trading.buy'))

    print("[BUY] GET request - rendering buy form")
    user_data = user_ref.get().to_dict()
    return render_template('buy.html.jinja2', user=user_data, user_portfolio={}, watchlist=[], recent_orders=[])

@trading_bp.route('/sell', methods=['GET', 'POST'])
def sell():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user_id = session['user_id']
    user_ref = db.collection('users').document(user_id)
    user_data = user_ref.get().to_dict()

    if request.method == 'POST':
        symbol = request.form.get('symbol', '').upper()
        try:
            shares_to_sell = float(request.form.get('shares', 0))
        except Exception:
            shares_to_sell = 0
        if not symbol or shares_to_sell <= 0:
            flash('Invalid symbol or quantity', 'error')
            return redirect(url_for('trading.sell'))

        # Get portfolio position
        position_query = db.collection('portfolios')\
            .where('user_id', '==', user_id)\
            .where('symbol', '==', symbol)\
            .where('asset_type', '==', 'stock')\
            .limit(1)\
            .get()
        portfolio_items = list(position_query)
        if not portfolio_items:
            flash(f'No position found for {symbol}', 'error')
            return redirect(url_for('trading.sell'))
        position = portfolio_items[0]
        position_data = position.to_dict()

        if position_data['shares'] < shares_to_sell:
            flash(f'Insufficient shares. You only have {position_data["shares"]} {symbol}', 'error')
            return redirect(url_for('trading.sell'))

        # Get current price
        price_data = fetch_stock_data(symbol)
        if not price_data or 'close' not in price_data or price_data['close'] <= 0:
            flash('Unable to fetch stock price', 'error')
            return redirect(url_for('trading.sell'))
        current_price = price_data['close']

        sale_amount = shares_to_sell * current_price
        trading_fee = sale_amount * 0.001
        net_amount = sale_amount - trading_fee
        purchase_price = position_data['purchase_price']
        profit_loss = (current_price - purchase_price) * shares_to_sell

        # Start transaction
        transaction_batch = db.batch()
        new_balance = user_data['balance'] + net_amount
        transaction_batch.update(user_ref, {'balance': new_balance})

        remaining_shares = position_data['shares'] - shares_to_sell
        if remaining_shares > 0:
            transaction_batch.update(position.reference, {
                'shares': remaining_shares,
                'last_updated': firestore.SERVER_TIMESTAMP
            })
        else:
            transaction_batch.delete(position.reference)

        transaction_ref = db.collection('transactions').document()
        transaction_batch.set(transaction_ref, {
            'user_id': user_id,
            'symbol': symbol,
            'shares': shares_to_sell,
            'price': current_price,
            'total_amount': sale_amount,
            'net_amount': net_amount,
            'transaction_type': 'SELL',
            'asset_type': 'stock',
            'timestamp': firestore.SERVER_TIMESTAMP,
            'trading_fee': trading_fee,
            'profit_loss': profit_loss,
            'purchase_price': purchase_price
        })

        transaction_batch.commit()
        flash(f'Successfully sold {shares_to_sell} shares of {symbol} for ${sale_amount:.2f}', 'success')
        return redirect(url_for('portfolio.portfolio'))

    # GET: show sell form
    portfolio_query = db.collection('portfolios').where('user_id', '==', user_id).where('asset_type', '==', 'stock').get()
    portfolio_items = [
        {
            'symbol': item.to_dict()['symbol'],
            'shares': item.to_dict()['shares'],
            'asset_type': item.to_dict()['asset_type']
        }
        for item in portfolio_query
    ]
    return render_template('sell.html.jinja2', portfolio_items=portfolio_items, user=user_data)