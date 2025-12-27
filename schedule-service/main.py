from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from jose import jwt, JWTError
import os
import httpx

from db import SessionLocal, Schedule, init_db
from schemas import (
    CreateScheduleRequest,
    CreateScheduleResponse,
    GetScheduleResponse,
    ScheduleResponseItem,
    ValidateAvailabilityRequest,
    ValidateAvailabilityResponse
)

# CONFIG
JWT_SECRET = os.getenv("JWT_SECRET", "EfEmEitch123")
JWT_ALGORITHM = "HS256"

# Defaulting to Deployed IPs for ease of development
ROOM_SERVICE_URL = os.getenv("ROOM_SERVICE_URL", "http://54.162.202.203:8000")
CLASS_SERVICE_URL = os.getenv("CLASS_SERVICE_URL", "http://3.225.88.17:8000")

security = HTTPBearer()
app = FastAPI()

# ---------- DB ----------
async def get_db():
    async with SessionLocal() as session:
        yield session

@app.on_event("startup")
async def startup():
    await init_db()

# ---------- JWT ----------
def get_institution_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM]
        )
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_raw_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    return credentials.credentials

# ---------- HELPER ----------
async def validate_external_id(
    service_url: str, 
    endpoint: str, 
    payload_key: str, 
    id_key: str, 
    id_val: str, 
    token: str
):
    """
    Generic helper to call validate-existence endpoints of other services.
    Returns the object name if found, None otherwise.
    """
    async with httpx.AsyncClient() as client:
        try:
            payload = {payload_key: [{id_key: id_val}]}
            resp = await client.post(
                f"{service_url}/{endpoint}",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            if not data.get("valid"):
                return None
            
            # Extract name (assuming structure: {items: [{id:..., name:...}]})
            items = data.get(payload_key, [])
            if items:
                return items[0].get("name")
            return None
            
        except Exception as e:
            print(f"Error calling {service_url}: {e}")
            return None

# ---------- API ----------

# 1. CREATE SCHEDULE
@app.post("/schedules/create", response_model=CreateScheduleResponse)
async def create_schedules(
    data: CreateScheduleRequest,
    institution_id: str = Depends(get_institution_id),
    token: str = Depends(get_raw_token),
    db: AsyncSession = Depends(get_db)
):
    for item in data.schedules:
        # A. Validate Room Existence
        room_name = await validate_external_id(
            ROOM_SERVICE_URL, "rooms/validate-existence", "rooms", "id", item.room_id, token
        )
        if not room_name:
            raise HTTPException(status_code=400, detail=f"Invalid Room ID: {item.room_id}")

        # B. Validate Class Existence
        class_name = await validate_external_id(
            CLASS_SERVICE_URL, "classes/validate-existence", "classes", "id", item.class_id, token
        )
        if not class_name:
            raise HTTPException(status_code=400, detail=f"Invalid Class ID: {item.class_id}")

        # C. Check Time Conflict (Same Room, Same Day, Overlapping Time)
        # Overlap Logic: (StartA < EndB) and (EndA > StartB)
        conflict = await db.execute(
            select(Schedule).where(
                Schedule.institution_id == institution_id,
                Schedule.room_id == item.room_id,
                Schedule.day == item.day,
                and_(
                    Schedule.start_time < item.end_time,
                    Schedule.end_time > item.start_time
                )
            )
        )
        if conflict.scalar_one_or_none():
            raise HTTPException(
                status_code=409, 
                detail=f"Room {room_name} is already booked on Day {item.day} between {item.start_time}-{item.end_time}"
            )

        # D. Save
        new_schedule = Schedule(
            institution_id=institution_id,
            room_id=item.room_id,
            room_name=room_name,
            class_id=item.class_id,
            class_name=class_name,
            day=item.day,
            start_time=item.start_time,
            end_time=item.end_time
        )
        db.add(new_schedule)
    
    await db.commit()
    return CreateScheduleResponse(message="successful")

# 2. GET SCHEDULES
@app.get("/schedules", response_model=GetScheduleResponse)
async def get_schedules(
    institution_id: str = Depends(get_institution_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Schedule).where(Schedule.institution_id == institution_id)
    )
    schedules = result.scalars().all()
    
    return GetScheduleResponse(
        schedules=[
            ScheduleResponseItem(
                id=s.id,
                room_id=s.room_id,
                room_name=s.room_name,
                class_id=s.class_id,
                class_name=s.class_name,
                day=s.day,
                start_time=s.start_time,
                end_time=s.end_time
            )
            for s in schedules
        ]
    )

# 3. VALIDATE AVAILABILITY
@app.post("/schedules/validate-availability", response_model=ValidateAvailabilityResponse)
async def validate_availability(
    data: ValidateAvailabilityRequest,
    institution_id: str = Depends(get_institution_id),
    db: AsyncSession = Depends(get_db)
):
    conflicts = []
    
    for item in data.schedules:
        result = await db.execute(
            select(Schedule).where(
                Schedule.institution_id == institution_id,
                Schedule.room_id == item.room_id,
                Schedule.day == item.day,
                and_(
                    Schedule.start_time < item.end_time,
                    Schedule.end_time > item.start_time
                )
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            conflicts.append({
                "room_id": item.room_id,
                "conflict_with_class": existing.class_name
            })
            
    if conflicts:
        return ValidateAvailabilityResponse(valid=False, conflicts=conflicts)
        
    return ValidateAvailabilityResponse(valid=True)
