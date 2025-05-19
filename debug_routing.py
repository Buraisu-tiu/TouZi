"""
A diagnostic tool to debug Flask routes.
Run this file to see all registered routes in your app.
"""

from src.app import app

def debug_routes():
    print("\n==== REGISTERED ROUTES ====")
    print("{:<40} {:<20} {:<30}".format('Route', 'Methods', 'Endpoint'))
    print("-" * 90)
    
    # Get all registered rules
    rules = sorted(app.url_map.iter_rules(), key=lambda rule: str(rule))
    
    for rule in rules:
        methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        print("{:<40} {:<20} {:<30}".format(str(rule), methods, rule.endpoint))
    
    print("\n==== Trading Routes ====")
    for rule in rules:
        if 'trading' in rule.endpoint:
            methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
            print("{:<40} {:<20} {:<30}".format(str(rule), methods, rule.endpoint))
    
    print("\n==== Static Routes ====")
    for rule in rules:
        if rule.endpoint == 'static':
            print(f"Static URL: {rule}")
            print(f"Static folder: {app.static_folder}")

if __name__ == "__main__":
    debug_routes()
