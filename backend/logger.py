import logging
import sys

def get_logger(name: str):
    """
    Configures and returns a logger.
    """
    # Create a logger with the specified name
    logger = logging.getLogger(name)
    
    # This check prevents adding handlers multiple times, which would cause duplicate log messages
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Create a handler to print log messages to the console (standard output)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        
        # Create a formatter to define the structure of the log messages
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        
        # Add the configured handler to the logger
        logger.addHandler(handler)
        
    return logger