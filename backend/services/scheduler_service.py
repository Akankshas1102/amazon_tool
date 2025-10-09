# backend/services/scheduler_service.py

import schedule
import time
import threading
from logger import get_logger
from services import proevent_service # Changed from device_service

logger = get_logger(__name__)

def check_proevent_states():
    """
    Job function for the scheduler to check proevent states.
    """
    logger.info("Scheduler running: Checking proevent states...")
    try:
        # Calling the new, correct function
        proevent_service.check_and_notify_disarmed_proevents()
    except Exception as e:
        logger.error(f"Error in scheduled proevent check: {e}")

def run_scheduler():
    """
    Runs the scheduler in a separate thread.
    """
    schedule.every(1).minutes.do(check_proevent_states)

    while True:
        schedule.run_pending()
        time.sleep(1)

def start_scheduler():
    """
    Starts the scheduler in a background thread.
    """
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    logger.info("Scheduler started.")