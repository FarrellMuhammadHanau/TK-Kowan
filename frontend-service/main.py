from fastapi import FastAPI, Request, Cookie
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from auth import router as auth_router
from attendee import router as attendee_router
from room import router as room_router

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(auth_router)
app.include_router(attendee_router)
app.include_router(room_router)

def check_auth(jwt_token: str = None):
    """Check if user is authenticated"""
    return jwt_token is not None

@app.get("/")
def home(jwt_token: str = Cookie(None)):
    if check_auth(jwt_token):
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/login", status_code=302)

@app.get("/dashboard")
def dashboard(request: Request, jwt_token: str = Cookie(None)):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
    )
