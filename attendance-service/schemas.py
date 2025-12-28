from pydantic import BaseModel
from typing import Optional

# ---------- CREDENTIAL ----------
class GetCredentialRequest(BaseModel):
    room_id: str

class CredentialResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ---------- SUBMIT PRESENCE ----------
class SubmitPresenceRequest(BaseModel):
    attendee_code: str
    attendee_secret: str

class SubmitPresenceResponse(BaseModel):
    message: str
    student_name: Optional[str] = None
    class_name: Optional[str] = None
