import json
import os
# from config import CACHE_FILE  <-- This was the error, it's removed.
from logger import get_logger
import threading

logger = get_logger(__name__)

# Define the cache file path directly in this file
CACHE_FILE = "app_cache.json"
_cache = {}
_cache_lock = threading.Lock()

def load_cache():
    """
    Load the cache from a JSON file into memory.
    """
    global _cache
    with _cache_lock:
        if _cache:
            return _cache
        
        if not os.path.exists(CACHE_FILE):
            logger.warning(f"Cache file not found at {CACHE_FILE}. Creating a new one.")
            _cache = {}
            save_cache(_cache) # Create the file
            return _cache

        try:
            with open(CACHE_FILE, 'r') as f:
                _cache = json.load(f)
                logger.info("Cache loaded from file.")
                return _cache
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Error loading cache file: {e}. Using empty cache.")
            _cache = {}
            return _cache

def save_cache(cache_data):
    """
    Save the in-memory cache to the JSON file.
    """
    global _cache
    with _cache_lock:
        _cache = cache_data
        try:
            with open(CACHE_FILE, 'w') as f:
                json.dump(_cache, f, indent=4)
        except IOError as e:
            logger.error(f"Failed to save cache to file: {e}")