# backend/services/proevent_service.py

from config import execute_query, fetch_all
from logger import get_logger
from datetime import datetime
from sqlite_config import get_all_building_times, get_ignored_proevents, log_proevent_state
from services import proserver_service

logger = get_logger(__name__)

def set_proevent_reactive_for_building(building_id: int, reactive: int):
    """
    Sets all proevents in a building to a specific reactive state,
    unless they are individually ignored for that specific action.
    """
    ignored_proevents = get_ignored_proevents()
    
    sql = "UPDATE ProEvent_TBL SET pevReactive_FRK = :reactive WHERE pevBuilding_FRK = :building_id"
    params = {"reactive": reactive, "building_id": building_id}
    
    proevents_to_ignore = []
    for proevent_id, ignore_settings in ignored_proevents.items():
        if reactive == 1 and ignore_settings.get("ignore_on_arm"):
            proevents_to_ignore.append(proevent_id)
        elif reactive == 0 and ignore_settings.get("ignore_on_disarm"):
            proevents_to_ignore.append(proevent_id)

    if proevents_to_ignore:
        ignored_params = {f"ignore_{i}": pid for i, pid in enumerate(proevents_to_ignore)}
        sql += f" AND ProEvent_PRK NOT IN ({', '.join(':' + name for name in ignored_params)})"
        params.update(ignored_params)

    affected_rows = execute_query(sql, params)
    logger.info(f"Set ProEvents to reactive={reactive} for building {building_id}. Affected rows: {affected_rows}")
    
    log_proevent_state(0, building_id, f"Bulk {'Arm' if reactive == 1 else 'Disarm'}")
    
    return affected_rows


def get_all_proevents_for_building(building_id: int, search: str | None = None, limit: int = 100, offset: int = 0):
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


def check_and_manage_scheduled_states():
    """
    Scheduler job to automatically make proevents non-reactive during
    scheduled times and reactive again afterward.
    """
    logger.info("Scheduler: Checking and managing scheduled proevent states...")
    building_schedules = get_all_building_times()
    current_time = datetime.now().time()

    for building_id, schedule in building_schedules.items():
        if not schedule or not schedule.get("start_time") or not schedule.get("end_time"):
            continue

        start_time = datetime.strptime(schedule["start_time"], "%H:%M").time()
        end_time = datetime.strptime(schedule["end_time"], "%H:%M").time()

        # Check if we are currently within the non-reactive period
        is_in_schedule = start_time <= current_time < end_time

        # We need to know the current state to avoid unnecessary database writes
        # This is a simplified check; a more robust solution might query the panel state
        # For now, we assume we need to enforce the state on every run.
        
        if is_in_schedule:
            logger.debug(f"Building {building_id} is IN schedule. Setting to non-reactive.")
            set_proevent_reactive_for_building(building_id, 0) # Non-reactive
        else:
            logger.debug(f"Building {building_id} is OUTSIDE schedule. Setting to reactive.")
            set_proevent_reactive_for_building(building_id, 1) # Reactive