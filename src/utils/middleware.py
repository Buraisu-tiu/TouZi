"""
Middleware utilities for Flask application
"""
from flask import request, g
import time

class RequestDebugger:
    """Middleware to debug request flow"""
    
    def __init__(self, app):
        self.app = app
        self.app.before_request(self.before_request)
        self.app.after_request(self.after_request)
    
    def before_request(self):
        """Log before each request"""
        g.start_time = time.time()
        print(f"[REQUEST] {request.method} {request.path} started")
        print(f"[REQUEST] Referrer: {request.referrer}")
        print(f"[REQUEST] Args: {request.args}")
    
    def after_request(self, response):
        """Log after each request"""
        duration = time.time() - g.start_time
        print(f"[RESPONSE] {request.method} {request.path} -> {response.status_code} ({duration:.4f}s)")
        if response.status_code >= 300 and response.status_code < 400:
            print(f"[REDIRECT] Redirecting to: {response.location}")
        return response
