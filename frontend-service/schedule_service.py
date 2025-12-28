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
async def create_schedule_page(request: Request, jwt_token: str = Cookie(None)):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    classes = []
    rooms = []
    error = request.query_params.get("error")
    
    try:
        async with httpx.AsyncClient() as client:
            # Fetch classes
            class_res = await client.get(
                f"{os.getenv('CLASS_SERVICE_URL', 'http://3.225.88.17:8000')}/classes",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            if class_res.status_code == 200:
                classes = class_res.json()
            
            # Fetch rooms
            room_res = await client.get(
                f"{os.getenv('ROOM_SERVICE_URL', 'http://54.162.202.203:8000')}/rooms",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            if room_res.status_code == 200:
                rooms = room_res.json()
    except Exception:
        traceback.print_exc()
    
    return templates.TemplateResponse(
        "schedule_create.html",
        {
            "request": request,
            "classes": classes,
            "rooms": rooms,
            "error": error
        }
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
                try:
                    error_detail = res.json().get("detail", "Failed to create schedule")
                except:
                    error_detail = f"Failed to create schedule (Status: {res.status_code})"
                print(f"Schedule creation error: {error_detail}")
                return RedirectResponse(url=f"/schedules/create?error={error_detail}", status_code=302)
            
            return RedirectResponse(
                url=f"/schedules?success=1&schedule_name=Schedule",
                status_code=302
            )
    except Exception as e:
        traceback.print_exc()
        return RedirectResponse(url=f"/schedules/create?error=Error: {str(e)}", status_code=302)

# Delete schedule (POST)
@router.post("/schedules/{schedule_id}/delete")
async def delete_schedule(
    schedule_id: str,
    jwt_token: str = Cookie(None)
):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.delete(
                f"{SCHEDULE_SERVICE_URL}/schedules/{schedule_id}",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            
            if res.status_code not in [200, 204]:
                error_msg = "Failed to delete schedule"
                return RedirectResponse(
                    url=f"/schedules?error={error_msg}",
                    status_code=302
                )
            
            return RedirectResponse(
                url="/schedules?success=Schedule%20deleted%20successfully",
                status_code=302
            )
    except Exception:
        traceback.print_exc()
        return RedirectResponse(
            url="/schedules?error=Failed%20to%20delete%20schedule",
            status_code=302
        )
