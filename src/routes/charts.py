# src/routes/charts.py
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify
import plotly.express as px
import plotly.graph_objects as go
from services.market_data import fetch_historical_data, fetch_stock_data
from utils.db import db
from utils.constants import POPULAR_STOCKS, MARKET_INDICES
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import VolumeWeightedAveragePrice
import logging
import yfinance as yf
import random

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
    volume_html = None
    company_news = None
    related_stocks = None
    
    # Check if market is open (simple approximation)
    now = datetime.now()
    market_is_open = (
        now.weekday() < 5 and  # Monday-Friday
        9 <= now.hour < 16 and  # 9am-4pm
        not (now.hour == 9 and now.minute < 30)  # After 9:30am
    )
    
    symbol = request.form.get('symbol', request.args.get('symbol', '')).upper().strip()
    
    # Get filter parameters
    sector_filter = request.args.get('sector', '')
    market_cap_filter = request.args.get('market_cap', '')
    exchange_filter = request.args.get('exchange', '')
    
    # Get market overview data directly from APIs
    market_overview = {}
    try:
        for index, name in MARKET_INDICES.items():
            try:
                # Use our fetch_stock_data which tries multiple sources
                data = fetch_stock_data(index)
                if 'error' not in data:
                    market_overview[index] = {
                        'name': name,
                        'close': data['close'],
                        'prev_close': data['prev_close'],
                        'change': ((data['close'] - data['prev_close']) / data['prev_close'] * 100) if data['prev_close'] > 0 else 0
                    }
            except Exception as e:
                logging.error(f"Error fetching market data for {index}: {str(e)}")
                # Skip this index if we can't get data - no mock data
                continue
    except Exception as e:
        logging.error(f"Error fetching market overview: {str(e)}")
    
    # Get real market data for gainers, losers, and volume leaders
    gainers = []
    losers = []
    volume_leaders = []
    
    try:
        # Use more reliable data source for popular stocks
        sample_tickers = POPULAR_STOCKS[:20]  # Take a subset to avoid rate limits
        
        for stock in sample_tickers:
            ticker = stock["symbol"]
            try:
                # Use fetch_stock_data which tries multiple sources
                price_data = fetch_stock_data(ticker)
                if 'error' not in price_data:
                    current_price = price_data['close']
                    prev_price = price_data['prev_close']
                    change_pct = ((current_price - prev_price) / prev_price * 100) if prev_price > 0 else 0
                    
                    # Fetch recent volume from yfinance (can't avoid this API call)
                    try:
                        ticker_data = yf.Ticker(ticker)
                        hist = ticker_data.history(period='1d')
                        volume = int(hist['Volume'].iloc[-1]) if not hist.empty else 0
                    except Exception:
                        volume = 0
                    
                    stock_info = {
                        'symbol': ticker,
                        'name': stock["name"],
                        'price': current_price,
                        'change_pct': change_pct,
                        'volume': volume
                    }
                    
                    # Add to appropriate list
                    if change_pct > 0:
                        gainers.append(stock_info)
                    else:
                        losers.append(stock_info)
                    
                    # Add to volume leaders
                    volume_leaders.append(stock_info)
            except Exception as e:
                logging.error(f"Error processing {ticker}: {str(e)}")
                continue
        
        # Sort and limit
        if gainers:
            gainers = sorted(gainers, key=lambda x: x['change_pct'], reverse=True)[:5]
        if losers:
            losers = sorted(losers, key=lambda x: x['change_pct'])[:5]
        if volume_leaders:
            volume_leaders = sorted(volume_leaders, key=lambda x: x['volume'], reverse=True)[:5]
    except Exception as e:
        logging.error(f"Error getting market movers: {str(e)}")
    
    # Get sector performance
    sector_performance = {}
    sector_etfs = {
        'Technology': 'XLK',
        'Healthcare': 'XLV',
        'Financial': 'XLF',
        'Consumer Discretionary': 'XLY',
        'Consumer Staples': 'XLP',
        'Energy': 'XLE',
        'Utilities': 'XLU',
        'Materials': 'XLB',
        'Industrial': 'XLI',
        'Real Estate': 'XLRE',
        'Communication': 'XLC'
    }
    
    for sector, etf in sector_etfs.items():
        try:
            ticker = yf.Ticker(etf)
            hist = ticker.history(period='2d')
            
            if len(hist) >= 2:
                today = hist.iloc[-1]
                yesterday = hist.iloc[-2]
                change_pct = ((float(today['Close']) - float(yesterday['Close'])) / float(yesterday['Close'])) * 100
                
                sector_performance[sector] = {
                    'symbol': etf,
                    'price': float(today['Close']),
                    'change_pct': change_pct
                }
        except Exception as e:
            continue
    
    # Sort sectors by performance
    sector_performance = dict(sorted(
        sector_performance.items(), 
        key=lambda item: item[1]['change_pct'], 
        reverse=True
    ))
    
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
                    'volume': int(today['Volume']),
                    'market_cap': info.get('marketCap'),
                    'sector': info.get('sector'),
                    'industry': info.get('industry'),
                    'long_business_summary': info.get('longBusinessSummary'),
                    'year_high': info.get('fiftyTwoWeekHigh'),
                    'year_low': info.get('fiftyTwoWeekLow'),
                    'forward_pe': info.get('forwardPE'),
                    'dividend_yield': info.get('dividendYield'),
                    'ex_dividend_date': info.get('exDividendDate'),
                    'beta': info.get('beta'),
                    'eps': info.get('trailingEPS'),
                    'target_price': info.get('targetMeanPrice'),
                    'recommendation': info.get('recommendationKey', 'N/A').upper(),
                    'company_name': info.get('shortName', symbol)
                }
                
                # Calculate recommendation color
                rec_map = {
                    'STRONG_BUY': '#4CAF50',  # Green
                    'BUY': '#8BC34A',         # Light green
                    'HOLD': '#FFC107',        # Yellow
                    'UNDERPERFORM': '#FF9800', # Orange
                    'SELL': '#F44336'          # Red
                }
                stock_data['recommendation_color'] = rec_map.get(stock_data['recommendation'], '#9E9E9E')
                
                # Get recent news
                try:
                    news = ticker.news[:5]
                    company_news = [{
                        'title': item.get('title'),
                        'publisher': item.get('publisher'),
                        'link': item.get('link'),
                        'timestamp': datetime.fromtimestamp(item.get('providerPublishTime', 0)),
                        'thumbnail': item.get('thumbnail', {}).get('resolutions', [{}])[0].get('url', '')
                    } for item in news]
                except Exception as e:
                    logging.error(f"Error fetching news: {str(e)}")
                
                # Get related stocks in the same industry
                try:
                    industry = stock_data.get('industry')
                    if industry:
                        related = []
                        for stock in POPULAR_STOCKS:
                            try:
                                if stock["symbol"] != symbol:
                                    related_ticker = yf.Ticker(stock["symbol"])
                                    related_info = related_ticker.info
                                    if related_info.get('industry') == industry:
                                        related.append({
                                            'symbol': stock["symbol"],
                                            'name': stock["name"]
                                        })
                                        if len(related) >= 5:  # Limit to 5 related stocks
                                            break
                            except Exception:
                                continue
                        related_stocks = related
                except Exception as e:
                    logging.error(f"Error fetching related stocks: {str(e)}")
                
                # Fetch historical data for the graph
                df = fetch_historical_data(symbol)
                if df is not None and len(df) > 0:
                    try:
                        # Calculate technical indicators
                        # Price chart with volume
                        fig = go.Figure()
                        
                        # Add candlestick chart
                        fig.add_trace(go.Candlestick(
                            x=df.index,
                            open=df['open'], 
                            high=df['high'],
                            low=df['low'], 
                            close=df['close'],
                            name='Price'
                        ))
                        
                        # Add volume bars as a secondary y-axis
                        fig.add_trace(go.Bar(
                            x=df.index,
                            y=df['volume'],
                            name='Volume',
                            marker={
                                'color': 'rgba(100, 100, 100, 0.3)',
                            },
                            yaxis='y2'
                        ))
                        
                        # Calculate moving averages
                        sma50 = SMAIndicator(df['close'], window=50).sma_indicator()
                        sma200 = SMAIndicator(df['close'], window=200).sma_indicator()
                        
                        # Add moving averages
                        fig.add_trace(go.Scatter(
                            x=df.index, 
                            y=sma50, 
                            name='SMA 50', 
                            line=dict(color='blue', width=1)
                        ))
                        
                        fig.add_trace(go.Scatter(
                            x=df.index, 
                            y=sma200, 
                            name='SMA 200', 
                            line=dict(color='red', width=1)
                        ))
                            
                        # Setup the layout with two y-axes
                        fig.update_layout(
                            title=f'{symbol} - {stock_data["company_name"]} Price History',
                            yaxis_title='Price',
                            xaxis_title='Date',
                            template='plotly_dark',
                            height=600,
                            xaxis_rangeslider_visible=False,
                            plot_bgcolor='rgba(0, 0, 0, 0)',
                            paper_bgcolor='rgba(0, 0, 0, 0)',
                            font=dict(color='rgba(255, 255, 255, 0.8)'),
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1
                            ),
                            yaxis2=dict(
                                title='Volume',
                                titlefont=dict(color='rgba(100, 100, 100, 0.8)'),
                                tickfont=dict(color='rgba(100, 100, 100, 0.8)'),
                                overlaying='y',
                                side='right',
                                showgrid=False
                            ),
                            margin=dict(l=50, r=50, t=80, b=50)
                        )
                        
                        graph_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
                        
                        # RSI Chart
                        rsi = RSIIndicator(df['close']).rsi()
                        
                        rsi_fig = go.Figure()
                        rsi_fig.add_trace(go.Scatter(
                            x=df.index, 
                            y=rsi, 
                            mode='lines', 
                            name='RSI',
                            line=dict(color='purple', width=1.5)
                        ))
                        
                        # Add horizontal lines for overbought and oversold levels
                        rsi_fig.add_shape(
                            type="line", line_color="red", line_dash="dash",
                            x0=df.index[0], x1=df.index[-1], y0=70, y1=70
                        )
                        rsi_fig.add_shape(
                            type="line", line_color="green", line_dash="dash",
                            x0=df.index[0], x1=df.index[-1], y0=30, y1=30
                        )
                        
                        rsi_fig.update_layout(
                            title='Relative Strength Index (RSI)',
                            height=250,
                            template='plotly_dark',
                            plot_bgcolor='rgba(0, 0, 0, 0)',
                            paper_bgcolor='rgba(0, 0, 0, 0)',
                            yaxis=dict(range=[0, 100]),
                            margin=dict(l=50, r=20, t=50, b=20)
                        )
                        
                        rsi_html = rsi_fig.to_html(full_html=False, include_plotlyjs=False)
                        
                        # MACD Chart
                        macd = MACD(df['close'])
                        
                        macd_fig = go.Figure()
                        
                        # MACD line
                        macd_fig.add_trace(go.Scatter(
                            x=df.index, 
                            y=macd.macd(), 
                            mode='lines',
                            name='MACD',
                            line=dict(color='blue', width=1.5)
                        ))
                        
                        # Signal line
                        macd_fig.add_trace(go.Scatter(
                            x=df.index, 
                            y=macd.macd_signal(), 
                            mode='lines',
                            name='Signal',
                            line=dict(color='red', width=1.5)
                        ))
                        
                        # MACD Histogram
                        macd_hist = macd.macd() - macd.macd_signal()
                        colors = ['green' if val >= 0 else 'red' for val in macd_hist]
                        
                        macd_fig.add_trace(go.Bar(
                            x=df.index, 
                            y=macd_hist,
                            name='Histogram',
                            marker_color=colors
                        ))
                        
                        macd_fig.update_layout(
                            title='Moving Average Convergence Divergence (MACD)',
                            height=250,
                            template='plotly_dark',
                            plot_bgcolor='rgba(0, 0, 0, 0)',
                            paper_bgcolor='rgba(0, 0, 0, 0)',
                            margin=dict(l=50, r=20, t=50, b=20)
                        )
                        
                        macd_html = macd_fig.to_html(full_html=False, include_plotlyjs=False)
                        
                        # Volume Analysis Chart
                        vwap = VolumeWeightedAveragePrice(
                            high=df['high'], 
                            low=df['low'], 
                            close=df['close'], 
                            volume=df['volume']
                        )
                        
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
    
    # Check if this is an API request, return JSON if it is
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': error_message is None,
            'error': error_message,
            'stock_data': stock_data,
            'graphs': {
                'main': graph_html,
                'rsi': rsi_html,
                'macd': macd_html,
                'volume': volume_html
            },
            'news': company_news,
            'related_stocks': related_stocks,
            'market_overview': market_overview,
            'gainers': gainers,
            'losers': losers,
            'volume_leaders': volume_leaders,
            'sector_performance': sector_performance,
            'market_is_open': market_is_open
        })
    
    return render_template('lookup.html.jinja2', 
                         user=user,
                         graph_html=graph_html,
                         rsi_html=rsi_html,
                         macd_html=macd_html,
                         volume_html=volume_html,
                         error_message=error_message,
                         symbol=symbol,
                         stock_data=stock_data,
                         market_overview=market_overview,
                         gainers=gainers,
                         losers=losers,
                         volume_leaders=volume_leaders,
                         company_news=company_news,
                         related_stocks=related_stocks,
                         sector_performance=sector_performance,
                         market_is_open=market_is_open,
                         page_title=f"{symbol} Stock Analysis" if symbol else "Market Lookup")

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
