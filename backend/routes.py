from fastapi import APIRouter, HTTPException, Query
from services import device_service, proevent_service
from models import DeviceOut, DeviceActionRequest, DeviceActionResponse
from logger import get_logger
from collections import defaultdict

router = APIRouter()
logger = get_logger(__name__)


@router.get("/buildings")
def list_buildings():
    """
    Return distinct building identifiers from Device_TBL.
    """
    return device_service.get_distinct_buildings()


@router.get("/devices", response_model=list[DeviceOut])
def list_devices(
    state: str | None = Query(default=None),
    building: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0)
):
    """
    Return devices optionally filtered by state, building, or search term.
    Supports pagination via limit & offset.
    """
    devices = device_service.get_all_devices(
        state=state, building=building, search=search, limit=limit, offset=offset
    )
    return [
        DeviceOut(
            id=d["id"],
            name=d["name"],
            state=d.get("state") or "",
            building=d.get("building") or ""
        )
        for d in devices
    ]


@router.get("/devices/grouped")
def list_devices_grouped():
    """
    Return devices grouped by building.
    """
    devices = device_service.get_all_devices()
    grouped = defaultdict(list)
    for d in devices:
        grouped[d.get("building") or "Unknown"].append({
            "id": d["id"],
            "name": d["name"],
            "state": d.get("state") or ""
        })
    return grouped


@router.post("/devices/action", response_model=DeviceActionResponse)
def device_action(req: DeviceActionRequest):
    """
    Arm / Disarm action for a device.
    """
    device_id = req.device_id
    action = req.action.lower()

    proevent_id = device_service.get_linked_proevent_id(device_id)
    if not proevent_id:
        raise HTTPException(400, "No linked ProEvent found for device")

    current_state = (device_service.get_device_current_state(device_id) or "").lower()

    # Normalize state check
    if action == "disarm" and current_state != "armed":
        raise HTTPException(400, "Device not in 'armed' state")

    reactive = 1 if action == "arm" else 0
    affected = proevent_service.set_proevent_reactive(proevent_id, reactive)
    if affected == 0:
        raise HTTPException(400, "No rows updated")

    return DeviceActionResponse(
        device_id=device_id,
        action=action,
        proevent_id=proevent_id,
        status="Success",
        message=f"ProEvent updated (reactive={reactive})"
    )
