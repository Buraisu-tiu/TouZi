# src/services/tasks.py
from celery import Celery
from ..utils.db import db
from .market_data import fetch_stock_data

celery = Celery('tasks', broker='redis://localhost:6379/0')

@celery.task(bind=True)
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