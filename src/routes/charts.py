# src/routes/charts.py
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
import plotly.graph_objects as go
from services.market_data import fetch_historical_data, fetch_stock_data
from utils.db import db
from utils.constants import POPULAR_STOCKS, MARKET_INDICES
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands
import logging
import traceback

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
    """Modified lookup route to use Finnhub instead of yfinance."""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    
    symbol = request.form.get('symbol', request.args.get('symbol', '')).upper().strip()
    
    if symbol:
        try:
            # Get current stock data using our fetch_stock_data function
            price_data = fetch_stock_data(symbol)
            if price_data and not price_data.get('error'):
                stock_data = {
                    'close': price_data['close'],
                    'prev_close': price_data['prev_close'],
                    'high': price_data.get('high', price_data['close']),
                    'low': price_data.get('low', price_data['close']),
                    'volume': price_data.get('volume', 0),
                    'company_name': symbol,  # Default to symbol if name not available
                }
                
                # Get historical data
                df = fetch_historical_data(symbol)
                if df is not None:
                    # Create charts with available data
                    graph_html = create_price_chart(df, symbol)
                    rsi_html = create_rsi_chart(df)
                    
                    return render_template('lookup.html.jinja2',
                                        user=user,
                                        symbol=symbol,
                                        stock_data=stock_data,
                                        graph_html=graph_html,
                                        rsi_html=rsi_html)
            else:
                return render_template('lookup.html.jinja2',
                                    user=user,
                                    error_message=f"Could not fetch data for {symbol}")
                                    
        except Exception as e:
            logging.error(f"Error in lookup: {str(e)}")
            logging.error(traceback.format_exc())
            return render_template('lookup.html.jinja2',
                                user=user,
                                error_message=f"An error occurred: {str(e)}")
    
    # Default view without symbol
    return render_template('lookup.html.jinja2',
                         user=user,
                         symbol='')

@charts_bp.route('/market-analysis')
def market_analysis():
    """Redirect to lookup which now serves as the unified market analysis page"""
    return redirect(url_for('charts.lookup'))

@charts_bp.route('/api/technical-analysis', methods=['POST'])
def get_technical_analysis():
    data = request.json
    symbol = data.get('symbol')
    timeframe = data.get('timeframe', 'D')  # D=daily, W=weekly, M=monthly
    indicators = data.get('indicators', [])
    
    # Fetch historical data
    historical_data = fetch_historical_data(symbol)
    if historical_data is None:
        return jsonify({'error': 'Failed to fetch data'})
    
    df = pd.DataFrame(historical_data)
    results = {'price_data': historical_data}
    
    # Calculate requested indicators
    if 'sma' in indicators:
        sma = SMAIndicator(df['close'], window=20)
        results['sma'] = sma.sma_indicator().tolist()
    
    if 'ema' in indicators:
        ema = EMAIndicator(df['close'], window=20)
        results['ema'] = ema.ema_indicator().tolist()
    
    if 'rsi' in indicators:
        rsi = RSIIndicator(df['close'])
        results['rsi'] = rsi.rsi().tolist()
    
    if 'macd' in indicators:
        macd = MACD(df['close'])
        results['macd_line'] = macd.macd().tolist()
        results['signal_line'] = macd.macd_signal().tolist()
    
    if 'bollinger' in indicators:
        bollinger = BollingerBands(df['close'])
        results['bollinger_high'] = bollinger.bollinger_hband().tolist()
        results['bollinger_mid'] = bollinger.bollinger_mavg().tolist()
        results['bollinger_low'] = bollinger.bollinger_lband().tolist()

    return jsonify(results)

@charts_bp.route('/api/stock-screener', methods=['POST'])
def screen_stocks():
    criteria = request.json
    results = []
    
    # Get list of stocks to screen (e.g., S&P 500 components)
    stocks = POPULAR_STOCKS  # From your constants.py
