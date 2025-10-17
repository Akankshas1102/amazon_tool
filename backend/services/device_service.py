# backend/services/device_service.py

from typing import List, Dict, Any
from config import fetch_all, fetch_one
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
    """
    Gets the state of the panel for a given building.
    """
    sql = """
        SELECT dvcCurrentState_TXT
        FROM Device_TBL
        WHERE dvcBuilding_FRK = :building_id AND dvcName_TXT LIKE '%Panel%'
    """
    row = fetch_one(sql, {"building_id": building_id})
    if not row or not row.get("dvccurrentstate_txt"):
        return "Unknown"

    state_text = row["dvccurrentstate_txt"]
    if 'AreaArmingStates.4' in state_text:
        return "Armed"
    elif 'AreaArmingStates.2' in state_text:
        return "Disarmed"
    else:
        return "Unknown"

def get_all_building_panel_states() -> Dict[int, str]:
    """
    Gets the panel state for all buildings.
    """
    buildings = get_distinct_buildings()
    building_states = {}
    for building in buildings:
        state = get_building_panel_state(building["id"])
        building_states[building["id"]] = state
    return building_states