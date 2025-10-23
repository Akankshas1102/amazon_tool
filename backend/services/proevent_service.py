# backend/services/proevent_service.py

# --- THIS IS THE FIX ---
# Removed get_db and ProEvent, which don't exist in sqlite_config.py
from sqlite_config import get_building_time, get_ignored_proevents
# --- END OF FIX ---

from services import device_service, proserver_service, cache_service
from logger import get_logger
from datetime import datetime
import traceback

logger = get_logger(__name__)


def get_all_proevents_for_building(building_id: int, search: str | None = None,
                                 limit: int = 100, offset: int = 0) -> list[dict]:
    """
    Retrieves all proevents for a specific building.
    
    This function now assumes that device_service is the source of truth
    for proevents, as they are not in the building_schedules.db.
    """
    logger.debug(f"Fetching proevents for building {building_id} with search='{search}'")
    try:
        # This function MUST exist in your device_service.py file
        proevents = device_service.get_devices(
            building_id=building_id, search=search, limit=limit, offset=offset
        )
        return proevents
    except AttributeError:
        logger.error("CRITICAL: device_service.get_devices() function is missing from device_service.py.")
        return []
    except Exception as e:
        logger.error(f"Error fetching proevents: {e}")
        return []

def set_proevent_reactive_for_building(building_id: int, reactive: int,
                                       ignored_ids: list[int] | None = None) -> int:
    """
    Sets the reactive state for all proevents in a building,
    skipping those in the ignored_ids list.
    
    This function now assumes device_service handles the state change.
    """
    if ignored_ids is None:
        ignored_ids = []
    
    action = "Arm" if reactive == 1 else "Disarm"
    logger.info(f"Setting reactive state for building {building_id} to {action}, ignoring {len(ignored_ids)} proevents.")
    
    try:
        # This function MUST exist in your device_service.py file
        affected_rows = device_service.set_reactive_state_for_building(
            building_id=building_id, 
            reactive=reactive, 
            ignored_ids=ignored_ids
        )
        
        if affected_rows > 0:
            logger.info(f"Updated {affected_rows} proevents for building {building_id} to state {reactive}.")
        return affected_rows
    except AttributeError:
         logger.error("CRITICAL: device_service.set_reactive_state_for_building() function is missing from device_service.py.")
         return 0
    except Exception as e:
        logger.error(f"Error in bulk {action} for building {building_id}: {e}")
        return 0

def get_proevents_to_change(building_id: int, target_state: int,
                            ignored_ids: list[int]) -> list[dict]:
    """
    Get list of proevents that need to be changed to the target_state
    and are not in the ignored list.
    
    This function now assumes device_service provides the current state.
    """
    try:
        all_proevents = get_all_proevents_for_building(building_id, limit=10000)
        
        to_change = []
        for proevent in all_proevents:
            proevent_id = proevent["id"]
            current_state = 1 if proevent.get("reactive_state", 0) == 1 else 0 # Normalize state
            
            if current_state != target_state and proevent_id not in ignored_ids:
                to_change.append(proevent)
                
        return to_change
    except Exception as e:
        logger.error(f"Error getting proevents to change: {e}")
        return []


def check_and_manage_scheduled_states():
    """
    Checks building schedules and updates proevent states.
    If panel is ARMED: Arms/disarms devices based on schedule.
    If panel is DISARMED: Sends 'notarmed' alerts for devices that *should* be
    armed but are not ignored.
    """
    try:
        logger.info("Scheduler running: Checking building schedules...")
        
        # 1. Get Global Panel Status
        panel_is_armed = cache_service.get_cache_value('panel_armed')
        if panel_is_armed is None:
            logger.warning("Panel status not in cache. Defaulting to 'Armed'.")
            panel_is_armed = True
            
        logger.info(f"Panel Status: {'ARMED' if panel_is_armed else 'DISARMED'}")

        # This assumes device_service provides the building list
        all_buildings = device_service.get_distinct_buildings()
        ignored_proevents_map = get_ignored_proevents() # Gets dict from sqlite
        now = datetime.now().time()

        for building in all_buildings:
            building_id = building["id"]
            building_name = building["name"]
            
            # 2. Get schedule from SQLite
            times = get_building_time(building_id)
            
            # Safer check for None, str, or invalid dicts
            if not isinstance(times, dict) or not times.get("start_time") or not times.get("end_time"):
                logger.warning(f"Skipping building {building_id} - invalid or no schedule set (times: {times}).")
                continue

            try:
                start_time = datetime.strptime(times["start_time"], "%H:%M").time()
                end_time = datetime.strptime(times["end_time"], "%H:%M").time()
            except ValueError:
                logger.error(f"Invalid time format for building {building_id}. Skipping.")
                continue

            is_within_schedule = start_time <= now < end_time
            
            # 3. Get lists of ignored IDs for this building
            ignored_on_arm_ids = [
                pid for pid, flags in ignored_proevents_map.items()
                if flags.get("building_frk") == building_id and flags.get("ignore_on_arm", False)
            ]
            ignored_on_disarm_ids = [
                pid for pid, flags in ignored_proevents_map.items()
                if flags.get("building_frk") == building_id and flags.get("ignore_on_disarm", False)
            ]

            # --- Main Logic Branch ---
            
            if panel_is_armed:
                # --- PANEL IS ARMED: Original arm/disarm logic ---
                logger.debug(f"Panel is ARMED. Checking schedule for {building_name}")
                if is_within_schedule:
                    # Within schedule: ARM devices (that aren't ignored on arm)
                    set_proevent_reactive_for_building(building_id, 1, ignored_on_arm_ids)
                else:
                    # Outside schedule: DISARM devices (that aren't ignored on disarm)
                    # Get list *before* disarming to send notifications
                    proevents_to_disarm = get_proevents_to_change(
                        building_id, 0, ignored_on_disarm_ids
                    )
                    
                    if proevents_to_disarm:
                        set_proevent_reactive_for_building(building_id, 0, ignored_on_disarm_ids)
                        # Send notification for each device disarmed by schedule
                        for proevent in proevents_to_disarm:
                            proserver_service.send_proserver_notification(proevent["id"], "disarmed")
            
            else:
                # --- PANEL IS DISARMED: New 'not-armed' alert logic ---
                if is_within_schedule:
                    # We are in schedule, but panel is disarmed.
                    # Find all devices that *should* be armed and are *not* ignored.
                    logger.info(f"Panel is DISARMED. Checking 'not-armed' alerts for building {building_name}")
                    
                    all_proevents = get_all_proevents_for_building(building_id, limit=10000)
                    for proevent in all_proevents:
                        proevent_id = proevent["id"]
                        
                        # Check if this proevent is ignored on *disarm*
                        is_ignored_on_disarm = proevent_id in ignored_on_disarm_ids
                        
                        # If it's NOT ignored on disarm, send the alert.
                        if not is_ignored_on_disarm:
                            logger.debug(f"Sending 'not-armed' alert for device {proevent_id} in {building_name}")
                            proserver_service.send_not_armed_alert(
                                building_name=building_name,
                                device_id=proevent_id
                            )
                        else:
                            logger.debug(f"Skipping 'not-armed' alert for {proevent_id}, as it is ignored.")
                else:
                    # Outside schedule and panel is disarmed. No action needed.
                    logger.debug(f"Panel is DISARMED and outside schedule for {building_name}. No action.")
                    pass # Explicitly do nothing

    except Exception as e:
        tb_str = traceback.format_exc()
        logger.error(f"Critical error in scheduled job: {e}\n{tb_str}")