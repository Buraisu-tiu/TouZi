# src/services/tasks.py
from utils.db import db
from .market_data import fetch_stock_data
from celery import Celery

celery_app = Celery(
    "stock_trading",
    broker="redis://localhost:6379/0",  # Make sure Redis is running
    backend="redis://localhost:6379/0"
)

@celery_app.task
def update_stock_prices(self):
    try:
        portfolios = db.collection('portfolios').get()
        for portfolio in portfolios:
            symbol = portfolio.to_dict()['symbol']
            data = fetch_stock_data(symbol)
            if data and 'error' not in data:
                portfolio.reference.update({'latest_price': data['close']})
    except Exception as e:
        self.retry(exc=e)