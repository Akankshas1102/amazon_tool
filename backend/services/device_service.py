from typing import List, Dict, Any
from config import fetch_all, fetch_one
from sqlite_config import get_building_time, get_all_building_times
import logging

logger = logging.getLogger(__name__)


def get_all_devices(
    state: str | None = None,
    building: int | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    where_clauses = []
    params = {}

    if state:
        where_clauses.append("LOWER(d.dvcCurrentState_TXT) LIKE LOWER(:state)")
        params["state"] = f"%{state}%"

    if building:
        where_clauses.append("d.dvcBuilding_FRK = :building")
        params["building"] = building

    if search:
        where_clauses.append("(LOWER(d.dvcName_TXT) LIKE LOWER(:search) OR LOWER(d.dvcCurrentState_TXT) LIKE LOWER(:search))")
        params["search"] = f"%{search}%"

    sql = """
        SELECT
            d.Device_PRK AS id,
            d.dvcName_TXT AS name,
            d.dvcCurrentState_TXT AS state,
            b.Bldbuildingname_TXT AS building_name
        FROM Device_TBL d
        LEFT JOIN Building_TBL b ON d.dvcBuilding_FRK = b.Building_PRK
    """

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    sql += " ORDER BY d.dvcName_TXT OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY"
    params.update({"limit": limit, "offset": offset})

    rows = fetch_all(sql, params)
    return [dict(row) for row in rows]


def get_distinct_buildings() -> List[Dict[str, Any]]:
    """
    Return distinct buildings (ID and Name) that have devices, with scheduled times.
    """
    sql = """
        SELECT DISTINCT
            b.Building_PRK AS id,
            b.Bldbuildingname_TXT AS name
        FROM Device_TBL d
        JOIN Building_TBL b ON d.dvcBuilding_FRK = b.Building_PRK
        WHERE d.dvcBuilding_FRK IS NOT NULL
        ORDER BY b.Bldbuildingname_TXT
    """
    rows = fetch_all(sql)
    buildings = [dict(row) for row in rows]
    
    # Get all building times from SQLite
    building_times = get_all_building_times()
    
    # Add scheduled_time to each building
    for building in buildings:
        building["scheduled_time"] = building_times.get(building["id"])
    
    return buildings


def get_linked_proevent_id(device_id: int) -> int | None:
    sql = "SELECT dstProEvent_FRK FROM DeviceStateLink_TBL WHERE dstDevice_FRK = :device_id"
    row = fetch_one(sql, {"device_id": device_id})
    return row.get("dstProEvent_FRK") if row else None


def get_device_current_state(device_id: int) -> str | None:
    sql = "SELECT dvcCurrentState_TXT AS state FROM Device_TBL WHERE Device_PRK = :device_id"
    row = fetch_one(sql, {"device_id": device_id})
    return row.get("state") if row else None