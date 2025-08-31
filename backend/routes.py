from fastapi import APIRouter, HTTPException, Query
from services import device_service, proevent_service
from models import DeviceOut, DeviceActionRequest, DeviceActionResponse
from logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


# ✅ GET /devices with optional ?state=
@router.get("/devices", response_model=list[DeviceOut])
def list_devices(state: str | None = Query(default=None)):
    if state:
        devices = device_service.get_all_devices(state)
    else:
        devices = device_service.get_all_devices()
    return [DeviceOut(**d) for d in devices]

@router.get("/devices/{device_id}/state")
def get_device_state(device_id: int):
    state = device_service.get_device_state(device_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"device_id": device_id, "state": state}


# ✅ POST /devices/action (arm/disarm)
@router.post("/devices/action", response_model=DeviceActionResponse)
def device_action(payload: DeviceActionRequest):
    device_id, action = payload.device_id, payload.action
    state = device_service.get_device_state(device_id)
    if not state:
        raise HTTPException(404, "Device not found")

    proevent_id = device_service.get_linked_proevent_id(device_id)
    if not proevent_id:
        raise HTTPException(404, "ProEvent not found")

    # Validate state before update
    if action == "arm" and "AreaArmingStates.4" not in state:
        return DeviceActionResponse(
            device_id=device_id,
            action=action,
            proevent_id=proevent_id,
            status="Skipped",
            message="Device not in 'arm' state"
        )
    if action == "disarm" and "AreaArmingStates.2" not in state:
        return DeviceActionResponse(
            device_id=device_id,
            action=action,
            proevent_id=proevent_id,
            status="Skipped",
            message="Device not in 'disarm' state"
        )

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
