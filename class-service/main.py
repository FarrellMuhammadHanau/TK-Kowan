from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
import os
import httpx

from db import SessionLocal, Class, ClassAttendee, init_db
from schemas import (
    CreateClassesRequest,
    CreateClassesResponse,
    GetClassResponse,
    AddAttendeesRequest,
    GetClassAttendeesResponse,
    ValidateAttendeeRequest,
    ValidateAttendeeResponse,
    ValidateClassExistenceRequest,
    ValidateClassExistenceResponse
)

JWT_SECRET = os.getenv("JWT_SECRET", "EfEmEitch123")
JWT_ALGORITHM = "HS256"
ATTENDEE_SERVICE_URL = os.getenv("ATTENDEE_SERVICE_URL", "http://18.214.134.23:8000")

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

# ---------- API ----------

# 1. CREATE CLASSES
@app.post("/classes/create", response_model=CreateClassesResponse)
async def create_classes(
    data: CreateClassesRequest,
    institution_id: str = Depends(get_institution_id),
    db: AsyncSession = Depends(get_db)
):
    for item in data.classes:
        # Optional: Check for duplicate code within institution
        exists = await db.execute(
            select(Class).where(
                Class.institution_id == institution_id,
                Class.code == item.code
            )
        )
        if exists.scalar_one_or_none():
            continue # Skip duplicates or raise error based on preference

        new_class = Class(
            institution_id=institution_id,
            code=item.code,
            name=item.name
        )
        db.add(new_class)
    
    await db.commit()
    return CreateClassesResponse(message="successful")

# 2. GET CLASSES
@app.get("/classes", response_model=list[GetClassResponse])
async def get_classes(
    institution_id: str = Depends(get_institution_id),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Class).where(Class.institution_id == institution_id)
    )
    classes = result.scalars().all()
    
    return [
        GetClassResponse(id=c.id, code=c.code, name=c.name)
        for c in classes
    ]

# 3. GET ATTENDEES FOR A CLASS
@app.get("/classes/{class_id}/attendees")
async def get_class_attendees(
    class_id: str,
    institution_id: str = Depends(get_institution_id),
    token: str = Depends(get_raw_token),
    db: AsyncSession = Depends(get_db)
):
    # Verify class exists and belongs to institution
    result = await db.execute(
        select(Class).where(
            Class.id == class_id,
            Class.institution_id == institution_id
        )
    )
    class_obj = result.scalar_one_or_none()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Get all attendee codes for this class
    result = await db.execute(
        select(ClassAttendee.attendee_code).where(
            ClassAttendee.class_id == class_id,
            ClassAttendee.institution_id == institution_id
        )
    )
    attendee_codes = [row[0] for row in result.all()]
    
    if not attendee_codes:
        return {"attendees": []}
    
    # Fetch attendee details from attendee service
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{ATTENDEE_SERVICE_URL}/attendees/validate-existence",
                json={"attendees": [{"code": code} for code in attendee_codes]},
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            validation_data = response.json()
            
            if validation_data.get("valid"):
                return {"attendees": validation_data.get("attendees", [])}
            else:
                # Even if validation fails, return the codes we have
                return {"attendees": [{"code": code, "name": "Unknown"} for code in attendee_codes]}
        except (httpx.RequestError, httpx.HTTPStatusError):
            # If attendee service is unavailable, return codes only
            return {"attendees": [{"code": code, "name": "Unknown"} for code in attendee_codes]}

