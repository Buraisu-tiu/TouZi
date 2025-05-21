"""
Test routes for diagnosing issues with the application.
"""

from flask import Blueprint, jsonify, session, current_app
import sys
import traceback

# Set url_prefix to '' so routes are at root level
test_bp = Blueprint('test', __name__, url_prefix='')

@test_bp.route('/test-routes', methods=['GET'])
def test_all_routes():
    """Debug view that lists all registered routes."""
    try:
        routes = []
        for rule in current_app.url_map.iter_rules():
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'path': str(rule)
            })
        # Print all routes to the terminal for immediate debugging
        print("\n[TEST_ROUTES] Registered routes:")
        for r in routes:
            print(f"  {r['methods']} {r['path']} -> {r['endpoint']}")
        # Sort routes by path
        routes = sorted(routes, key=lambda x: x['path'])
        
        # Check for specific endpoints
        watchlist_routes = [r for r in routes if 'watchlist' in r['endpoint']]
        api_routes = [r for r in routes if '/api/' in r['path']]
        
        return jsonify({
            'success': True,
            'message': 'Routes diagnostic information',
            'total_routes': len(routes),
            'routes': routes,
            'watchlist_routes': watchlist_routes,
            'api_routes': api_routes,
            'session': {
                'has_user_id': 'user_id' in session,
                # Don't expose the actual user_id for security
            }
        })
    except Exception as e:
        exc_info = sys.exc_info()
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@test_bp.route('/test-watchlist', methods=['GET'])
def test_watchlist():
    """Special test endpoint for checking watchlist functionality."""
    try:
        # Check if the watchlist blueprint exists
        watchlist_blueprint_object = current_app.blueprints.get('watchlist')
        
        # Print to terminal for immediate feedback
        if watchlist_blueprint_object:
            print(f"\n[TEST_WATCHLIST] Found blueprint: 'watchlist' (Object: {watchlist_blueprint_object})")
        else:
            print("\n[TEST_WATCHLIST] Blueprint 'watchlist' NOT FOUND in current_app.blueprints.")

        # Check for watchlist routes
        watchlist_routes = []
        for rule in current_app.url_map.iter_rules():
            if 'watchlist' in rule.endpoint:
                watchlist_routes.append({
                    'endpoint': rule.endpoint,
                    'methods': list(rule.methods),
                    'path': str(rule)
                })
        
        return jsonify({
            'success': True,
            'message': 'Watchlist diagnostic information',
            'watchlist_blueprint_exists': watchlist_blueprint_object is not None,
            'watchlist_routes': watchlist_routes,
            'authentication': {
                'user_id_in_session': 'user_id' in session,
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

# Ensure this file is imported and test_bp is registered in your app.py:
# from routes.test_routes import test_bp
# app.register_blueprint(test_bp)
