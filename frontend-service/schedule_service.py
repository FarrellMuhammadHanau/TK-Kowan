from fastapi import APIRouter, Request, Form, Cookie
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import httpx
import os

SCHEDULE_SERVICE_URL = os.getenv("SCHEDULE_SERVICE_URL", "http://localhost:8000")

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def check_auth(jwt_token: str | None = None):
    """Check if user is authenticated"""
    return jwt_token is not None

@router.get("/schedules")
async def schedules_page(request: Request, jwt_token: str = Cookie(None)):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    schedules = []
    error = None
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{SCHEDULE_SERVICE_URL}/schedules",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            
            if res.status_code == 200:
                schedules = res.json()
    except Exception:
        error = "Gagal mengambil data schedule"
    
    success = request.query_params.get("success")
    schedule_name = request.query_params.get("schedule_name")
    
    return templates.TemplateResponse(
        "schedules.html",
        {
            "request": request,
            "schedules": schedules,
            "error": error,
            "success": success,
            "schedule_name": schedule_name
        }
    )

@router.get("/schedules/create")
def create_schedule_page(request: Request, jwt_token: str = Cookie(None)):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        "schedule_create.html",
        {"request": request}
    )

@router.post("/schedules/create")
async def create_schedule_submit(
    jwt_token: str = Cookie(None),
    class_id: int = Form(...),
    room_id: int = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    day_of_week: str = Form(...)
):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                f"{SCHEDULE_SERVICE_URL}/schedules",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={
                    "schedules": [{
                        "class_id": class_id,
                        "room_id": room_id,
                        "start_time": start_time,
                        "end_time": end_time,
                        "day_of_week": day_of_week
                    }]
                }
            )
            
            if res.status_code != 200:
                return RedirectResponse(url="/schedules/create?error=1", status_code=302)
            
            return RedirectResponse(
                url=f"/schedules?success=1&schedule_name=Schedule",
                status_code=302
            )
    except Exception:
        return RedirectResponse(url="/schedules/create?error=1", status_code=302)
