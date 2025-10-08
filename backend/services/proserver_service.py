import socket
import os
from logger import get_logger

logger = get_logger(__name__)

# Now using environment variables with defaults
PROSERVER_IP = os.getenv("PROSERVER_IP", "127.0.0.1")
PROSERVER_PORT = int(os.getenv("PROSERVER_PORT", 9999))

def send_proserver_notification(device_id: int):
    """
    Sends a notification to the ProServer when a device is disarmed.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((PROSERVER_IP, PROSERVER_PORT))
            message = f"Axe,{device_id}_disarmed"
            s.sendall(message.encode())
            logger.info(f"Sent notification to ProServer for device {device_id}")
    except Exception as e:
        logger.error(f"Failed to send notification to ProServer: {e}")