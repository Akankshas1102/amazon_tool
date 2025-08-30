from pydantic import BaseModel, Field
from typing import Literal

class DeviceOut(BaseModel):
    id: int
    name: str
    state: str

class DeviceActionRequest(BaseModel):
    device_id: int = Field(..., gt=0)
    action: Literal["arm", "disarm"]

class DeviceActionResponse(BaseModel):
    device_id: int
    action: Literal["arm", "disarm"]
    proevent_id: int
    status: str
    message: str
