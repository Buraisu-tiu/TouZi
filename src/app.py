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
from routes.watchlist import watchlist_bp
import re
import os

cache = Cache()  # Define cache globally

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(config_class)
    
    # Load API keys from different sources
    from utils.constants import api_keys
    
    # Clear existing API keys to avoid duplicates
    api_keys.clear()
    
    # First try to load from api_keys.py file (our main source now)
    try:
        import api_keys as api_keys_file
        if hasattr(api_keys_file, 'FINNHUB_API_KEYS'):
            for key in api_keys_file.FINNHUB_API_KEYS:
                if key and key not in api_keys:
                    api_keys.append(key)
            print(f"✅ Loaded {len(api_keys_file.FINNHUB_API_KEYS)} Finnhub API keys from api_keys.py")
            
            # Print the masked keys for verification
            for i, key in enumerate(api_keys):
                masked_key = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "****"
                print(f"  Key #{i+1}: {masked_key}")
    except ImportError:
        # api_keys.py doesn't exist, that's okay
        pass
    
    # As backup, check for API keys in environment
    finnhub_key = app.config.get('FINNHUB_API_KEY') or os.environ.get('FINNHUB_API_KEY')
    if finnhub_key and finnhub_key not in api_keys:
        api_keys.append(finnhub_key)
        print(f"✅ Added Finnhub API key from environment")
    
    # Log the final API key count
    print(f"✅ Total Finnhub API keys available: {len(api_keys)}")
    if not api_keys:
        print("⚠️ WARNING: No Finnhub API keys found!")
    
   # Disable template caching
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.auto_reload = True
    app.jinja_env.cache = {}

    # Initialize extensions
    HTMLMIN(app)
    # Remove caching initialization to disable caching:
    # cache.init_app(app)

    # Register blueprints
    app.register_blueprint(user_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(charts_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(trading_bp)
    app.register_blueprint(portfolio_bp)
    app.register_blueprint(leaderboard_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(watchlist_bp)  # Add this line


    return app
app = create_app()

@app.before_request
def before_request():
    g.user = None
    g.notifications = [] # Notifications will be empty as badge logic is removed
    if 'user_id' not in session:
        return
        
    try:
        user = db.collection('users').document(session['user_id']).get()
        if user.exists:
            g.user = user.to_dict()
            
            # Badge processing is already effectively removed here by setting g.notifications to []
            # and commenting out the badge fetching logic.
    except Exception as e:
        print(f"Error in before_request: {e}")
        # Allow the request to continue even if we can't set up user info

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

@app.route('/debug/template_cache')
def template_cache():
    from flask import jsonify
    # Return the list of cached template keys; if caching is disabled, this may be empty.
    cache_keys = list(app.jinja_env.cache.keys()) if app.jinja_env.cache else []
    return jsonify({'template_cache_keys': cache_keys})

@app.errorhandler(500)
def internal_server_error(e):
    # Log the error
    app.logger.error(f"Internal Server Error: {e}")
    return "500 error", 500

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__':
    app.run(debug=True)
