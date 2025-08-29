from pydantic import BaseModel

class Device(BaseModel):
    id: int
    name: str
    type: str

class ProEvent(BaseModel):
    id: int
    event_name: str
    description: str
