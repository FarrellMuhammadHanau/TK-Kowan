from fastapi import APIRouter, Request, Form, Cookie, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import httpx
import os

ROOM_SERVICE_URL = os.getenv("ROOM_SERVICE_URL", "http://54.162.202.203:8000")
ATTENDANCE_SERVICE_URL = os.getenv("ATTENDANCE_SERVICE_URL", "http://100.28.146.147:8000")

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def check_auth(jwt_token: str | None = None):
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
    except Exception:
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
    except Exception:
        return RedirectResponse(url="/rooms/create?error=1", status_code=302)

# Simulasi Absensi - Get Credential FIRST, THEN logout and redirect
@router.get("/rooms/{room_id}/simulate-attendance")
async def simulate_attendance(
    room_id: str,
    jwt_token: str = Cookie(None)
):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        # 1. Minta credential pakai JWT admin yang masih ada
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                f"{ATTENDANCE_SERVICE_URL}/attendance/attendance-credential",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"room_id": room_id}
            )
            
            print(f"Credential response status: {res.status_code}")
            print(f"Credential response body: {res.text}")
            
            if res.status_code != 200:
                return RedirectResponse(url="/rooms?error=1", status_code=302)
            
            data = res.json()
            credential_token = data.get("access_token")
            
            if not credential_token:
                print("No access_token in response")
                return RedirectResponse(url="/rooms?error=1", status_code=302)
            
            # 2. Setelah dapat credential, logout admin dan set attendance token
            redirect = RedirectResponse(url="/attendance-machine", status_code=302)
            redirect.delete_cookie("jwt_token")  # Logout admin
            redirect.set_cookie(
                key="attendance_token",
                value=credential_token,
                httponly=True,
                max_age=86400,
                samesite="lax"
            )
            return redirect
            
    except Exception as e:
        print(f"Error getting credential: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/rooms?error=1", status_code=302)