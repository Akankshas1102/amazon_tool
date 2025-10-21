# backend/routes.py

from fastapi import APIRouter, HTTPException, Query
from services import device_service, proevent_service, cache_service
from models import (DeviceOut, DeviceActionRequest, DeviceActionSummaryResponse,
                   BuildingOut, BuildingTimeRequest, BuildingTimeResponse,
                   IgnoredItemRequest, IgnoredItemResponse, IgnoredItemBulkRequest,
                   PanelStatus) # Import new PanelStatus model
from sqlite_config import (get_building_time, set_building_time,
                           get_ignored_proevents, set_proevent_ignore_status)
from logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


# --- NEW Panel Status Endpoints ---

@router.get("/panel_status", response_model=PanelStatus)
def get_panel_status():
    """
    Get the current global armed/disarmed status of the panel.
    """
    status = cache_service.get_cache_value('panel_armed')
    if status is None:
        # Default to armed if not set (should be set on startup, but as a fallback)
        logger.warning("Panel status not found in cache, defaulting to 'armed'.")
        status = True
        cache_service.set_cache_value('panel_armed', status)
    return PanelStatus(armed=status)

@router.post("/panel_status", response_model=PanelStatus)
def set_panel_status(status: PanelStatus):
    """
    Set the current global armed/disarmed status of the panel.
    """
    try:
        cache_service.set_cache_value('panel_armed', status.armed)
        logger.info(f"Global panel status set to: {'Armed' if status.armed else 'Disarmed'}")
        return status
    except Exception as e:
        logger.error(f"Failed to set panel status in cache: {e}")
        raise HTTPException(500, "Failed to update panel status")


# --- Existing Routes ---

@router.get("/buildings", response_model=list[BuildingOut])
def list_buildings():
    buildings = device_service.get_distinct_buildings()
    buildings_out = []
    for b in buildings:
        # If start_time or end_time is not set, provide a default value.
        start_time = b.get("start_time", "09:00")
        end_time = b.get("end_time", "17:00")

        buildings_out.append(BuildingOut(
            id=b["id"],
            name=b["name"],
            start_time=start_time,
            end_time=end_time
        ))
    return buildings_out


@router.get("/devices", response_model=list[DeviceOut])
def list_proevents(
    building: int | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0)
):
    if building is None:
        raise HTTPException(status_code=400, detail="A building ID is required.")

    proevents = proevent_service.get_all_proevents_for_building(
        building_id=building, search=search, limit=limit, offset=offset
    )

    ignored_proevents = get_ignored_proevents()

    proevents_out = []
    for p in proevents:
        ignore_status = ignored_proevents.get(p["id"], {})
        proevent_out = DeviceOut(
            id=p["id"],
            name=p["name"],
            state="armed" if p["reactive_state"] == 1 else "disarmed",
            building_name=None, # You might want to populate this from the building table
            is_ignored_on_arm=ignore_status.get("ignore_on_arm", False),
            is_ignored_on_disarm=ignore_status.get("ignore_on_disarm", False)
        )
        proevents_out.append(proevent_out)

    return proevents_out


@router.post("/devices/action", response_model=DeviceActionSummaryResponse)
def device_action(req: DeviceActionRequest):
    action = req.action.lower()
    reactive = 1 if action == "arm" else 0

    try:
        affected_rows = proevent_service.set_proevent_reactive_for_building(req.building_id, reactive)
        if affected_rows == 0:
            logger.warning(f"No proevents updated for building {req.building_id}.")
        return DeviceActionSummaryResponse(
            success_count=affected_rows,
            failure_count=0,
            details=[{"building_id": req.building_id, "status": "Success", "message": f"Updated {affected_rows} proevents"}]
        )
    except Exception as e:
        logger.error(f"Error during bulk action for building {req.building_id}: {e}")
        return DeviceActionSummaryResponse(
            success_count=0,
            failure_count=1,
            details=[{"building_id": req.building_id, "status": "Failure", "message": str(e)}]
        )


@router.get("/buildings/{building_id}/time")
def get_building_scheduled_time(building_id: int):
    times = get_building_time(building_id)
    return {
        "building_id": building_id,
        "start_time": times.get("start_time") if times else None,
        "end_time": times.get("end_time") if times else None
    }


@router.post("/buildings/{building_id}/time", response_model=BuildingTimeResponse)
def set_building_scheduled_time(building_id: int, request: BuildingTimeRequest):
    if request.building_id != building_id:
        raise HTTPException(400, "Building ID in path and body must match")
    success = set_building_time(building_id, request.start_time, request.end_time)
    if not success:
        raise HTTPException(500, "Failed to update building scheduled time")
    return BuildingTimeResponse(
        building_id=building_id,
        start_time=request.start_time,
        end_time=request.end_time,
        updated=True
    )

# UPDATED: Endpoint to handle new data
@router.post("/proevents/ignore", response_model=IgnoredItemResponse)
def manage_ignored_proevents(req: IgnoredItemRequest):
    """
    Set the ignore status for a proevent.
    """
    success = set_proevent_ignore_status(
        req.item_id, req.building_frk, req.device_prk, req.ignore_on_arm, req.ignore_on_disarm
    )

    if not success:
        raise HTTPException(500, f"Failed to update ignore status for proevent {req.item_id}")

    return IgnoredItemResponse(
        item_id=req.item_id,
        success=True
    )

# UPDATED: Endpoint to handle new data
@router.post("/proevents/ignore/bulk")
def manage_ignored_proevents_bulk(req: IgnoredItemBulkRequest):
    """
    Set the ignore status for multiple proevents.
    """
    for item in req.items:
        set_proevent_ignore_status(
            item.item_id, item.building_frk, item.device_prk, item.ignore_on_arm, item.ignore_on_disarm
        )

    return {"status": "success"}