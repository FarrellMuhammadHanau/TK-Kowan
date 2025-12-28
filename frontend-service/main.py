from fastapi import FastAPI, Request, Cookie
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from jose import jwt
import os

from auth import router as auth_router
from attendee import router as attendee_router
from room import router as room_router
from class_service import router as class_router
from schedule_service import router as schedule_router
from attendance import router as attendance_router  # TAMBAH INI

JWT_SECRET = os.getenv("JWT_SECRET", "EfEmEitch123")
JWT_ALGORITHM = "HS256"

app = FastAPI()
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router)
app.include_router(attendee_router)
app.include_router(room_router)
app.include_router(class_router)
app.include_router(schedule_router)
app.include_router(attendance_router)  # TAMBAH INI

def check_auth(jwt_token: str | None = None):
    """Check if user is authenticated"""
    return jwt_token is not None

def decode_jwt(jwt_token: str | None = None) -> dict | None:
    """Decode JWT token and return payload"""
    if not jwt_token:
        return None
    try:
        return jwt.decode(jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except:
        return None

@app.get("/")
def home(jwt_token: str = Cookie(None)):
    if check_auth(jwt_token):
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/login", status_code=302)

@app.get("/dashboard")
def dashboard(request: Request, jwt_token: str = Cookie(None)):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    payload = decode_jwt(jwt_token)
    institution_name = payload.get("institution_name", "Unknown") if payload else "Unknown"
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "institution_name": institution_name
        }
    )