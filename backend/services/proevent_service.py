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
    # DEFENSIVE CHECK: Ensure ignored_proevents is a dictionary.
    if ignored_proevents is None:
        ignored_proevents = {}

    sql = "UPDATE ProEvent_TBL SET pevReactive_FRK = :reactive WHERE pevBuilding_FRK = :building_id"
    params = {"reactive": reactive, "building_id": building_id}

    proevents_to_ignore = []
    # This loop is now safe.
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
    results = fetch_all(sql, params)
    # DEFENSIVE CHECK: Ensure this function always returns a list.
    return results if results is not None else []


def check_and_manage_scheduled_states():
    """
    Scheduler job to automatically make proevents non-reactive during
    scheduled times and reactive again afterward.
    """
    logger.info("Scheduler: Checking and managing scheduled proevent states...")
    building_schedules = get_all_building_times()

    # DEFENSIVE CHECK 1: Ensure building_schedules is a dictionary before iterating.
    if building_schedules is None:
        logger.warning("get_all_building_times() returned None. Skipping this scheduler run.")
        return  # Exit the function early to prevent a crash.

    current_time = datetime.now().time()
    for building_id, schedule in building_schedules.items():
        # DEFENSIVE CHECK 2: Ensure the schedule for a building is valid.
        if schedule is None or not schedule.get("start_time") or not schedule.get("end_time"):
            continue

        start_time = datetime.strptime(schedule["start_time"], "%H:%M").time()
        end_time = datetime.strptime(schedule["end_time"], "%H:%M").time()

        is_in_schedule = start_time <= current_time < end_time

        if is_in_schedule:
            logger.debug(f"Building {building_id} is IN schedule. Setting to non-reactive.")
            affected_rows = set_proevent_reactive_for_building(building_id, 0)

            if affected_rows > 0:
                logger.info(f"Building {building_id} disarmed. Sending notifications...")
                devices_in_building = get_all_proevents_for_building(building_id, limit=1000)

                # DEFENSIVE CHECK 3: Ensure devices_in_building is a list before iterating.
                if devices_in_building is not None:
                    for device in devices_in_building:
                        if device and device.get("reactive_state") == 0:
                            proserver_service.send_proserver_notification(device['id'])
        else:
            logger.debug(f"Building {building_id} is OUTSIDE schedule. Setting to reactive.")
            set_proevent_reactive_for_building(building_id, 1)