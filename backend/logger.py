import logging
from logging.handlers import RotatingFileHandler

def get_logger(name: str):
    """
    Configures and returns a logger that writes to app.log.
    """
    logger = logging.getLogger(name)
    
    # This check prevents adding handlers multiple times
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Create a file handler to log to a file, replacing the console handler
        handler = RotatingFileHandler("app.log", maxBytes=1024 * 1024, backupCount=5)
        handler.setLevel(logging.DEBUG)
        
        # Create a formatter to define the structure of the log messages
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        
        # Add the configured handler to the logger
        logger.addHandler(handler)
        
    return logger