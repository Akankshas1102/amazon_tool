import schedule
import time
import threading
from logger import get_logger
from services import device_service

logger = get_logger(__name__)

def check_device_states():
    """
    Checks the state of all devices and sends notifications for disarmed devices.
    """
    logger.info("Scheduler running: Checking device states...")
    try:
        device_service.check_and_notify_disarmed_devices()
    except Exception as e:
        logger.error(f"Error in scheduled device check: {e}")

def run_scheduler():
    """
    Runs the scheduler in a separate thread.
    """
    # Schedule the job to run every 5 minutes
    schedule.every(5).minutes.do(check_device_states)

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