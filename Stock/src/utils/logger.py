# src/utils/logger.py
import logging
from logging import FileHandler, Formatter

def setup_logger(app):
    file_handler = FileHandler('errorlog.txt')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    app.logger.addHandler(file_handler)
    
    # Set up basic logging
    logging.basicConfig(level=logging.INFO)
    return app.logger

# Create a logger instance that can be imported by other modules
logger = logging.getLogger('stock_trading')