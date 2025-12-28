from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
import os
import httpx
from datetime import datetime
from zoneinfo import ZoneInfo

from db import SessionLocal, Attendance, init_db
from schemas import (
    GetCredentialRequest,
    CredentialResponse,
    SubmitPresenceRequest,
    SubmitPresenceResponse
)

# CONFIG
JWT_SECRET = os.getenv("JWT_SECRET", "EfEmEitch123")
JWT_ALGORITHM = "HS256"
TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Asia/Jakarta"))

# SERVICE URLs (Default to Deployed Production IPs)
ATTENDEE_SERVICE_URL = os.getenv("ATTENDEE_SERVICE_URL", "http://18.214.134.23:8000")
CLASS_SERVICE_URL = os.getenv("CLASS_SERVICE_URL", "http://3.225.88.17:8000")
SCHEDULE_SERVICE_URL = os.getenv("SCHEDULE_SERVICE_URL", "http://35.171.134.244:8000")
ROOM_SERVICE_URL = os.getenv("ROOM_SERVICE_URL", "http://54.162.202.203:8000")

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
    data: GetCredentialRequest,
    payload: dict = Depends(get_current_institution)
):
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Fetch room name from room service
    room_name = None
    institution_name = payload.get("institution_name")  # Get from JWT (backward compatible)
    
    try:
        internal_token = create_access_token({"sub": payload["sub"], "role": "admin"})
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{ROOM_SERVICE_URL}/rooms",
                headers={"Authorization": f"Bearer {internal_token}"}
            )
            if resp.status_code == 200:
                rooms = resp.json()
                for room in rooms:
                    if room["id"] == data.room_id:
                        room_name = room["name"]
                        break
    except Exception as e:
        print(f"Failed to fetch room name: {e}")
    
    # Create a token for the attendance machine bound to specific room
    machine_payload = {
        "sub": payload["sub"],
        "role": "attendee",
        "room": data.room_id,
        "room_name": room_name,  # (optional, backward compatible)
        "institution_name": institution_name  # (optional, backward compatible)
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
    
    # Extract room_id from JWT token (not from request body)
    room_id = payload.get("room")
    if not room_id:
        raise HTTPException(status_code=400, detail="Token does not contain room information")
    
    # Admin Token (to reuse for inter-service calls)
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
        now = datetime.now(TIMEZONE)
        day = now.isoweekday()
        time_int = int(now.strftime("%H%M"))
        
        try:
            resp = await client.get(f"{SCHEDULE_SERVICE_URL}/schedules", headers=headers)
            resp.raise_for_status()
            schedules = resp.json().get("schedules", [])
            
            print(f"Current time: {now} (Day {day}, Time {time_int})")
            print(f"Room ID to match: {room_id}")
            print(f"Total schedules retrieved: {len(schedules)}")
            
            active_schedule = None
            for s in schedules:
                if s["room_id"] == room_id:
                    print(f"Found schedule for this room: Day {s['day']}, {s['start_time']}-{s['end_time']}")
                
                if (s["room_id"] == room_id and 
                    s["day"] == day and 
                    s["start_time"] <= time_int <= s["end_time"]):
                    active_schedule = s
                    break
            
            if not active_schedule:
                print(f"No matching schedule found. Looking for: room={room_id}, day={day}, time={time_int}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"No class scheduled in this room right now (Day {day}, Time {time_int})"
                )
                
        except HTTPException:
            raise
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