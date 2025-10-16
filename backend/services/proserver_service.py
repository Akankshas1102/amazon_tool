import socket
import os
from logger import get_logger

logger = get_logger(__name__)

PROSERVER_IP = os.getenv("PROSERVER_IP", "10.192.0.173")
PROSERVER_PORT = int(os.getenv("PROSERVER_PORT", 7777))

def send_proserver_notification(device_id: int, message_type: str = "disarmed"):
    """
    Sends a notification to the ProServer when a device is disarmed.
    """
    logger.info(f"Attempting to send notification to ProServer for device_id: {device_id}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((PROSERVER_IP, PROSERVER_PORT))
            message = f"Axe,{device_id}_{message_type}@"
            s.sendall(message.encode())
            logger.info(f"Sent notification to ProServer for device {device_id}")
    except Exception as e:
        logger.error(f"Failed to send notification to ProServer: {e}")