# 4. ADD ATTENDEES TO CLASS
@app.post("/classes/add-attendees")
async def add_attendees(
    data: AddAttendeesRequest,
    institution_id: str = Depends(get_institution_id),
    token: str = Depends(get_raw_token),
    db: AsyncSession = Depends(get_db)
):
    # A. Validate Class
    result = await db.execute(
        select(Class).where(
            Class.id == data.class_id,
            Class.institution_id == institution_id
        )
    )
    class_obj = result.scalar_one_or_none()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    # B. Validate Attendees (Call External Service)
    # Prepare payload for attendee-service
    attendee_codes = [item['code'] for item in data.attendees]
    validation_payload = {
        "attendees": [{"code": code} for code in attendee_codes]
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{ATTENDEE_SERVICE_URL}/attendees/validate-existence",
                json=validation_payload,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            validation_data = response.json()
        except httpx.RequestError:
             raise HTTPException(status_code=503, detail="Attendee service unavailable")
        except httpx.HTTPStatusError:
             raise HTTPException(status_code=400, detail="Attendee validation failed")

    if not validation_data.get("valid"):
        raise HTTPException(status_code=400, detail="One or more attendees invalid")

    # C. Add to Database
    for code in attendee_codes:
        # Check if already in class
        exists = await db.execute(
            select(ClassAttendee).where(
                ClassAttendee.class_id == data.class_id,
                ClassAttendee.attendee_code == code
            )
        )
        if not exists.scalar_one_or_none():
            link = ClassAttendee(
                institution_id=institution_id,
                class_id=data.class_id,
                attendee_code=code
            )
            db.add(link)

    await db.commit()
    return {"message": "successful"}

# 4b. GET ATTENDEES IN CLASS
@app.get("/classes/{class_id}/attendees", response_model=GetClassAttendeesResponse)
async def get_class_attendees(
    class_id: str,
    institution_id: str = Depends(get_institution_id),
    token: str = Depends(get_raw_token),
    db: AsyncSession = Depends(get_db)
):
    # Verify class exists
    result = await db.execute(
        select(Class).where(
            Class.id == class_id,
            Class.institution_id == institution_id
        )
    )
    class_obj = result.scalar_one_or_none()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Get all attendee codes for this class
    result = await db.execute(
        select(ClassAttendee).where(
            ClassAttendee.class_id == class_id,
            ClassAttendee.institution_id == institution_id
        )
    )
    class_attendees = result.scalars().all()
    
    if not class_attendees:
        return GetClassAttendeesResponse(attendees=[])
    
    # Get attendee details from Attendee Service
    attendee_codes = [ca.attendee_code for ca in class_attendees]
    
    attendees_with_names = []
    async with httpx.AsyncClient() as client:
        try:
            # Call attendee service to get names
            response = await client.post(
                f"{ATTENDEE_SERVICE_URL}/attendees/validate-existence",
                json={"attendees": [{"code": code} for code in attendee_codes]},
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                validation_data = response.json()
                if validation_data.get("valid"):
                    attendees_with_names = validation_data.get("attendees", [])
                else:
                    # If validation fails, return codes without names
                    attendees_with_names = [{"code": code, "name": code} for code in attendee_codes]
            else:
                # Fallback: return codes as names
                attendees_with_names = [{"code": code, "name": code} for code in attendee_codes]
        except Exception as e:
            print(f"Error fetching attendee names: {e}")
            # Fallback: return codes as names
            attendees_with_names = [{"code": code, "name": code} for code in attendee_codes]
    
    return GetClassAttendeesResponse(attendees=attendees_with_names)

# 5. REMOVE ATTENDEE FROM CLASS
@app.delete("/classes/{class_id}/attendees/{attendee_code}")
async def remove_attendee(
    class_id: str,
    attendee_code: str,
    institution_id: str = Depends(get_institution_id),
    db: AsyncSession = Depends(get_db)
):
    # Verify class exists
    result = await db.execute(
        select(Class).where(
            Class.id == class_id,
            Class.institution_id == institution_id
        )
    )
    class_obj = result.scalar_one_or_none()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Find and delete the class-attendee relationship
    result = await db.execute(
        select(ClassAttendee).where(
            ClassAttendee.class_id == class_id,
            ClassAttendee.attendee_code == attendee_code,
            ClassAttendee.institution_id == institution_id
        )
    )
    class_attendee = result.scalar_one_or_none()
    
    if not class_attendee:
        raise HTTPException(status_code=404, detail="Attendee not found in this class")
    
    await db.delete(class_attendee)
    await db.commit()
    
    return {"message": "Attendee removed successfully"}

# 6. VALIDATE ATTENDEE IN CLASS
@app.post("/classes/validate-attendee", response_model=ValidateAttendeeResponse)
async def validate_attendee(
    data: ValidateAttendeeRequest,
    institution_id: str = Depends(get_institution_id),
    db: AsyncSession = Depends(get_db)
):
    # Join ClassAttendee with Class to get the class name
    result = await db.execute(
        select(ClassAttendee, Class)
        .join(Class, ClassAttendee.class_id == Class.id)
        .where(
            ClassAttendee.class_id == data.class_id,
            ClassAttendee.attendee_code == data.attendee_code,
            ClassAttendee.institution_id == institution_id
        )
    )
    row = result.first()
    
    if not row:
        return ValidateAttendeeResponse(valid=False)
    
    class_attendee, class_obj = row
    
    return ValidateAttendeeResponse(
        valid=True,
        class_attendee_id=class_attendee.id,
        class_name=class_obj.name
    )

# 7. VALIDATE CLASS EXISTENCE
@app.post("/classes/validate-existence", response_model=ValidateClassExistenceResponse)
async def validate_class_existence(
    data: ValidateClassExistenceRequest,
    institution_id: str = Depends(get_institution_id),
    db: AsyncSession = Depends(get_db)
):
    ids = [item.id for item in data.classes]
    
    if not ids:
        return ValidateClassExistenceResponse(valid=True, classes=[])
        
    result = await db.execute(
        select(Class).where(
            Class.institution_id == institution_id,
            Class.id.in_(ids)
        )
    )
    found = result.scalars().all()
    
    if len(found) != len(set(ids)):
        return ValidateClassExistenceResponse(valid=False)
        
    return ValidateClassExistenceResponse(
        valid=True,
        classes=[
            {"id": c.id, "name": c.name}
            for c in found
        ]
    )

# 8. DELETE CLASS
@app.delete("/classes/{class_id}")
async def delete_class(
    class_id: str,
    institution_id: str = Depends(get_institution_id),
    db: AsyncSession = Depends(get_db)
):
    # Verify class exists and belongs to institution
    result = await db.execute(
        select(Class).where(
            Class.id == class_id,
            Class.institution_id == institution_id
        )
    )
    class_obj = result.scalar_one_or_none()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Delete all class-attendee relationships first
    await db.execute(
        select(ClassAttendee).where(
            ClassAttendee.class_id == class_id
        )
    )
    from sqlalchemy import delete as sql_delete
    await db.execute(
        sql_delete(ClassAttendee).where(
            ClassAttendee.class_id == class_id
        )
    )
    
    # Delete the class
    await db.delete(class_obj)
    await db.commit()
    
    return {"message": "Class deleted successfully"}
