# src/app.py
from flask import Flask, redirect, url_for
from flask_caching import Cache
from flask_htmlmin import HTMLMIN
from utils.config import Config
from routes.user import user_bp
from routes.api import api_bp
from routes.charts import charts_bp
from routes.auth import auth_bp
from routes.trading import trading_bp
from routes.portfolio import portfolio_bp
from routes.leaderboard import leaderboard_bp
from routes.market import market_bp
from utils.db import init_db
from routes.auth import login 
import os

def create_app(config_class=Config):
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(config_class)
    
    # Initialize extensions
    HTMLMIN(app)
    Cache(app)
    
    # Register blueprints
    app.register_blueprint(user_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(charts_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(trading_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(leaderboard_bp)
    app.register_blueprint(market_bp)

    return app

app = create_app()


@app.route('/')
def home():
    return redirect(url_for('auth.login'))


if __name__ == '__main__':
    app.run(debug=True)