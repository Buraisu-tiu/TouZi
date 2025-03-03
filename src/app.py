from flask import Flask, redirect, url_for
from flask_caching import Cache
from flask_htmlmin import HTMLMIN
from utils.config import Config 
from routes.user import user_bp
from routes.charts import charts_bp
from routes.auth import auth_bp
from routes.trading import trading_bp
from routes.portfolio import portfolio_bp
from routes.leaderboard import leaderboard_bp
from routes.market import market_bp
from utils.db import init_db
from routes.api import api_bp
import re

cache = Cache()  # Define cache globally



def create_app(config_class=Config):
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(config_class)

    # Configure Redis cache
    app.config["CACHE_TYPE"] = "redis"
    app.config["CACHE_REDIS_HOST"] = "localhost"
    app.config["CACHE_REDIS_PORT"] = 6379
    app.config["CACHE_REDIS_DB"] = 0
    app.config["CACHE_REDIS_URL"] = "redis://localhost:6379/0"
    app.config["CACHE_DEFAULT_TIMEOUT"] = 60

    # Initialize extensions
    HTMLMIN(app)
    cache.init_app(app)  # Initialize cache properly

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


# Define hex_to_rgb filter
def hex_to_rgb(hex_color):
    """Convert a hex color (e.g., #007bff) to an RGB tuple (0, 123, 255)."""
    hex_color = hex_color.lstrip('#')  # Remove '#' if present
    if not re.match(r'^[0-9A-Fa-f]{6}$', hex_color):
        return "0, 0, 0"  # Return black (fail-safe) if invalid
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f"{r}, {g}, {b}"

# Register filter with Jinja2
app.jinja_env.filters['hex_to_rgb'] = hex_to_rgb

@app.route('/')
def home():
    return redirect(url_for('auth.login'))

app.route('/documentation')
def documentation_call():
    return redirect(url_for('auth.documentation'))

if __name__ == '__main__':
    app.run(debug=True)
