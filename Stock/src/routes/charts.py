# src/routes/charts.py
from flask import Blueprint, render_template, session, redirect, url_for, request
import plotly.express as px
from ..services.market_data import fetch_historical_data, fetch_stock_data
from ..utils.db import db
from datetime import datetime
import logging

charts_bp = Blueprint('charts', __name__)

@charts_bp.route('/plot/<symbol>', methods=['GET'])
def plot(symbol):
    df = fetch_historical_data(symbol)
    if df is not None:
        fig = px.line(df, x=df.index, y='close', 
                     title=f'Recent Price Changes for {symbol}')
        fig.update_layout(
            xaxis_title='Date',
            yaxis_title='Close Price',
            template='plotly_dark',
            plot_bgcolor='rgba(0, 0, 0, 0)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            font=dict(color='white'),
            xaxis=dict(gridcolor='gray'),
            yaxis=dict(gridcolor='gray')
        )

        graph_html = fig.to_html(full_html=False)

        # Store the plot data
        plot_ref = db.collection('plots').document(symbol)
        if not plot_ref.get().exists:
            plot_ref.set({
                'symbol': symbol,
                'graph_html': graph_html,
                'timestamp': datetime.utcnow()
            })

        return render_template('plot.html.jinja2', 
                             graph_html=graph_html, 
                             symbol=symbol)
    return "Failed to fetch stock data."

@charts_bp.route('/lookup', methods=['GET', 'POST'])
def lookup():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    graph_html = None
    error_message = None
    stock_data = None
    
    # Get symbol from either POST data or URL parameters
    symbol = request.form.get('symbol', request.args.get('symbol', '')).upper().strip()
    
    if symbol:
        try:
            # Fetch current stock data
            stock_data = fetch_stock_data(symbol)
            if 'error' in stock_data:
                error_message = stock_data['error']
            else:
                # Fetch historical data for the graph
                df = fetch_historical_data(symbol)
                if df is not None:
                    fig = px.line(df, x=df.index, y='close', 
                                title=f'{symbol} Price History (Last 30 Days)',
                                labels={'close': 'Price ($)', 'index': 'Date'})
                    
                    # Customize the graph appearance
                    fig.update_layout(
                        template='plotly_dark',
                        plot_bgcolor='rgba(0, 0, 0, 0)',
                        paper_bgcolor='rgba(0, 0, 0, 0)',
                        font=dict(color='white'),
                        xaxis=dict(
                            gridcolor='rgba(128, 128, 128, 0.2)',
                            title_font=dict(size=14),
                            tickfont=dict(size=12),
                            title='Date'
                        ),
                        yaxis=dict(
                            gridcolor='rgba(128, 128, 128, 0.2)',
                            title_font=dict(size=14),
                            tickfont=dict(size=12),
                            title='Price ($)'
                        ),
                        title=dict(
                            font=dict(size=16)
                        ),
                        margin=dict(t=50, l=50, r=20, b=50)
                    )
                    
                    graph_html = fig.to_html(full_html=False, config={'displayModeBar': True})
                else:
                    error_message = "Unable to fetch historical data for this symbol"
        except Exception as e:
            logging.error(f"An error occurred: {str(e)}")
            error_message = f"An error occurred: {str(e)}"
    else:
        error_message = "No stock symbol provided"
    
    return render_template('lookup.html.jinja2', 
                         user=user,
                         graph_html=graph_html, 
                         error_message=error_message,
                         symbol=symbol,
                         stock_data=stock_data)
