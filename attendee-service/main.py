from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
import secrets
import string
import hashlib
import os

from db import SessionLocal, Attendee, init_db
from schemas import (
    CreateAttendeesRequest,
    AttendeeCreateResponse,
    GetAttendeeResponse,
    ValidateExistenceRequest,
    ValidateSecretRequest,
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

# ---------- SECRET ----------
def generate_secret(length: int = 8) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))

def hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()

def verify_secret(secret: str, secret_hash: str) -> bool:
    return hash_secret(secret) == secret_hash

# ---------- API ----------

# CREATE ATTENDEES (BULK)
@app.post("/attendees", response_model=list[AttendeeCreateResponse])
async def create_attendees(
    data: CreateAttendeesRequest,
    institution_id: str = Depends(get_institution_id),
    db: AsyncSession = Depends(get_db)
):
    responses = []

    for item in data.attendees:
        exists = await db.execute(
            select(Attendee).where(
                Attendee.institution_id == institution_id,
                Attendee.code == item.code
            )
        )
        if exists.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Attendee code already exists"
            )

        secret = generate_secret()
        attendee = Attendee(
            institution_id=institution_id,
            code=item.code,
            name=item.name,
            secret_hash=hash_secret(secret)
        )

        db.add(attendee)
        responses.append(
            AttendeeCreateResponse(code=item.code, secret=secret)
        )

    await db.commit()
    return responses

# GET ALL ATTENDEES
@app.get("/attendees", response_model=list[GetAttendeeResponse])
async def get_attendees(
    institution_id: str = Depends(get_institution_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Attendee).where(
            Attendee.institution_id == institution_id
        )
    )
    attendees = result.scalars().all()

    return [
        GetAttendeeResponse(code=a.code, name=a.name)
        for a in attendees
    ]

# VALIDATE EXISTENCE (BATCH) -> RETURN LIST CODE + NAME
@app.post("/attendees/validate-existence", response_model=ValidateResponse)
async def validate_existence(
    data: ValidateExistenceRequest,
    institution_id: str = Depends(get_institution_id),
    db: AsyncSession = Depends(get_db)
):
    codes = [item.code for item in data.attendees]

    if not codes:
        return ValidateResponse(valid=True, attendees=[])

    result = await db.execute(
        select(Attendee).where(
            Attendee.institution_id == institution_id,
            Attendee.code.in_(codes)
        )
    )
    found = result.scalars().all()

    if len(found) != len(set(codes)):
        return ValidateResponse(valid=False)

    return ValidateResponse(
        valid=True,
        attendees=[
            {"code": a.code, "name": a.name}
            for a in found
        ]
    )

# VALIDATE SECRET (SINGLE) -> RETURN CODE + NAME
@app.post("/attendees/validate-secret", response_model=ValidateResponse)
async def validate_secret(
    data: ValidateSecretRequest,
    institution_id: str = Depends(get_institution_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Attendee).where(
            Attendee.institution_id == institution_id,
            Attendee.code == data.code
        )
    )
    attendee = result.scalar_one_or_none()

    if not attendee:
        return ValidateResponse(valid=False)

    if not verify_secret(data.secret, attendee.secret_hash):
        return ValidateResponse(valid=False)

    return ValidateResponse(
        valid=True,
        code=attendee.code,
        name=attendee.name
    )