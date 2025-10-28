from typing import List, Dict, Any
from config import fetch_all, fetch_one, execute_query
from sqlite_config import get_all_building_times
import logging
import time

logger = logging.getLogger(__name__)

# --- Simple In-Memory Cache for Buildings ---
# This will store the buildings list to avoid hitting the database repeatedly.
buildings_cache = {
    "data": None,
    "timestamp": 0
}
CACHE_DURATION_SECONDS = 300 # Cache for 5 minutes

def get_distinct_buildings() -> List[Dict[str, Any]]:
    """
    Fetches a distinct list of buildings, using a time-based cache
    to avoid excessive database queries.
    """
    # Check if the cache is still valid
    is_cache_valid = (time.time() - buildings_cache["timestamp"]) < CACHE_DURATION_SECONDS
    
    if buildings_cache["data"] and is_cache_valid:
        logger.info("Returning buildings list from cache.")
        return buildings_cache["data"]

    logger.info("Fetching distinct buildings from database (cache empty or expired).")
    sql = """
        SELECT DISTINCT b.Building_PRK AS id, b.bldBuildingName_TXT AS name
        FROM Device_TBL d JOIN Building_TBL b ON d.dvcBuilding_FRK = b.Building_PRK
        WHERE d.dvcBuilding_FRK IS NOT NULL AND d.dvcDeviceType_FRK=138
        ORDER BY b.bldBuildingName_TXT
    """
    rows = fetch_all(sql)
    buildings = [dict(row) for row in rows]
    logger.info(f"Found {len(buildings)} distinct buildings.")
    
    building_times = get_all_building_times()
    for building in buildings:
        times = building_times.get(building["id"])
        if times:
            building["start_time"] = times.get("start_time")
            building["end_time"] = times.get("end_time")
            
    # Update the cache
    buildings_cache["data"] = buildings
    buildings_cache["timestamp"] = time.time()
    
    return buildings

def get_building_panel_state(building_id: int) -> str:
    sql = """
        SELECT dvcCurrentState_TXT 
        FROM Device_TBL 
        WHERE dvcBuilding_FRK = :building_id AND dvcName_TXT LIKE '%Panel%'
    """
    params = {"building_id": building_id}
    row = fetch_one(sql, params)
    if not row or not row.get("dvccurrentstate_txt"):
        return "Unknown"
    
    state_text = row["dvccurrentstate_txt"]
    if 'AreaArmingStates.4' in state_text:
        return "Armed"
    elif 'AreaArmingStates.2' in state_text:
        return "Disarmed"
    else:
        return "Unknown"

# --- ADDED: Function to get all proevents/devices for a building ---
def get_devices(building_id: int, search: str | None = None,
                limit: int = 100, offset: int = 0) -> list[dict]:
    """
    Fetches all proevents (devices) for a specific building,
    joining with ProEvent_TBL to get their reactive state.
    """
    logger.debug(f"Fetching devices for building {building_id} with search='{search}'")
    
    # Parameters for OFFSET/FETCH must be literals for pyodbc, not bound parameters.
    # This is safe as limit/offset are guaranteed to be integers.
    params = {
        "building_id": building_id,
        "search": f"%{search}%" if search else "%",
    }
    
    # We now use f-strings for {int(offset)} and {int(limit)}
    sql = f"""
        SELECT 
            p.ProEvent_PRK AS id,
            p.pevAlias_TXT AS name,
            p.pevReactive_FRK AS reactive_state
        FROM 
            Device_TBL d
        JOIN 
            ProEvent_TBL p ON p.pevBuilding_FRK = d.dvcBuilding_FRK
        WHERE 
            d.dvcBuilding_FRK = :building_id
            AND d.dvcDeviceType_FRK = 138
            AND d.dvcName_TXT LIKE :search
        ORDER BY
            d.dvcName_TXT
        OFFSET {int(offset)} ROWS
        FETCH NEXT {int(limit)} ROWS ONLY
    """
    
    try:
        rows = fetch_all(sql, params)
        logger.info(f"Found {len(rows)} devices for building {building_id}.") # Added log to see if query works
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching devices: {e}")
        return []

# --- MODIFIED: Function to set the reactive state for a building ---
def set_reactive_state_for_building(building_id: int, reactive: int, 
                                    ignored_ids: list[int]) -> int:
    """
    Sets the reactive state for all proevents in a building, skipping
    any IDs in the ignored_ids list.
    """
    action = "Arm" if reactive == 0 else "Disarm"
    logger.info(f"Setting reactive state to {action} for building {building_id}")

    # Base query
    sql = """
        UPDATE ProEvent_TBL
        SET pevReactive_FRK = :reactive
        WHERE pevBuilding_FRK IN (
            SELECT dvcBuilding_FRK 
            FROM Device_TBL 
            WHERE dvcBuilding_FRK = :building_id AND dvcDeviceType_FRK = 138
        )
    """
    params = {
        "reactive": reactive,
        "building_id": building_id
    }

    # Add ignored IDs to the query safely
    if ignored_ids:
        logger.info('found ignoredIDs running sql query for it')
        # Create named parameters for each ignored ID
        ignored_params = {f"id_{i}": p_id for i, p_id in enumerate(ignored_ids)}
        print(ignored_params)
        # --- THIS IS THE FIX ---
        # Changed "proDevice_FRK" to "ProEvent_PRK" to match the primary key
        # of ProEvent_TBL, which is what your ignored_ids list contains.
        sql += f" AND ProEvent_PRK NOT IN ({', '.join([f':{k}' for k in ignored_params.keys()])})"
        logger.info(f'o sqlqueries for/device/action:{sql}')
        # --- END OF FIX ---
        
        # Add the new parameters to the main params dict
        params.update(ignored_params)
        

    try:
        affected_rows = execute_query(sql, params)
        logger.info(f"Affected {affected_rows} rows for building {building_id}.")
        return affected_rows
    except Exception as e:
        logger.error(f"Error setting reactive state for building {building_id}: {e}")
        return 0