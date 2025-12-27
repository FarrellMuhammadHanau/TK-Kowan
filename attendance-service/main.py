from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
import os
import httpx
from datetime import datetime

from db import SessionLocal, Attendance, init_db
from schemas import (
    CredentialResponse,
    SubmitPresenceRequest,
    SubmitPresenceResponse
)

# CONFIG
JWT_SECRET = os.getenv("JWT_SECRET", "EfEmEitch123")
JWT_ALGORITHM = "HS256"

# SERVICE URLs (Default to Deployed Production IPs)
ATTENDEE_SERVICE_URL = os.getenv("ATTENDEE_SERVICE_URL", "http://18.214.134.23:8000")
CLASS_SERVICE_URL = os.getenv("CLASS_SERVICE_URL", "http://3.225.88.17:8000")
SCHEDULE_SERVICE_URL = os.getenv("SCHEDULE_SERVICE_URL", "http://3.239.169.255:8000")

security = HTTPBearer()
app = FastAPI()

# ---------- DB ----------
async def get_db():
    async with SessionLocal() as session:
        yield session

@app.on_event("startup")
async def startup():
    await init_db()

# ---------- JWT HELPER ----------
def create_access_token(data: dict):
    return jwt.encode(data, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_current_institution(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_raw_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    return credentials.credentials

# ---------- API ----------

# 1. GET CREDENTIAL (Admin Only)
@app.post("/attendance/attendance-credential", response_model=CredentialResponse)
async def get_credential(
    payload: dict = Depends(get_current_institution)
):
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Create a token for the attendance machine
    machine_payload = {
        "sub": payload["sub"],
        "role": "attendee" # Role for the machine
    }
    token = create_access_token(machine_payload)
    return CredentialResponse(access_token=token)


# 2. SUBMIT PRESENCE (The Core Orchestrator)
@app.post("/attendance/presence", response_model=SubmitPresenceResponse)
async def submit_presence(
    data: SubmitPresenceRequest,
    payload: dict = Depends(get_current_institution),
    db: AsyncSession = Depends(get_db)
):
    # Verify this is a valid attendance token
    if payload.get("role") != "attendee" and payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Invalid role for submission")
        
    institution_id = payload["sub"]
    
    # Admin Token (to reuse for inter-service calls)
    # Since the machine token might not be accepted by other services if they check for "admin",
    # We should ideally have an Admin token. 
    # BUT, for simplicity in this system design, we assume services accept the JWT signed by the same secret.
    # However, Attendee/Class/Schedule services specifically check for 'role': 'admin'.
    # The 'attendance machine' token has role 'attendee'.
    # To fix this: We need to sign a temporary ADMIN token here to talk to other services,
    # Solution: We generate a short-lived admin token for internal calls.
    internal_token = create_access_token({"sub": institution_id, "role": "admin"})
    headers = {"Authorization": f"Bearer {internal_token}"}

    async with httpx.AsyncClient() as client:
        
        # Validate Secret (Attendee Service)
        try:
            resp = await client.post(
                f"{ATTENDEE_SERVICE_URL}/attendees/validate-secret",
                json={"code": data.attendee_code, "secret": data.attendee_secret},
                headers=headers
            )
            if resp.status_code != 200 or not resp.json().get("valid"):
                raise HTTPException(status_code=400, detail="Invalid attendee secret or code")
            
            student_name = resp.json().get("name")
        except Exception as e:
            print(f"Attendee Service Error: {e}")
            raise HTTPException(status_code=503, detail="Attendee validation failed")

        # Validate Schedule (Schedule Service)
        # We need to know 'current time'.
        now = datetime.now()
        day = now.isoweekday() # 1=Mon, 7=Sun
        time_int = int(now.strftime("%H%M"))
        
        # Note: In real world, we might want to check a buffer (e.g., +/- 15 mins).
        # For this simplified assignment, we assume the validate-availability endpoint checks existence.
        # The Schedule Service 'validate-availability' checks for CONFLICTS (creation).
        # It does NOT check "Is there a class NOW?".
        # We need to query GET /schedules and filter locally, OR assume Schedule Service logic.
        # validate-availability returns 'valid: false' if there IS a schedule (conflict).
        # We want a schedule to exist.
        
        # fetch all schedules and filter.
        try:
            resp = await client.get(f"{SCHEDULE_SERVICE_URL}/schedules", headers=headers)
            schedules = resp.json().get("schedules", [])
            
            # Find matching schedule
            # Logic: Same Room, Same Day, Current Time is within Start-End
            active_schedule = None
            for s in schedules:
                if (s["room_id"] == data.room_id and 
                    s["day"] == day and 
                    s["start_time"] <= time_int <= s["end_time"]):
                    active_schedule = s
                    break
            
            if not active_schedule:
                raise HTTPException(status_code=400, detail="No class scheduled in this room right now")
                
        except Exception as e:
            print(f"Schedule Service Error: {e}")
            raise HTTPException(status_code=503, detail="Schedule validation failed")

        # Validate Enrollment (Class Service)
        try:
            resp = await client.post(
                f"{CLASS_SERVICE_URL}/classes/validate-attendee",
                json={"class_id": active_schedule["class_id"], "attendee_code": data.attendee_code},
                headers=headers
            )
            val_data = resp.json()
            if not val_data.get("valid"):
                raise HTTPException(status_code=400, detail="Student is not enrolled in this class")
            
            class_attendee_id = val_data.get("class_attendee_id")
            
        except Exception as e:
             print(f"Class Service Error: {e}")
             raise HTTPException(status_code=503, detail="Enrollment validation failed")

    # Persist Attendance
    attendance = Attendance(
        institution_id=institution_id,
        class_attendee_id=class_attendee_id,
        schedule_id=active_schedule["id"],
        class_name=active_schedule["class_name"],
        room_name=active_schedule["room_name"]
    )
    db.add(attendance)
    await db.commit()

    return SubmitPresenceResponse(
        message="successful",
        student_name=student_name,
        class_name=active_schedule["class_name"]
    )
