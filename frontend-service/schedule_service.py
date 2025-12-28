from fastapi import APIRouter, Request, Form, Cookie
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import httpx
import os
import traceback

SCHEDULE_SERVICE_URL = os.getenv("SCHEDULE_SERVICE_URL", "http://35.171.134.244:8000")

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
                data = res.json()
                schedules = data if isinstance(data, list) else data.get("schedules", [])

    except Exception:
        traceback.print_exc()
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
    class_id: str = Form(...),
    room_id: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    day: int = Form(...)
):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        start_hhmm = int(start_time.replace(":", ""))
        end_hhmm = int(end_time.replace(":", ""))
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {
                "schedules": [{
                    "class_id": class_id,
                    "room_id": room_id,
                    "start_time": start_hhmm,
                    "end_time": end_hhmm,
                    "day": day
                }]
            }
            
            res = await client.post(
                f"{SCHEDULE_SERVICE_URL}/schedules/create",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json=payload
            )
            
            if res.status_code not in [200, 201]:
                return RedirectResponse(url="/schedules/create?error=1", status_code=302)
            
            return RedirectResponse(
                url=f"/schedules?success=1&schedule_name=Schedule",
                status_code=302
            )
    except Exception:
        traceback.print_exc()
        return RedirectResponse(url="/schedules/create?error=1", status_code=302)
