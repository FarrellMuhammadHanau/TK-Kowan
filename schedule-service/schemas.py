from pydantic import BaseModel
from typing import List, Optional

# ---------- CREATE ----------
class ScheduleCreateItem(BaseModel):
    room_id: str
    class_id: str
    day: int
    start_time: int
    end_time: int

class CreateScheduleRequest(BaseModel):
    schedules: List[ScheduleCreateItem]

class CreateScheduleResponse(BaseModel):
    message: str

# ---------- GET ----------
class ScheduleResponseItem(BaseModel):
    id: str
    room_id: str
    room_name: Optional[str] = None
    class_id: str
    class_name: Optional[str] = None
    day: int
    start_time: int
    end_time: int

class GetScheduleResponse(BaseModel):
    schedules: List[ScheduleResponseItem]

# ---------- VALIDATE AVAILABILITY ----------
class ValidateAvailabilityItem(BaseModel):
    room_id: str
    day: int
    start_time: int
    end_time: int

class ValidateAvailabilityRequest(BaseModel):
    schedules: List[ValidateAvailabilityItem]

class ValidateAvailabilityResponse(BaseModel):
    valid: bool
    conflicts: List[dict] = []
