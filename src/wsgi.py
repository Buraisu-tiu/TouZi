import sys
import os

# Add the current directory to the path so we can import app
sys.path.append(os.path.dirname(__file__))

try:
    from app import app as application
except ImportError as e:
    # Provide more helpful error messages on import failures
    import traceback
    print("=== ERROR IMPORTING APPLICATION ===")
    print(f"Error: {e}")
    print("Traceback:")
    traceback.print_exc()
    
    # Create a simple WSGI app that will display the error
    def application(environ, start_response):
        status = '500 Internal Server Error'
        headers = [('Content-type', 'text/html')]
        start_response(status, headers)
        error_msg = f"""
        <html>
            <head>
                <title>Application Import Error</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    pre {{ background: #f0f0f0; padding: 10px; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <h1>Application Import Error</h1>
                <p>There was an error importing the application:</p>
                <pre>{str(e)}</pre>
                <p>Please check the logs for more details.</p>
            </body>
        </html>
        """
        return [error_msg.encode('utf-8')]

if __name__ == "__main__":
    application.run()