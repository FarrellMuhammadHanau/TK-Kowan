from pydantic import BaseModel
from typing import List, Optional

# ---------- CREATE CLASSES ----------
class ClassCreateItem(BaseModel):
    code: str
    name: str

class CreateClassesRequest(BaseModel):
    classes: List[ClassCreateItem]

class CreateClassesResponse(BaseModel):
    message: str


# ---------- GET CLASSES ----------
class GetClassResponse(BaseModel):
    id: str
    code: str
    name: str


# ---------- ADD ATTENDEES ----------
class AddAttendeesRequest(BaseModel):
    class_id: str
    attendees: List[dict] # Expecting [{"code": "string"}]


# ---------- VALIDATE ATTENDEE IN CLASS ----------
class ValidateAttendeeRequest(BaseModel):
    class_id: str
    attendee_code: str

class ValidateAttendeeResponse(BaseModel):
    valid: bool
    class_attendee_id: Optional[str] = None
    class_name: Optional[str] = None


# ---------- VALIDATE CLASS EXISTENCE ----------
class ValidateClassItem(BaseModel):
    id: str

class ValidateClassExistenceRequest(BaseModel):
    classes: List[ValidateClassItem]

class ValidateClassExistenceResponse(BaseModel):
    valid: bool
    classes: List[dict] = []
