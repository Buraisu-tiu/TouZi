from flask import Flask, redirect, url_for, session, jsonify
from flask_caching import Cache
from flask_htmlmin import HTMLMIN
from utils.config import Config, DevelopmentConfig
from routes.user import user_bp
from routes.charts import charts_bp
from routes.auth import auth_bp
from routes.trading import trading_bp
from routes.portfolio import portfolio_bp
from routes.leaderboard import leaderboard_bp
from routes.market import market_bp
from utils.db import init_db, db
from routes.api import api_bp
import re

cache = Cache()  # Define cache globally

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(config_class)

    # Initialize extensions
    HTMLMIN(app)
    cache.init_app(app)  # Initialize cache with Flask app ✅

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

@app.route('/documentation')
def documentation_call():
    return redirect(url_for('auth.documentation'))

@app.route('/api/theme', methods=['POST'])
def toggle_theme():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
        
    user_ref = db.collection('users').document(session['user_id'])
    user_data = user_ref.get().to_dict()
    
    # Toggle between light and dark theme
    is_dark = user_data.get('theme', 'dark') == 'dark'
    new_theme = 'light' if is_dark else 'dark'
    
    theme_colors = {
        'dark': {
            'background_color': '#0a0a0a',
            'text_color': '#ffffff',
        },
        'light': {
            'background_color': '#ffffff',
            'text_color': '#0a0a0a',
        }
    }
    
    user_ref.update({
        'theme': new_theme,
        'background_color': theme_colors[new_theme]['background_color'],
        'text_color': theme_colors[new_theme]['text_color']
    })
    
    return jsonify({
        'success': True,
        'theme': new_theme,
        'colors': theme_colors[new_theme]
    })

if __name__ == '__main__':
    app.run(debug=True)
