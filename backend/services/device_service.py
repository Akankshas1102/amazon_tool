from sqlalchemy import text
from config import get_db_connection
import logging


logger = logging.getLogger(__name__)
def get_all_devices(state: str | None = None):
    """
    Retrieves all devices from the database, with an optional filter for the state.
    Maps DB columns to Pydantic field names.
    """
    sql = """
        SELECT Device_PRK, dvcName_TXT, dvcCurrentState_TXT
        FROM Device_TBL
    """
    params = {}

    if state:
        sql += " WHERE dvcCurrentState_TXT LIKE :state_filter"
        params["state_filter"] = f"%{state}%"

    with get_db_connection() as conn:
        results = conn.execute(text(sql), params).mappings().all()

        # ✅ Map DB column names → Pydantic model field names
        devices = [
            {
                "id": row["Device_PRK"],
                "name": row["dvcName_TXT"],
                "state": row["dvcCurrentState_TXT"]
            }
            for row in results
        ]

        return devices

def handle_arm_event():
    """
    Checks for armed devices and updates proevents accordingly.
    """
    update_sql = """
        UPDATE ProEvent_TBL
        SET pevReactive_FRK = 1
        WHERE pevAlias_TXT LIKE '%arm%';
    """
    check_sql = "SELECT 1 FROM Device_TBL WHERE dvcCurrentState_TXT LIKE '%AreaArmingStates.4%'"

    with get_db_connection() as conn:
        device_found = conn.execute(text(check_sql)).first()
        if device_found:
            conn.execute(text(update_sql))
            conn.commit()
            return {"status": "success", "message": "ARM event handled. ProEvents updated."}
    return {"status": "no_action", "message": "No armed devices found."}


def handle_disarm_event():
    """
    Checks for disarmed devices and updates proevents accordingly.
    """
    update_sql = """
        UPDATE ProEvent_TBL
        SET pevReactive_FRK = 0
        WHERE pevAlias_TXT LIKE '%arm%';
    """
    check_sql = "SELECT 1 FROM Device_TBL WHERE dvcCurrentState_TXT LIKE '%AreaArmingStates.2%'"

    with get_db_connection() as conn:
        device_found = conn.execute(text(check_sql)).first()
        if device_found:
            conn.execute(text(update_sql))
            conn.commit()
            return {"status": "success", "message": "DISARM event handled. ProEvents updated."}
    return {"status": "no_action", "message": "No disarmed devices found."}
