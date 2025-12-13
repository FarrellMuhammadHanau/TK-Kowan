from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt
import hashlib
import os

from db import SessionLocal, Institution, init_db
from schemas import RegisterRequest, LoginRequest, TokenResponse

JWT_SECRET = os.getenv("JWT_SECRET", "EfEmEitch123")
JWT_ALGORITHM = "HS256"

app = FastAPI()

async def get_db():
    async with SessionLocal() as session:
        yield session

@app.on_event("startup")
async def startup():
    await init_db()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hash: str) -> bool:
    return hash_password(password) == hash

def create_jwt(institution_id: str) -> str:
    payload = {
        "sub": institution_id,
        "role": "admin"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

@app.post("/register")
async def register(
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Institution).where(Institution.name == data.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Institution already exists")

    inst = Institution(
        name=data.name,
        password_hash=hash_password(data.password)
    )
    db.add(inst)
    await db.commit()

    return {"message": "registered"}

@app.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Institution).where(Institution.name == data.name)
    )
    inst = result.scalar_one_or_none()

    if not inst or not verify_password(data.password, inst.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")

    token = create_jwt(inst.id)
    return TokenResponse(access_token=token)