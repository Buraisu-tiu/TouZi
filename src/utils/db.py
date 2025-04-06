# src/utils/db.py
import os
import firebase_admin
from firebase_admin import credentials, firestore
import google.cloud.logging
from google.cloud.logging import Client
import google.auth
import redis

# Change Redis configuration to use local Redis without authentication
REDIS_URL = "redis://127.0.0.1:6379/0"

try:
    redis_client = redis.Redis(host='127.0.0.1', port=6379, db=0, decode_responses=True)
    redis_client.ping()
except redis.ConnectionError:
    print("Warning: Redis connection failed, falling back to dummy cache")
    class DummyRedis:
        def get(self, *args): return None
        def set(self, *args, **kwargs): pass
        def setex(self, *args, **kwargs): pass
    redis_client = DummyRedis()

def init_db():
    credentials, project_id = google.auth.load_credentials_from_file(
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'],
        scopes=['https://www.googleapis.com/auth/firestore']
    )
    
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials)
    
    db = firestore.Client(project='stock-trading-simulator-b6e27')
    return db

db = init_db()