from pydantic import BaseModel, Field
from typing import Literal, List

class BuildingOut(BaseModel):
    id: int
    name: str

class DeviceOut(BaseModel):
    id: int
    name: str
    state: str
    building_name: str | None = None

class DeviceActionRequest(BaseModel):
    device_ids: List[int] = Field(..., min_items=1)
    action: Literal["arm", "disarm"]

class DeviceActionSummaryResponse(BaseModel):
    success_count: int
    failure_count: int
    details: List[dict]