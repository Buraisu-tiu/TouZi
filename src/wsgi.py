import os
import sys

# Add the src directory to the Python path so that imports work correctly
sys.path.insert(0, os.path.dirname(__file__))

# Import the application object
from app import app as application

# Create a variable named 'app' that Gunicorn will look for
app = application

if __name__ == "__main__":
    application.run()