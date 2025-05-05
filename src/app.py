from flask import Flask, redirect, url_for, session, jsonify, flash as original_flash, g
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
from services.badge_services import fetch_user_badges, ACHIEVEMENTS

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

@app.before_request
def before_request():
    g.user = None
    g.notifications = []
    if 'user_id' in session:
        user = db.collection('users').document(session['user_id']).get()
        if user.exists:
            g.user = user.to_dict()
            
            # Fetch user badges and format them as notifications
            badges = fetch_user_badges(session['user_id'])
            g.notifications = [{
                'type': 'badge_earned',
                'badge_name': badge['name'],
                'badge_description': badge['description'],
                'badge_icon': ACHIEVEMENTS[badge['badge_id']]['icon']
            } for badge in badges]

@app.context_processor
def inject_template_vars():
    return {
        'user': g.user,
        'notifications': g.notifications
    }

# Custom flash function
def flash(message, category='message'):
    """Custom flash function to log notifications to the terminal."""
    print(f"[{category.upper()}] {message}")  # Log to the terminal
    original_flash(message, category)

# Replace the default flash function with the custom one
app.jinja_env.globals['flash'] = flash

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

@app.errorhandler(500)
def internal_server_error(e):
    # Log the error
    app.logger.error(f"Internal Server Error: {e}")
    return "500 error", 500

if __name__ == '__main__':
    app.run(debug=True)
