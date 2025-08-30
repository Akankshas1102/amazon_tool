import json
import os
from config import logger, DEVICES_FILE, PROEVENT_FILE

def load_json(file_path):
    """Load JSON data from file."""
    if not os.path.exists(file_path):
        logger.warning(f"{file_path} not found, creating a new empty file.")
        save_json(file_path, [])
        return []
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.error(f"Corrupted JSON in {file_path}, resetting file.")
        save_json(file_path, [])
        return []

def save_json(file_path, data):
    """Save data to JSON file."""
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
        logger.info(f"Data successfully saved to {file_path}")
    except Exception as e:
        logger.error(f"Error saving to {file_path}: {e}")

# Device functions
def get_all_devices():
    return load_json(DEVICES_FILE)

def add_device(device):
    devices = load_json(DEVICES_FILE)
    devices.append(device)
    save_json(DEVICES_FILE, devices)

def clear_devices():
    save_json(DEVICES_FILE, [])

# ProEvent functions
def get_all_proevents():
    return load_json(PROEVENT_FILE)

def add_proevent(event):
    events = load_json(PROEVENT_FILE)
    events.append(event)
    save_json(PROEVENT_FILE, events)

def clear_proevents():
    save_json(PROEVENT_FILE, [])
