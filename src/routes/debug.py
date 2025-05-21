# Debug routes for troubleshooting and diagnostics
import json
import traceback
import sys
from datetime import datetime
from flask import Blueprint, request, jsonify, session, current_app, url_for
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('debug_routes')

debug_bp = Blueprint('debug', __name__)
print(f"[DEBUG MODULE] Initializing debug blueprint at {datetime.now()}")

@debug_bp.route('/api/debug/watchlist', methods=['POST'])
def debug_watchlist():
    """Endpoint for logging watchlist debugging information"""
    try:
        data = request.json
        
        # Log detailed debugging information
        logger.error("\n" + "="*80)
        logger.error("[WATCHLIST DEBUG] Client-side error report received")
        logger.error(f"Timestamp: {datetime.now().isoformat()}")
        logger.error(f"User ID: {session.get('user_id', 'Not authenticated')}")
        logger.error(f"Symbol: {data.get('symbol', 'Not provided')}")
        logger.error(f"Endpoint: {data.get('endpoint', 'Not provided')}")
        logger.error(f"Error: {data.get('error', 'Not provided')}")
        logger.error(f"Status: {data.get('status', 'Not provided')}")
        logger.error(f"User Agent: {data.get('userAgent', 'Not provided')}")
        
        # Log error text if available
        if 'errorText' in data:
            logger.error(f"Error Text: {data.get('errorText')}")
            
        # Log request environment details
        logger.error("\nRequest Environment Details:")
        logger.error(f"Request Method: {request.method}")
        logger.error(f"Request Path: {request.path}")
        logger.error(f"Request Headers: {dict(request.headers)}")
        logger.error(f"Client IP: {request.remote_addr}")
        
        # Log server configuration details
        logger.error("\nServer Configuration Details:")
        logger.error(f"Registered Blueprints: {list(current_app.blueprints.keys())}")
        logger.error(f"URL Map:")
        for rule in current_app.url_map.iter_rules():
            logger.error(f"  {rule.endpoint}: {rule}")
        
        logger.error("="*80 + "\n")
        
        return jsonify({"status": "debug data received"})
    except Exception as e:
        logger.error(f"Exception in debug endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500

@debug_bp.route('/debug/routes')
def list_routes():
    """Display all registered routes for debugging"""
    routes = []
    for rule in current_app.url_map.iter_rules():
        methods = ','.join(sorted(rule.methods))
        routes.append({
            'endpoint': rule.endpoint,
            'methods': methods,
            'path': str(rule),
        })
    
    # Sort routes by path
    routes = sorted(routes, key=lambda x: x['path'])
    
    # Format as HTML
    html = "<h1>Registered Routes</h1>"
    html += "<table border='1'><tr><th>Path</th><th>Endpoint</th><th>Methods</th></tr>"
    for route in routes:
        html += f"<tr><td>{route['path']}</td><td>{route['endpoint']}</td><td>{route['methods']}</td></tr>"
    html += "</table>"
    
    return html

print(f"[DEBUG MODULE] Registered routes:")
print(f"[DEBUG MODULE] - /api/debug/watchlist (POST)")
print(f"[DEBUG MODULE] - /debug/routes (GET)")
