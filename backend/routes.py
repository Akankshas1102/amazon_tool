from fastapi import APIRouter, HTTPException, Query
from services import device_service, proevent_service
from models import (DeviceOut, DeviceActionRequest, DeviceActionSummaryResponse, 
                   BuildingOut, BuildingTimeRequest, BuildingTimeResponse)
from sqlite_config import get_building_time, set_building_time
from logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/buildings", response_model=list[BuildingOut])
def list_buildings():
    """
    Return distinct building identifiers from Device_TBL with scheduled times.
    """
    buildings = device_service.get_distinct_buildings()
    return [
        BuildingOut(
            id=b["id"],
            name=b["name"],
            scheduled_time=b.get("scheduled_time")
        )
        for b in buildings
    ]


@router.get("/devices", response_model=list[DeviceOut])
def list_devices(
    state: str | None = Query(default=None),
    building: int | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0)
):
    """
    Return devices optionally filtered by state, building, or search term.
    """
    devices = device_service.get_all_devices(
        state=state, building=building, search=search, limit=limit, offset=offset
    )
    return [
        DeviceOut(
            id=d["id"],
            name=d["name"],
            state=d.get("state") or "",
            building_name=d.get("building_name") or "Unknown"
        )
        for d in devices
    ]


@router.post("/devices/action", response_model=DeviceActionSummaryResponse)
def device_action(req: DeviceActionRequest):
    """
    Arm / Disarm action for a list of devices.
    """
    action = req.action.lower()
    results = []
    success_count = 0
    failure_count = 0

    for device_id in req.device_ids:
        try:
            proevent_id = device_service.get_linked_proevent_id(device_id)
            if not proevent_id:
                raise HTTPException(400, "No linked ProEvent found for device")

            current_state = (device_service.get_device_current_state(device_id) or "").lower()

            if action == "disarm" and current_state != "armed":
                raise HTTPException(400, "Device not in 'armed' state")

            reactive = 1 if action == "arm" else 0
            affected = proevent_service.set_proevent_reactive(proevent_id, reactive)
            if affected == 0:
                raise HTTPException(400, "No rows updated")

            results.append({
                "device_id": device_id,
                "status": "Success",
                "message": f"ProEvent updated (reactive={reactive})"
            })
            success_count += 1

        except HTTPException as e:
            results.append({
                "device_id": device_id,
                "status": "Failure",
                "message": e.detail
            })
            failure_count += 1

    return DeviceActionSummaryResponse(
        success_count=success_count,
        failure_count=failure_count,
        details=results
    )


@router.get("/buildings/{building_id}/time")
def get_building_scheduled_time(building_id: int):
    """
    Get the scheduled time for a specific building.
    """
    scheduled_time = get_building_time(building_id)
    return {
        "building_id": building_id,
        "scheduled_time": scheduled_time
    }


@router.post("/buildings/{building_id}/time", response_model=BuildingTimeResponse)
def set_building_scheduled_time(building_id: int, request: BuildingTimeRequest):
    """
    Set the scheduled time for a specific building.
    """
    if request.building_id != building_id:
        raise HTTPException(400, "Building ID in path and body must match")
    
    success = set_building_time(building_id, request.scheduled_time)
    if not success:
        raise HTTPException(500, "Failed to update building scheduled time")
    
    return BuildingTimeResponse(
        building_id=building_id,
        scheduled_time=request.scheduled_time,
        updated=True
    )