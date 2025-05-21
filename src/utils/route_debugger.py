"""
Utility to debug Flask routing issues
"""

def print_routes(app):
    """Print all registered routes in the Flask app"""
    print("\n=== REGISTERED ROUTES ===")
    for rule in sorted(app.url_map.iter_rules(), key=lambda x: str(x)):
        methods = ','.join(rule.methods)
        print(f"{rule.endpoint:30s} {methods:20s} {rule}")
    print("========================\n")
