class Config:
    SECRET_KEY = 'your_secret_key'
    UPLOAD_FOLDER = 'static/uploads'
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    
    # Firebase configuration
    FIREBASE_PROJECT_ID = 'stock-trading-simulator-b6e27'
    
    # API configuration
    COINBASE_API_KEY = 'your_coinbase_api_key'
    COINBASE_API_SECRET = 'your_coinbase_api_secret'

    # Default cache configuration
    CACHE_TYPE = 'simple'  # Default is in-memory

class DevelopmentConfig(Config):
    DEBUG = True
    CACHE_TYPE = 'redis'
    CACHE_REDIS_HOST = 'localhost'
    CACHE_REDIS_PORT = 6379
    CACHE_REDIS_DB = 0
    CACHE_REDIS_URL = "redis://localhost:6379/0"
    CACHE_DEFAULT_TIMEOUT = 60

class ProductionConfig(Config):
    DEBUG = False
    CACHE_TYPE = 'redis'
    CACHE_REDIS_HOST = 'localhost'
    CACHE_REDIS_PORT = 6379
    CACHE_REDIS_DB = 0
    CACHE_REDIS_URL = "redis://localhost:6379/0"
    CACHE_DEFAULT_TIMEOUT = 60
