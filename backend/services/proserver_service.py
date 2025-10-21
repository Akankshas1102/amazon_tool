import socket
import os
from logger import get_logger

logger = get_logger(__name__)

PROSERVER_IP = os.getenv("PROSERVER_IP", "10.192.0.173")
PROSERVER_PORT = int(os.getenv("PROSERVER_PORT", 7777))

def send_proserver_notification(device_id: int, message_type: str = "disarmed"):
    """
    Sends a notification to the ProServer when a device is disarmed by schedule.
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

def send_not_armed_alert(building_name: str, device_id: int):
    """
    Sends the specific 'notarmed' alert to ProServer when panel is disarmed
    but a device is scheduled to be on.
    Format: axe,Bud_name_Device_ID_notarmed@
    """
    message = f"Axe,{building_name}_{device_id}_notarmed@"
    logger.info(f"Attempting to send 'notarmed' alert: {message}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((PROSERVER_IP, PROSERVER_PORT))
            s.sendall(message.encode())
            logger.info(f"Sent 'notarmed' alert for device {device_id} in {building_name}")
    except Exception as e:
        logger.error(f"Failed to send 'notarmed' alert to ProServer: {e}")