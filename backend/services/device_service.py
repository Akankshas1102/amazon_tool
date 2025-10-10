# backend/services/device_service.py
from typing import List, Dict, Any
from config import fetch_all, fetch_one
from sqlite_config import get_all_building_times
import logging

logger = logging.getLogger(__name__)

def get_distinct_buildings() -> List[Dict[str, Any]]:
    sql = """
        SELECT DISTINCT b.Building_PRK AS id, b.bldBuildingName_TXT AS name
        FROM Device_TBL d JOIN Building_TBL b ON d.dvcBuilding_FRK = b.Building_PRK
        WHERE d.dvcBuilding_FRK IS NOT NULL AND d.dvcDeviceType_FRK=138
        ORDER BY b.bldBuildingName_TXT
    """
    rows = fetch_all(sql)
    buildings = [dict(row) for row in rows]
    building_times = get_all_building_times()
    for building in buildings:
        times = building_times.get(building["id"])
        if times:
            building["start_time"] = times.get("start_time")
            building["end_time"] = times.get("end_time")
    return buildings

def get_building_panel_state(building_id: int) -> str:
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