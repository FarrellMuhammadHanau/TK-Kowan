from fastapi import APIRouter, Request, Form, Cookie
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import httpx
import os

ATTENDEE_SERVICE_URL = os.getenv("ATTENDEE_SERVICE_URL", "http://18.214.134.23:8000")

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def check_auth(jwt_token: str = None):
    """Check if user is authenticated"""
    return jwt_token is not None

@router.get("/attendees")
async def attendees_page(request: Request, jwt_token: str = Cookie(None)):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    attendees = []
    error = None
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{ATTENDEE_SERVICE_URL}/attendees",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            
            if res.status_code == 200:
                attendees = res.json()
    except Exception as e:
        error = "Gagal mengambil data attendee"
    
    secret_code = request.query_params.get("secret_code")
    secret_value = request.query_params.get("secret_value")
    
    return templates.TemplateResponse(
        "attendees.html",
        {
            "request": request,
            "attendees": attendees,
            "error": error,
            "secret_code": secret_code,
            "secret_value": secret_value
        }
    )

@router.get("/attendees/create")
def create_attendee_page(request: Request, jwt_token: str = Cookie(None)):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        "attendee_create.html",
        {"request": request}
    )

@router.post("/attendees/create")
async def create_attendee_submit(
    jwt_token: str = Cookie(None),
    code: str = Form(...),
    name: str = Form(...)
):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{ATTENDEE_SERVICE_URL}/attendees",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"attendees": [{"code": code, "name": name}]}
            )
            
            if res.status_code != 200:
                return RedirectResponse(url="/attendees/create?error=1", status_code=302)
            
            data = res.json()
            result = data[0]
            secret = result.get("secret")
            
            return RedirectResponse(
                url=f"/attendees?secret_code={code}&secret_value={secret}",
                status_code=302
            )
    except Exception:
        return RedirectResponse(url="/attendees/create?error=1", status_code=302)
