from typing import List, Dict, Any
from config import fetch_all, fetch_one
import logging

logger = logging.getLogger(__name__)


def get_all_devices(
    state: str | None = None,
    building: str | None = None,
    search: str | None = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Fetch devices from Device_TBL with optional filters:
      - state: partial match against dvcCurrentState_TXT
      - building: exact match against dvcBuilding_FRK
      - search: partial match against dvcName_TXT or dvcCurrentState_TXT
    Supports pagination via limit/offset.
    """
    where_clauses = []
    params = {}

    if state:
        where_clauses.append("LOWER(dvcCurrentState_TXT) LIKE LOWER(:state)")
        params["state"] = f"%{state}%"

    if building:
        where_clauses.append("dvcBuilding_FRK = :building")
        params["building"] = building

    if search:
        where_clauses.append("(LOWER(dvcName_TXT) LIKE LOWER(:search) OR LOWER(dvcCurrentState_TXT) LIKE LOWER(:search))")
        params["search"] = f"%{search}%"

    sql = """
        SELECT Device_PRK AS id,
               dvcName_TXT AS name,
               dvcDeviceType_FRK AS device_type,
               dvcCurrentState_TXT AS state,
               dvcBuilding_FRK AS building
        FROM Device_TBL
    """

    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    sql += " ORDER BY dvcName_TXT OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY"
    params.update({"limit": limit, "offset": offset})

    rows = fetch_all(sql, params)
    result = []
    for r in rows:
        result.append({
            "id": r.get("id"),
            "name": r.get("name") or "",
            "state": r.get("state") or "",
            "device_type": r.get("device_type") or "",
            "building": r.get("building") or ""
        })
    return result


def get_distinct_buildings() -> List[str]:
    """
    Return distinct building identifiers from Device_TBL.
    """
    sql = """
        SELECT DISTINCT dvcBuilding_FRK AS building
        FROM Device_TBL
        WHERE dvcBuilding_FRK IS NOT NULL
        ORDER BY dvcBuilding_FRK
    """
    rows = fetch_all(sql)
    return [r["building"] for r in rows]


def get_linked_proevent_id(device_id: int) -> int | None:
    """
    Retrieves the linked ProEvent ID for a given device ID.
    """
    sql = "SELECT dstProEvent_FRK FROM DeviceStateLink_TBL WHERE dstDevice_FRK = :device_id"
    row = fetch_one(sql, {"device_id": device_id})
    return row.get("dstProEvent_FRK") if row else None


def get_device_current_state(device_id: int) -> str | None:
    """
    Return the current state for a device.
    """
    sql = "SELECT dvcCurrentState_TXT AS state FROM Device_TBL WHERE Device_PRK = :device_id"
    row = fetch_one(sql, {"device_id": device_id})
    return row.get("state") if row else None
