# src/utils/config.py
import os

class Config:
    SECRET_KEY = 'your_secret_key'
    UPLOAD_FOLDER = 'static/uploads'
    CACHE_TYPE = 'simple'
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    
    # Firebase configuration
    FIREBASE_PROJECT_ID = 'stock-trading-simulator-b6e27'
    
    # API configuration
    COINBASE_API_KEY = 'your_coinbase_api_key'
    COINBASE_API_SECRET = 'your_coinbase_api_secret'

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False