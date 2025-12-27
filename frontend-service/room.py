from fastapi import APIRouter, Request, Form, Cookie
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import httpx
import os

ROOM_SERVICE_URL = os.getenv("ROOM_SERVICE_URL", "http://54.162.202.203:8000")

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def check_auth(jwt_token: str = None):
    """Check if user is authenticated"""
    return jwt_token is not None

@router.get("/rooms")
async def rooms_page(request: Request, jwt_token: str = Cookie(None)):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    rooms = []
    error = None
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{ROOM_SERVICE_URL}/rooms",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            
            if res.status_code == 200:
                rooms = res.json()
    except Exception as e:
        error = "Gagal mengambil data room"
    
    success = request.query_params.get("success")
    room_name = request.query_params.get("room_name")
    
    return templates.TemplateResponse(
        "rooms.html",
        {
            "request": request,
            "rooms": rooms,
            "error": error,
            "success": success,
            "room_name": room_name
        }
    )

@router.get("/rooms/create")
def create_room_page(request: Request, jwt_token: str = Cookie(None)):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        "room_create.html",
        {"request": request}
    )

@router.post("/rooms/create")
async def create_room_submit(
    jwt_token: str = Cookie(None),
    name: str = Form(...)
):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                f"{ROOM_SERVICE_URL}/rooms",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"rooms": [{"name": name}]}
            )
            
            if res.status_code != 200:
                return RedirectResponse(url="/rooms/create?error=1", status_code=302)
            
            return RedirectResponse(
                url=f"/rooms?success=1&room_name={name}",
                status_code=302
            )
    except Exception as e:
        return RedirectResponse(url="/rooms/create?error=1", status_code=302)
