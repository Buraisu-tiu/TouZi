from flask import Flask, redirect, url_for, session, jsonify, flash as original_flash, g, request
from flask_caching import Cache
from flask_htmlmin import HTMLMIN
from utils.config import Config, DevelopmentConfig # Assuming DevelopmentConfig is the one you want
from utils.db import db # Assuming db is initialized elsewhere or via init_db
import re
import os
import traceback

# Import all blueprints
from routes.auth import auth_bp
from routes.user import user_bp
from routes.trading import trading_bp
from routes.portfolio import portfolio_bp
from routes.leaderboard import leaderboard_bp
from routes.market import market_bp
from routes.api import api_bp
from routes.charts import charts_bp # Make sure this is used or remove
from routes.watchlist import watchlist_bp
from routes.debug import debug_bp
from routes.test_routes import test_bp

from utils.route_debugger import print_routes
from utils.middleware import RequestDebugger # Assuming this is correctly set up

cache = Cache()

def create_app(config_class=DevelopmentConfig):
    print("--- CREATING FLASK APP (app.py) ---")
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.config.from_object(config_class)
    
    # Initialize database if needed here, e.g., init_db(app)
    # For now, assuming 'db' from 'utils.db' is ready to use.

    # API Key Loading (ensure this doesn't break if api_keys.py is missing)
    try:
        from utils.constants import api_keys
        api_keys.clear() # Clear if re-populating
        import api_keys as api_keys_file
        if hasattr(api_keys_file, 'FINNHUB_API_KEYS'):
            for key in api_keys_file.FINNHUB_API_KEYS:
                if key and key not in api_keys:
                    api_keys.append(key)
            print(f"✅ Loaded {len(api_keys_file.FINNHUB_API_KEYS)} keys from api_keys.py")
    except ImportError:
        print("⚠️ api_keys.py not found or error loading keys from it.")
    except Exception as e:
        print(f"⚠️ Error during API key loading: {e}")
    # ... rest of your API key logic ...

    # Template settings
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.jinja_env.auto_reload = True
    app.jinja_env.cache = {} # Disable Jinja2 cache for development

    # Initialize extensions
    HTMLMIN(app)
    # cache.init_app(app) # Caching is commented out

    # Initialize RequestDebugger
    if RequestDebugger: # Check if it's not None
        RequestDebugger(app)

    # Register all blueprints
    print("\n----- REGISTERING BLUEPRINTS -----")
    blueprints_to_register = [
        (auth_bp, "auth_bp"), (user_bp, "user_bp"), (trading_bp, "trading_bp"),
        (watchlist_bp, "watchlist_bp"), (debug_bp, "debug_bp"), (test_bp, "test_bp"),
        (api_bp, "api_bp"), (charts_bp, "charts_bp"), (portfolio_bp, "portfolio_bp"),
        (leaderboard_bp, "leaderboard_bp"), (market_bp, "market_bp")
    ]

    for bp, name in blueprints_to_register:
        try:
            if bp: # Check if the blueprint object exists
                app.register_blueprint(bp)
                print(f"✅ Successfully registered blueprint: {name} (Object: {bp.name})")
            else:
                print(f"⚠️ Blueprint '{name}' is None, skipping registration.")
        except Exception as e:
            print(f"❌ ERROR registering blueprint '{name}': {e}")
            print(traceback.format_exc())
    
    print("----- BLUEPRINT REGISTRATION COMPLETE -----\n")

    return app

app = create_app() # Create the app instance

# --- App-level handlers and context processors ---
@app.before_request
def app_before_request():
    print(f"[DEBUG] Request: {request.method} {request.path} - Referrer: {request.referrer}")
    g.user = None
    g.notifications = []
    if 'user_id' in session:
        try:
            user_doc = db.collection('users').document(session['user_id']).get()
            if user_doc.exists:
                g.user = user_doc.to_dict()
        except Exception as e:
            print(f"Error in app_before_request loading user: {e}")

@app.context_processor
def inject_global_vars():
    return {'user': getattr(g, 'user', None), 'notifications': getattr(g, 'notifications', [])}

def custom_flash_function(message, category='message'):
    print(f"FLASH [{category.upper()}]: {message}")
    original_flash(message, category)

app.jinja_env.globals['flash'] = custom_flash_function

def hex_to_rgb_filter_func(hex_color):
    hex_color = hex_color.lstrip('#')
    if not re.match(r'^[0-9A-Fa-f]{6}$', hex_color):
        return "0, 0, 0"
    r_val, g_val, b_val = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f"{r_val}, {g_val}, {b_val}"

app.jinja_env.filters['hex_to_rgb'] = hex_to_rgb_filter_func

@app.route('/')
def index():
    """Root route handler - automatically logout and redirect to login"""
    session.clear()  # Clear any existing session
    return redirect(url_for('auth.login'))

# ... other app-level routes like /documentation, /api/theme ...

@app.errorhandler(500)
def handle_internal_server_error(e):
    app.logger.error(f"Internal Server Error: {e}")
    print(traceback.format_exc()) # Crucial for debugging 500 errors
    return "An internal server error occurred. Please check the logs.", 500

@app.after_request
def add_no_cache_headers_after_request(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.before_request
def check_authentication():
    """Clear session if trying to access protected routes while not properly authenticated"""
    public_routes = ['auth.login', 'auth.register', 'static']
    
    if not request.endpoint or request.endpoint.startswith('auth.'):
        session.clear()  # Always clear session on auth routes
        return
        
    if 'user_id' not in session and request.endpoint not in public_routes:
        session.clear()
        return redirect(url_for('auth.login'))

# Print routes after app creation and all blueprint registrations
if app: # Ensure app object exists
    print_routes(app)
else:
    print("⚠️ Flask app object not created. Cannot print routes.")

if __name__ == '__main__':
    # Set use_reloader=False to avoid duplicate print statements from Flask's reloader
    # and to ensure startup errors are clearly visible.
    app.run(debug=True, use_reloader=False)
