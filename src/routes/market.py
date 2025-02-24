# src/routes/market.py
from flask import Blueprint, render_template, session, redirect, url_for
from ..utils.db import db
from ..services.market_data import fetch_market_overview, fetch_user_portfolio
from ..utils.constants import POPULAR_STOCKS

market_bp = Blueprint('market', __name__)

@market_bp.route('/popular_stocks')
def popular_stocks():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    
    return render_template('popular_stocks.html.jinja2', 
                         stocks=POPULAR_STOCKS, 
                         user=user)

@market_bp.route('/history')
def transaction_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    transactions = db.collection('transactions')\
        .where('user_id', '==', user_id)\
        .order_by('timestamp', direction=firestore.Query.DESCENDING)\
        .get()
    
    history = []
    for t in transactions:
        t_data = t.to_dict()
        history.append({
            'date': t_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
            'type': t_data['transaction_type'],
            'symbol': t_data['symbol'],
            'shares': t_data['shares'],
            'price': t_data['price'],
            'total': t_data['total_amount'],
            'profit_loss': round(t_data.get('profit_loss', 0.0), 2)
        })
    
    return render_template('history.html.jinja2', 
                         history=history, 
                         user=user)