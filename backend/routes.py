from fastapi import APIRouter
from models import Device, ProEvent
from services.device_service import get_devices, add_device
from services.proevent_service import get_proevents, add_proevent
from services.cache_service import get_cache_value, set_cache_value

router = APIRouter()

@router.get("/devices")
def list_devices():
    return get_devices()

@router.post("/devices")
def create_device(device: Device):
    return add_device(device)

@router.get("/proevents")
def list_proevents():
    return get_proevents()

@router.post("/proevents")
def create_proevent(proevent: ProEvent):
    return add_proevent(proevent)

@router.get("/cache/{key}")
def read_cache(key: str):
    return {"value": get_cache_value(key)}

@router.post("/cache/{key}")
def write_cache(key: str, value: str):
    set_cache_value(key, value)
    return {"status": "success", "key": key, "value": value}
