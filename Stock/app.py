import os
import random
import requests
import logging
from datetime import datetime, timedelta, timezone
import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_caching import Cache
from flask_htmlmin import HTMLMIN
from celery import Celery
from coinbase.wallet.client import Client
from werkzeug.utils import secure_filename
from logging import FileHandler, Formatter
import yfinance as yf
from pycoingecko import CoinGeckoAPI as cg
import finnhub
import plotly.express as px
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud import firestore as gcp_firestore
import google.cloud.logging
from google.cloud.logging import Client as gcp_Logging_Client
import google.auth
import google.auth

# Specify the time zone
tz = timezone.utc

# Get the current time in the specified time zone
now = datetime.now(tz)
# Load the service account key file

credentials, project_id = google.auth.load_credentials_from_file(
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'],
    scopes=['https://www.googleapis.com/auth/firestore']
)

project_id = "stock-trading-simulator-b6e27"
client = google.cloud.logging.Client(credentials=credentials, project=project_id)



logging.basicConfig(level=logging.INFO)
# Create Firestore client
db = firestore.Client(project='stock-trading-simulator-b6e27')
print("Firestore client created:", db)
cg = cg()

# Enable Google Cloud logging
client = Client()
client.setup_logging()


    
app = Flask(__name__, static_folder='static')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
HTMLMIN(app)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
celery = Celery(app.name, broker='redis://localhost:6379/0')

celery.conf.update(app.config)


def register_template_filters():
    app.jinja_env.filters['hex_to_rgb'] = hex_to_rgb
    app.jinja_env.filters['lighten_color'] = lighten_color
    
    
register_template_filters()
# Setup detailed logging
file_handler = FileHandler('errorlog.txt')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
print(file_handler)


    
# List of API keys
api_keys = [
    'ctitlv1r01qgfbsvh1dgctitlv1r01qgfbsvh1e0',
    'ctitnthr01qgfbsvh59gctitnthr01qgfbsvh5a0',
    'ctjgjm1r01quipmu2qi0ctjgjm1r01quipmu2qig'
]

# Coinbase configuration
coinbase_api_key = 'your_coinbase_api_key'
coinbase_api_secret = 'your_coinbase_api_secret'

app.secret_key = 'your_secret_key'



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

@app.route('/')
def home():
    create_badges()
    return redirect(url_for('login'))



@app.route('/check-session')
def check_session():
    print("Current session:", dict(session))
    return jsonify({
        'session': dict(session),
        'username': session.get('username')
    })

@app.route('/dashboard')
def dashboard():
    
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    user = db.collection('users').document(user_id).get().to_dict()
    transactions_ref = db.collection('transactions').where('user_id', '==', user_id).where('transaction_type', '==', 'SELL').where('profit_loss', '!=', 0).order_by('timestamp', direction=firestore.Query.DESCENDING).limit(5)
    transactions = transactions_ref.stream()
    history = []
    for t in transactions:
        t_data = t.to_dict()
        history.append({
            'date': t_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
            'type': t_data['transaction_type'],
            'symbol': t_data['symbol'],
            'shares': t_data['shares'],
            'price': t_data['price'],
            'total': t_data['total_amount'],
            'profit_loss': round(t_data.get('profit_loss', 0.0), 2)
        })
    success = request.args.get('success')
    return render_template('dashboard.html.jinja2', user=user, transactions=history, success=success)



if __name__ == '__main__':
    register_template_filters()
    app.run(debug=True)