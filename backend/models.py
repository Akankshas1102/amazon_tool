# backend/models.py

from pydantic import BaseModel, Field
from typing import Literal, List, Optional

class BuildingOut(BaseModel):
    id: int
    name: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None

class DeviceOut(BaseModel):
    id: int
    name: str
    state: str
    building_name: str | None = None
    is_ignored: bool = False # Field re-added

class DeviceActionRequest(BaseModel):
    building_id: int
    action: Literal["arm", "disarm"]

class DeviceActionSummaryResponse(BaseModel):
    success_count: int
    failure_count: int
    details: List[dict]

class BuildingTimeRequest(BaseModel):
    building_id: int
    start_time: str = Field(..., pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")
    end_time: Optional[str] = Field(None, pattern=r"^([01]?[0-9]|2[0-3]):[0-5][0-9]$")

class BuildingTimeResponse(BaseModel):
    building_id: int
    start_time: str
    end_time: Optional[str]
    updated: bool

# --- New Models for Ignored ProEvents ---

class IgnoredItemRequest(BaseModel):
    item_id: int
    action: Literal["ignore", "unignore"]

class IgnoredItemResponse(BaseModel):
    item_id: int
    action: str
    success: bool