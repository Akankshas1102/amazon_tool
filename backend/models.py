from pydantic import BaseModel, Field
from typing import Literal, List, Optional
from datetime import time

class BuildingOut(BaseModel):
    id: int
    name: str
    scheduled_time: Optional[str] = None  # Format: "HH:MM"

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

class BuildingTimeRequest(BaseModel):
    building_id: int
    scheduled_time: str = Field(..., pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")  # HH:MM format

class BuildingTimeResponse(BaseModel):
    building_id: int
    scheduled_time: str
    updated: bool