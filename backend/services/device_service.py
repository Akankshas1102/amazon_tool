# backend/services/device_service.py

from typing import List, Dict, Any
from config import fetch_all, fetch_one
from sqlite_config import get_all_building_times
import logging
import time

logger = logging.getLogger(__name__)

# Simple in-memory cache for buildings to reduce database queries
buildings_cache = {
    "data": None,
    "timestamp": 0
}
CACHE_DURATION_SECONDS = 300  # Cache for 5 minutes


def get_distinct_buildings() -> List[Dict[str, Any]]:
    """
    Fetches a distinct list of buildings from the database.
    Uses time-based caching to avoid excessive database queries.
    
    Returns:
        List of building dictionaries with id, name, start_time, and end_time
    """
    # Check if cache is still valid
    is_cache_valid = (time.time() - buildings_cache["timestamp"]) < CACHE_DURATION_SECONDS
    
    if buildings_cache["data"] and is_cache_valid:
        logger.info("Returning buildings list from cache.")
        return buildings_cache["data"]

    logger.info("Fetching distinct buildings from database (cache empty or expired).")
    sql = """
        SELECT DISTINCT b.Building_PRK AS id, b.bldBuildingName_TXT AS name
        FROM Device_TBL d 
        JOIN Building_TBL b ON d.dvcBuilding_FRK = b.Building_PRK
        WHERE d.dvcBuilding_FRK IS NOT NULL AND d.dvcDeviceType_FRK = 138
        ORDER BY b.bldBuildingName_TXT
    """
    
    try:
        rows = fetch_all(sql)
        buildings = [dict(row) for row in rows]
        logger.info(f"Found {len(buildings)} distinct buildings.")
        
        # Merge with scheduled times from SQLite
        building_times = get_all_building_times()
        for building in buildings:
            times = building_times.get(building["id"])
            if times:
                building["start_time"] = times.get("start_time")
                building["end_time"] = times.get("end_time")
        
        # Update cache
        buildings_cache["data"] = buildings
        buildings_cache["timestamp"] = time.time()
        
        return buildings
    except Exception as e:
        logger.error(f"Error fetching buildings: {e}")
        # Return cached data if available even if expired
        return buildings_cache["data"] if buildings_cache["data"] else []


def get_building_panel_state(building_id: int) -> str:
    """
    Retrieves the current state of the alarm panel for a building.
    
    Args:
        building_id: The building ID to check
        
    Returns:
        State string: "Armed", "Disarmed", or "Unknown"
    """
    sql = """
        SELECT dvcCurrentState_TXT 
        FROM Device_TBL 
        WHERE dvcBuilding_FRK = :building_id AND dvcName_TXT LIKE '%Panel%'
    """
    
    try:
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
    except Exception as e:
        logger.error(f"Error fetching panel state for building {building_id}: {e}")
        return "Unknown"