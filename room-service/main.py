from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
import os

from db import SessionLocal, Room, init_db
from schemas import (
    CreateRoomsRequest,
    CreateRoomsResponse,
    GetRoomResponse,
    ValidateExistenceRequest,
    ValidateResponse
)

JWT_SECRET = os.getenv("JWT_SECRET", "EfEmEitch123")
JWT_ALGORITHM = "HS256"

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
        
        # Validasi role admin
        if payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        return payload["sub"]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ---------- API ----------

# CREATE ROOMS (BULK)
@app.post("/rooms/create", response_model=CreateRoomsResponse)
async def create_rooms(
    data: CreateRoomsRequest,
    institution_id: str = Depends(get_institution_id),
    db: AsyncSession = Depends(get_db)
):
    for item in data.rooms:
        room = Room(
            institution_id=institution_id,
            room_name=item.name
        )
        db.add(room)
    
    await db.commit()
    return CreateRoomsResponse(message="successful")

# GET ALL ROOMS
@app.get("/rooms", response_model=list[GetRoomResponse])
async def get_rooms(
    institution_id: str = Depends(get_institution_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Room).where(
            Room.institution_id == institution_id
        )
    )
    rooms = result.scalars().all()
    
    return [
        GetRoomResponse(id=r.id, name=r.room_name)
        for r in rooms
    ]

# VALIDATE EXISTENCE (BATCH)
@app.post("/rooms/validate-existence", response_model=ValidateResponse)
async def validate_existence(
    data: ValidateExistenceRequest,
    institution_id: str = Depends(get_institution_id),
    db: AsyncSession = Depends(get_db)
):
    room_ids = [item.id for item in data.rooms]
    
    if not room_ids:
        return ValidateResponse(valid=True, rooms=[])
    
    result = await db.execute(
        select(Room).where(
            Room.institution_id == institution_id,
            Room.id.in_(room_ids)
        )
    )
    found = result.scalars().all()
    
    if len(found) != len(set(room_ids)):
        return ValidateResponse(valid=False)
    
    return ValidateResponse(
        valid=True,
        rooms=[
            {"id": r.id, "name": r.room_name}
            for r in found
        ]
    )