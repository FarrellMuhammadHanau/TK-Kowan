from pydantic import BaseModel
from typing import List, Optional

# ---------- CREATE ----------
class AttendeeCreate(BaseModel):
    code: str
    name: str

class CreateAttendeesRequest(BaseModel):
    attendees: List[AttendeeCreate]

class AttendeeCreateResponse(BaseModel):
    code: str
    secret: str


# ---------- GET ----------
class GetAttendeeResponse(BaseModel):
    code: str
    name: str


# ---------- VALIDATE EXISTENCE (BATCH) ----------
class AttendeeExistenceItem(BaseModel):
    code: str

class ValidateExistenceRequest(BaseModel):
    attendees: List[AttendeeExistenceItem]


# ---------- VALIDATE SECRET (SINGLE) ----------
class ValidateSecretRequest(BaseModel):
    code: str
    secret: str


# ---------- VALIDATE RESPONSE (DIPAKAI DUA ENDPOINT) ----------
class ValidateResponse(BaseModel):
    valid: bool
    attendees: Optional[List[GetAttendeeResponse]] = None
    code: Optional[str] = None
    name: Optional[str] = None
