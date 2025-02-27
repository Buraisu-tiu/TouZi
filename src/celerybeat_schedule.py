from celery.schedules import crontab
from services.task import update_stock_cache  # Import task

CELERYBEAT_SCHEDULE = {
    "update_stocks_every_minute": {
        "task": "services.task.update_stock_cache",
        "schedule": crontab(minute="*"),  # Runs every minute
        "args": ("AAPL",)  # Example stock symbol
    }
}
