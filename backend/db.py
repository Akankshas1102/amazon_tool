# JSON is acting as our storage layer, so no DB connection is needed.
# This is just a placeholder to mimic a database module.
from config import DEVICES_FILE, PROEVENT_FILE
import json
import os

def _load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r") as f:
        return json.load(f)

def _save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def load_devices():
    return _load_json(DEVICES_FILE)

def save_devices(data):
    _save_json(DEVICES_FILE, data)

def load_proevents():
    return _load_json(PROEVENT_FILE)

def save_proevents(data):
    _save_json(PROEVENT_FILE, data)
