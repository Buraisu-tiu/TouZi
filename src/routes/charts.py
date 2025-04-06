# src/routes/charts.py
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
import plotly.express as px
from services.market_data import fetch_historical_data, fetch_stock_data
from utils.db import db
from utils.constants import POPULAR_STOCKS
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands
import logging
import yfinance as yf

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
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    graph_html = None
    error_message = None
    stock_data = None
    rsi_html = None
    macd_html = None
    
    symbol = request.form.get('symbol', request.args.get('symbol', '')).upper().strip()
    
    # Fetch market overview data using yfinance
    market_indices = {
        'SPY': 'S&P 500',
        'DIA': 'Dow Jones',
        'QQQ': 'NASDAQ',
        'IWM': 'Russell 2000'
    }
    
    market_overview = {}
    for index, name in market_indices.items():
        try:
            ticker = yf.Ticker(index)
            hist = ticker.history(period='2d')
            if not hist.empty:
                today = hist.iloc[-1]
                yesterday = hist.iloc[-2]
                market_overview[index] = {
                    'name': name,
                    'close': float(today['Close']),
                    'prev_close': float(yesterday['Close'])
                }
        except Exception as e:
            logging.error(f"Error fetching market data for {index}: {str(e)}")
            continue
    
    if symbol:
        try:
            # Use yfinance for current stock data
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period='2d')
            
            if not hist.empty:
                today = hist.iloc[-1]
                yesterday = hist.iloc[-2]
                stock_data = {
                    'close': float(today['Close']),
                    'prev_close': float(yesterday['Close']),
                    'high': float(today['High']),
                    'low': float(today['Low']),
                    'volume': int(today['Volume'])
                }
                
                # Fetch historical data for the graph
                df = fetch_historical_data(symbol)
                if df is not None and len(df) > 0:
                    try:
                        # Calculate technical indicators
                        sma20 = SMAIndicator(df['close'], window=20).sma_indicator()
                        ema20 = EMAIndicator(df['close'], window=20).ema_indicator()
                        rsi = RSIIndicator(df['close']).rsi()
                        macd = MACD(df['close'])
                        bb = BollingerBands(df['close'])

                        # Create the main price chart with increased size
                        fig = px.line(df, x=df.index, y='close', 
                                    title=f'{symbol} Price History with Technical Indicators')
                        
                        # Add technical indicators only if they contain valid data
                        if not sma20.isnull().all():
                            fig.add_scatter(x=df.index, y=sma20, name='SMA 20', 
                                         line=dict(color='blue', width=1))
                        if not ema20.isnull().all():
                            fig.add_scatter(x=df.index, y=ema20, name='EMA 20', 
                                         line=dict(color='orange', width=1))
                        
                        bb_high = bb.bollinger_hband()
                        bb_low = bb.bollinger_lband()
                        if not bb_high.isnull().all() and not bb_low.isnull().all():
                            fig.add_scatter(x=df.index, y=bb_high, name='BB Upper',
                                         line=dict(color='gray', width=1, dash='dash'))
                            fig.add_scatter(x=df.index, y=bb_low, name='BB Lower',
                                         line=dict(color='gray', width=1, dash='dash'))

                        # Update layout with larger size and improved visibility
                        fig.update_layout(
                            height=600,  # Increase height
                            template='plotly_dark',
                            plot_bgcolor='rgba(0, 0, 0, 0)',
                            paper_bgcolor='rgba(0, 0, 0, 0)',
                            font=dict(color='white', size=12),
                            xaxis=dict(
                                gridcolor='rgba(128, 128, 128, 0.2)',
                                title_font=dict(size=14),
                                tickfont=dict(size=12),
                                title='Date',
                                showgrid=True
                            ),
                            yaxis=dict(
                                gridcolor='rgba(128, 128, 128, 0.2)',
                                title_font=dict(size=14),
                                tickfont=dict(size=12),
                                title='Price ($)',
                                showgrid=True
                            ),
                            margin=dict(t=50, l=50, r=20, b=50),
                            showlegend=True,
                            legend=dict(
                                yanchor="top",
                                y=0.99,
                                xanchor="left",
                                x=0.01,
                                bgcolor='rgba(0,0,0,0.5)'
                            )
                        )

                        # Create RSI and MACD charts only if they contain valid data
                        if not rsi.isnull().all():
                            rsi_fig = px.line(x=df.index, y=rsi, title='RSI')
                            rsi_fig.add_hline(y=70, line_color='red', line_dash='dash')
                            rsi_fig.add_hline(y=30, line_color='green', line_dash='dash')
                            rsi_fig.update_layout(
                                template='plotly_dark',
                                plot_bgcolor='rgba(0, 0, 0, 0)',
                                paper_bgcolor='rgba(0, 0, 0, 0)',
                                height=200,
                                margin=dict(t=30, l=50, r=20, b=20)
                            )
                            rsi_html = rsi_fig.to_html(full_html=False, config={'displayModeBar': False})

                        if not macd.macd().isnull().all():
                            macd_fig = px.line(x=df.index, y=macd.macd(), title='MACD')
                            macd_fig.add_scatter(x=df.index, y=macd.macd_signal(), name='Signal')
                            macd_fig.update_layout(
                                template='plotly_dark',
                                plot_bgcolor='rgba(0, 0, 0, 0)',
                                paper_bgcolor='rgba(0, 0, 0, 0)',
                                height=200,
                                margin=dict(t=30, l=50, r=20, b=20)
                            )
                            macd_html = macd_fig.to_html(full_html=False, config={'displayModeBar': False})

                        graph_html = fig.to_html(full_html=False, config={'displayModeBar': True})
                        
                    except Exception as e:
                        logging.error(f"Error calculating indicators: {str(e)}")
                        error_message = "Error calculating technical indicators"
                else:
                    error_message = "Unable to fetch historical data for this symbol"
            else:
                error_message = f"No data available for {symbol}"
                
        except Exception as e:
            logging.error(f"Error in lookup: {str(e)}")
            error_message = f"An error occurred: {str(e)}"
    
    return render_template('lookup.html.jinja2', 
                         user=user,
                         graph_html=graph_html,
                         rsi_html=rsi_html,
                         macd_html=macd_html,
                         error_message=error_message,
                         symbol=symbol,
                         stock_data=stock_data,
                         market_overview=market_overview)

@charts_bp.route('/market-analysis')
def market_analysis():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    
    # Fetch market overview data
    market_indices = ['SPY', 'DIA', 'QQQ', 'IWM']  # S&P 500, Dow, Nasdaq, Russell 2000
    market_overview = {
        index: fetch_stock_data(index)
        for index in market_indices
    }
    
    # Fetch sector performance
    sectors = {
        'XLK': 'Technology',
        'XLF': 'Financial',
        'XLV': 'Healthcare',
        'XLE': 'Energy',
        'XLI': 'Industrial'
    }
    sector_performance = {
        name: fetch_stock_data(symbol)
        for symbol, name in sectors.items()
    }
    
    return render_template('market_analysis.html.jinja2',
                         user=user,
                         market_overview=market_overview,
                         sector_performance=sector_performance)

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
