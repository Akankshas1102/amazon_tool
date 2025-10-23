import socket
import os
from logger import get_logger

logger = get_logger(__name__)

PROSERVER_IP = os.getenv("PROSERVER_IP", "10.192.0.173")
PROSERVER_PORT = int(os.getenv("PROSERVER_PORT", 7777))

def send_proserver_notification(building_name: str, device_id: int):
    """
    Sends a unified notification to the ProServer.
    Format: Axe,{building_name}_{device_id}@
    """
    message = f"Axe,{building_name}_{device_id}@"
    logger.info(f"Attempting to send notification to ProServer: {message}")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((PROSERVER_IP, PROSERVER_PORT))
            s.sendall(message.encode())
            logger.info(f"Sent notification to ProServer for device {device_id} in {building_name}")
    except Exception as e:
        logger.error(f"Failed to send notification to ProServer: {e}")

# Removed send_not_armed_alert as it is no longer needed