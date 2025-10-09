# backend/services/proevent_service.py

from config import execute_query, fetch_all
from logger import get_logger
from datetime import datetime
from sqlite_config import get_all_building_times, get_ignored_proevents
from services import proserver_service

logger = get_logger(__name__)

def set_proevent_reactive_for_building(building_id: int, reactive: int):
    # ... (this function remains the same)
    sql = """
        UPDATE ProEvent_TBL
        SET pevReactive_FRK = :reactive
        WHERE pevBuilding_FRK = :building_id
    """
    affected_rows = execute_query(sql, {"reactive": reactive, "building_id": building_id})
    logger.info(f"Set ProEvents to reactive={reactive} for building {building_id}. Affected rows: {affected_rows}")
    return affected_rows

def get_all_proevents_for_building(building_id: int, search: str | None = None, limit: int = 100, offset: int = 0):
    # ... (this function remains the same)
    params = {
        "building_id": building_id,
        "limit": limit,
        "offset": offset
    }
    search_clause = ""
    if search:
        search_clause = "AND LOWER(pevAlias_TXT) LIKE LOWER(:search)"
        params["search"] = f"%{search}%"
    sql = f"""
        SELECT
            ProEvent_PRK AS id,
            pevAlias_TXT AS name,
            pevReactive_FRK AS reactive_state
        FROM ProEvent_TBL
        WHERE pevBuilding_FRK = :building_id
        {search_clause}
        ORDER BY pevAlias_TXT
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
    """
    return fetch_all(sql, params)


# --- New function for the scheduler ---
def check_and_notify_disarmed_proevents():
    """
    Checks for disarmed proevents based on building schedules and sends notifications.
    """
    logger.info("Scheduler: Checking proevent states...")
    building_schedules = get_all_building_times()
    ignored_proevents = get_ignored_proevents()
    current_time = datetime.now().time()

    for building_id, schedule in building_schedules.items():
        if not schedule or not schedule.get("start_time"):
            continue

        start_time = datetime.strptime(schedule["start_time"], "%H:%M").time()
        end_time = datetime.strptime(schedule["end_time"], "%H:%M").time() if schedule.get("end_time") else None

        # Check if current time is within the scheduled active time
        is_in_schedule = False
        if end_time:
            if start_time <= current_time <= end_time:
                is_in_schedule = True
        elif current_time >= start_time:
            is_in_schedule = True

        if is_in_schedule:
            proevents = get_all_proevents_for_building(building_id=building_id, limit=10000)
            for proevent in proevents:
                proevent_id = proevent["id"]
                is_disarmed = proevent["reactive_state"] == 0

                if is_disarmed and proevent_id not in ignored_proevents:
                    logger.info(f"ProEvent {proevent_id} in Building {building_id} is disarmed. Sending notification.")
                    proserver_service.send_proserver_notification(proevent_id)