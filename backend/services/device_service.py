# backend/services/device_service.py

from typing import List, Dict, Any
from config import fetch_all, fetch_one
from sqlite_config import get_all_building_times # Corrected import
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_distinct_buildings() -> List[Dict[str, Any]]:
    """
    Return distinct buildings (ID and Name) that have devices, with scheduled times.
    """
    sql = """
        SELECT DISTINCT
            b.Building_PRK AS id,
            b.bldBuildingName_TXT AS name
        FROM Device_TBL d
        JOIN Building_TBL b ON d.dvcBuilding_FRK = b.Building_PRK
        WHERE d.dvcBuilding_FRK IS NOT NULL
        and d.dvcDeviceType_FRK=138
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