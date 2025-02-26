# src/app.py
from flask import Flask
from flask_caching import Cache
from flask_htmlmin import HTMLMIN
from utils.config import Config
from routes.user import user_bp
from routes.api import api_bp
from routes.charts import charts_bp
from routes.auth import auth_bp
from routes.trading import trading_bp
from utils.db import init_db


def create_app(config_class=Config):
    app = Flask(__name__, static_folder='static')
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
    
    return app

app = create_app()


if __name__ == '__main__':
    app.run(debug=True)