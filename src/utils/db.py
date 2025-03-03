# src/utils/db.py
import os
import firebase_admin
from firebase_admin import credentials, firestore
import google.cloud.logging
from google.cloud.logging import Client
import google.auth
import redis

# Use the Redis URL from environment variables
REDIS_URL = os.getenv("REDIS_URL", "redis://red-cv1aijjtq21c73cofsng:6379")

redis_client = redis.StrictRedis.from_url(REDIS_URL, decode_responses=True)
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