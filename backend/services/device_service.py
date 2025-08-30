from sqlalchemy import text
from config import get_db_connection

def get_all_devices(state: str | None = None):
    """
    Retrieves all devices from the database, with an optional filter for the state.
    """
    # ✅ FIX: Changed 'dvcDevice_PK' to a more likely column name.
    # Please verify 'dvcId_INT' is the correct primary key for Device_TBL.
    sql = """
        SELECT
            dvcId_INT           AS id,
            dvcName_TXT         AS name,
            dvcCurrentState_TXT AS state
        FROM Device_TBL
    """
    params = {}
    if state:
        # Append a WHERE clause if a state filter is provided
        sql += " WHERE dvcCurrentState_TXT LIKE :state_filter"
        params["state_filter"] = f"%{state}%"

    with get_db_connection() as conn:
        # Execute the query and return the results as a list of dicts
        results = conn.execute(text(sql), params).mappings().all()
        return list(results)

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

