class Config:
    SECRET_KEY = 'your_secret_key'
    UPLOAD_FOLDER = 'static/uploads'
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    
    # Firebase configuration
    FIREBASE_PROJECT_ID = 'stock-trading-simulator-b6e27'
    
    # API configuration
    COINBASE_API_KEY = 'your_coinbase_api_key'
    COINBASE_API_SECRET = 'your_coinbase_api_secret'

    # Default to SimpleCache as a fallback
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 60

class DevelopmentConfig(Config):
    DEBUG = True
    # Try to use Redis but will fall back to SimpleCache if not available
    CACHE_TYPE = 'RedisCache'
    CACHE_REDIS_HOST = 'localhost'
    CACHE_REDIS_PORT = 6379
    CACHE_REDIS_DB = 0
    CACHE_REDIS_URL = "redis://localhost:6379/0"
    # Add a connection timeout to fail fast if Redis is not available
    CACHE_OPTIONS = {'socket_connect_timeout': 2}

class ProductionConfig(Config):
    DEBUG = False
    CACHE_TYPE = 'RedisCache'
    CACHE_REDIS_HOST = 'localhost'
    CACHE_REDIS_PORT = 6379
    CACHE_REDIS_DB = 0
    CACHE_REDIS_URL = "redis://localhost:6379/0"
    CACHE_OPTIONS = {'socket_connect_timeout': 2}
