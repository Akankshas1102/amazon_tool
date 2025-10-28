# backend/services/proevent_service.py

from sqlite_config import get_building_time, get_ignored_proevents
from services import device_service, proserver_service, cache_service
from logger import get_logger
from datetime import datetime
import traceback

logger = get_logger(__name__)


def get_all_proevents_for_building(building_id: int, search: str | None = None,
                                 limit: int = 100, offset: int = 0) -> list[dict]:
    """
    Retrieves all proevents for a specific building.
    """
    logger.debug(f"Fetching proevents for building {building_id} with search='{search}'")
    try:
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
    """
    if ignored_ids is None:
        ignored_ids = []
        
    print(ignored_ids)
    action = "Arm" if reactive == 1 else "Disarm"
    logger.info(f"Setting reactive state for building {building_id} to {action}, ignoring {len(ignored_ids)} proevents.")
    
    try:
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


# --- NEW FUNCTION TO RE-EVALUATE A BUILDING ---
def reevaluate_building_state(building_id: int):
    """
    Runs the core arm/disarm logic for a single building on demand.
    This is called after ignore settings are changed.
    """
    logger.info(f"Re-evaluating state for building {building_id}...")
    try:
        # 1. Get Global Panel Status
        panel_is_armed = cache_service.get_cache_value('panel_armed')
        if panel_is_armed is None:
            logger.warning("Panel status not in cache. Defaulting to 'Armed'.")
            panel_is_armed = True
        
        logger.info(f"Panel Status: {'ARMED' if panel_is_armed else 'DISARMED'}")

        # 2. Get schedule from SQLite
        times = get_building_time(building_id)
        if not isinstance(times, dict) or not times.get("start_time") or not times.get("end_time"):
            logger.warning(f"Skipping re-evaluation for building {building_id} - no schedule.")
            return

        start_time = datetime.strptime(times["start_time"], "%H:%M").time()
        end_time = datetime.strptime(times["end_time"], "%H:%M").time()
        now = datetime.now().time()
        is_within_schedule = start_time <= now < end_time

        # 3. Get ignored IDs
        ignored_proevents_map = get_ignored_proevents()
        ignored_on_disarm_ids = [
            pid for pid, flags in ignored_proevents_map.items()
            if flags.get("building_frk") == building_id and flags.get("ignore_on_disarm", False)
        ]
        
        # --- THIS IS THE NEW LOGGING LINE ---
        logger.info(f"RE-EVALUATE: Building {building_id} - Ignored IDs list: {ignored_on_disarm_ids}")
        # --- END OF NEW LOGGING LINE ---
        
        # 4. Apply Logic
        if panel_is_armed:
            logger.debug(f"Panel is ARMED. Checking schedule for {building_id}")
            if is_within_schedule:
                # Within schedule: ARM devices
                set_proevent_reactive_for_building(building_id, 1, [])
            else:
                # Outside schedule: DISARM devices (that aren't ignored on disarm)
                set_proevent_reactive_for_building(building_id, 0, ignored_on_disarm_ids)
        else:
            # Panel is disarmed, no state changes needed.
            logger.info(f"Panel is DISARMED. No state change needed for building {building_id} on re-evaluation.")
            pass # Explicitly do nothing to state
        
        logger.info(f"Re-evaluation complete for building {building_id}.")
        
    except Exception as e:
        logger.error(f"Error during re-evaluation for building {building_id}: {e}")
        # Re-raise so the API endpoint can return a 500
        raise

def check_and_manage_scheduled_states():
    """
    Checks building schedules and updates proevent states.
    If panel is ARMED: Arms/disarms devices based on schedule.
    If panel is DISARMED: Sends 'notarmed' alerts for devices that *should* be
    armed but are not ignored.
    """
    try:
        logger.info("Scheduler running: Checking building schedules...")
        
        panel_is_armed = cache_service.get_cache_value('panel_armed')
        if panel_is_armed is None:
            logger.warning("Panel status not in cache. Defaulting to 'Armed'.")
            panel_is_armed = True
            
        logger.info(f"Panel Status: {'ARMED' if panel_is_armed else 'DISARMED'}")

        all_buildings = device_service.get_distinct_buildings()
        ignored_proevents_map = get_ignored_proevents()
        now = datetime.now().time()
        now_time_minute = now.replace(second=0, microsecond=0)

        for building in all_buildings:
            building_id = building["id"]
            building_name = building["name"]
            
            times = get_building_time(building_id)
            
            if not isinstance(times, dict) or not times.get("start_time") or not times.get("end_time"):
                logger.warning(f"Skipping building {building_id} - invalid or no schedule set (times: {times}).")
                continue

            try:
                start_time = datetime.strptime(times["start_time"], "%H:%M").time()
                end_time = datetime.strptime(times["end_time"], "%H:%M").time()
            except ValueError:
                logger.error(f"Invalid time format for building {building_id}. Skipping.")
                continue

            is_start_time = (now_time_minute == start_time)
            is_within_schedule = start_time <= now < end_time
            
            ignored_on_disarm_ids = [
                pid for pid, flags in ignored_proevents_map.items()
                if flags.get("building_frk") == building_id and flags.get("ignore_on_disarm", False)
            ]
            
            if panel_is_armed:
                logger.debug(f"Panel is ARMED. Checking schedule for {building_name}")
                
                if is_start_time:
                    logger.info(f"Panel is ARMED at schedule start for {building_name}. Sending common alert.")
                    proserver_service.send_proserver_notification(
                        building_name=building_name,
                        device_id=None 
                    )

                if is_within_schedule:
                    set_proevent_reactive_for_building(building_id, 1, [])
                else:
                    proevents_to_disarm = get_proevents_to_change(
                        building_id, 0, ignored_on_disarm_ids
                    )
                    
                    if proevents_to_disarm:
                        set_proevent_reactive_for_building(building_id, 0, ignored_on_disarm_ids)
                        
                        logger.info(f"Panel is ARMED, outside schedule. Sent common disarm alert for {building_name}.")
                        proserver_service.send_proserver_notification(
                            building_name=building_name,
                            device_id=None 
                        )
            
            else:
                if is_within_schedule:
                    logger.info(f"Panel is DISARMED. Checking 'not-armed' alerts for {building_name}")
                    
                    all_proevents = get_all_proevents_for_building(building_id, limit=10000)
                    
                    alert_needed = False
                    for proevent in all_proevents:
                        proevent_id = proevent["id"]
                        is_ignored_on_disarm = proevent_id in ignored_on_disarm_ids
                        
                        if not is_ignored_on_disarm:
                            alert_needed = True
                            break 
                    
                    if alert_needed:
                        logger.debug(f"Panel is DISARMED within schedule. Sending common 'not-armed' alert for {building_name}")
                        proserver_service.send_proserver_notification(
                            building_name=building_name,
                            device_id=None 
                        )
                    else:
                         logger.debug(f"Panel is DISARMED within schedule for {building_name}, but all proevents are ignored. No alert.")
                else:
                    logger.debug(f"Panel is DISARMED and outside schedule for {building_name}. No action.")
                    pass 

    except Exception as e:
        tb_str = traceback.format_exc()
        logger.error(f"Critical error in scheduled job: {e}\n{tb_str}")