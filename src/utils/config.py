import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default_development_key')
    UPLOAD_FOLDER = 'static/uploads'
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    
    # Firebase configuration
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID', 'stock-trading-simulator-b6e27')
    
    # API configuration - Load from environment variables for security
    FINNHUB_API_KEY = os.environ.get('FINNHUB_API_KEY')
    ALPHA_VANTAGE_KEY = os.environ.get('ALPHA_VANTAGE_KEY')
    ALPHA_VANTAGE_BACKUP_KEY = os.environ.get('ALPHA_VANTAGE_BACKUP_KEY')

    # Default cache configuration
    CACHE_TYPE = 'null'  # Disable caching by default
    CACHE_DURATION = 300  # 5 minutes
    RATE_LIMIT_COOLDOWN = 60  # 1 minute

    # Cache settings
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_THRESHOLD = 1000
    
    # Market data settings
    MARKET_DATA_RETRY_ATTEMPTS = 3
    MARKET_DATA_BACKOFF_BASE = 0.5
    MARKET_DATA_CACHE_DURATION = 300
    
    # Rate limiting
    RATELIMIT_DEFAULT = "60/minute"
    RATELIMIT_STORAGE_URL = "memory://"

class DevelopmentConfig(Config):
    DEBUG = True
    CACHE_TYPE = 'simple'  # Use in-memory cache for development
    CACHE_DEFAULT_TIMEOUT = 60
    
    # For local development, allow loading API keys from a local file
    API_KEYS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api_keys.py')
    if os.path.exists(API_KEYS_FILE):
        try:
            # Load API keys from local file
            import importlib.util
            spec = importlib.util.spec_from_file_location("api_keys", API_KEYS_FILE)
            api_keys_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(api_keys_module)
            
            # Get API keys from module
            if hasattr(api_keys_module, 'FINNHUB_API_KEY') and not Config.FINNHUB_API_KEY:
                Config.FINNHUB_API_KEY = api_keys_module.FINNHUB_API_KEY
                print("✅ Loaded Finnhub API key from local file")
                
            if hasattr(api_keys_module, 'ALPHA_VANTAGE_KEY') and not Config.ALPHA_VANTAGE_KEY:
                Config.ALPHA_VANTAGE_KEY = api_keys_module.ALPHA_VANTAGE_KEY
                print("✅ Loaded Alpha Vantage API key from local file")
        except Exception as e:
            print(f"⚠️ Error loading API keys from file: {e}")

class ProductionConfig(Config):
    DEBUG = False
    CACHE_TYPE = 'redis'
    CACHE_REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
    CACHE_REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
    CACHE_REDIS_DB = int(os.environ.get('REDIS_DB', 0))
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', "redis://localhost:6379/0")
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
