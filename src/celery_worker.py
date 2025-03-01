from app import app
from celery import Celery

celery = Celery(app.name, broker='redis://localhost:6379/0')
celery.conf.update(app.config)
