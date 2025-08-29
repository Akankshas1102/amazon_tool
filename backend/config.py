import os

# Base configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# Ensure data directory exists
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# File paths for JSON storage
CACHE_FILE = os.path.join(DATA_DIR, "cache.json")
DEVICES_FILE = os.path.join(DATA_DIR, "devices.json")
PROEVENT_FILE = os.path.join(DATA_DIR, "proevents.json")
