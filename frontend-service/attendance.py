from fastapi import APIRouter, Request, Form, Cookie, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import httpx
import os
from jose import jwt

ATTENDANCE_SERVICE_URL = os.getenv("ATTENDANCE_SERVICE_URL", "http://100.28.146.147:8000")
JWT_SECRET = os.getenv("JWT_SECRET", "EfEmEitch123")
JWT_ALGORITHM = "HS256"

router = APIRouter()
templates = Jinja2Templates(directory="templates")

# Attendance Machine Page
@router.get("/attendance-machine")
async def attendance_machine_page(
    request: Request,
    attendance_token: str = Cookie(None)
):
    if not attendance_token:
        return RedirectResponse(url="/login", status_code=302)
    
    # Decode token to get institution_name and room_name
    institution_name = "Unknown"
    room_name = "Unknown"
    
    try:
        payload = jwt.decode(attendance_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        institution_name = payload.get("institution_name", "Unknown")
        room_name = payload.get("room_name", "Unknown")
    except:
        pass
    
    success = request.query_params.get("success")
    error = request.query_params.get("error")
    error_msg = request.query_params.get("error_msg")
    student_name = request.query_params.get("student_name")
    class_name = request.query_params.get("class_name")
    
    return templates.TemplateResponse(
        "attendance_machine.html",
        {
            "request": request,
            "institution_name": institution_name,
            "room_name": room_name,
            "success": success,
            "error": error,
            "error_msg": error_msg,
            "student_name": student_name,
            "class_name": class_name
        }
    )

# Submit Attendance
@router.post("/attendance-machine/submit")
async def submit_attendance(
    attendance_token: str = Cookie(None),
    attendee_code: str = Form(...),
    attendee_secret: str = Form(...)
):
    if not attendance_token:
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                f"{ATTENDANCE_SERVICE_URL}/attendance/presence",
                headers={"Authorization": f"Bearer {attendance_token}"},
                json={
                    "attendee_code": attendee_code,
                    "attendee_secret": attendee_secret
                }
            )
            
            if res.status_code == 200:
                data = res.json()
                return RedirectResponse(
                    url=f"/attendance-machine?success=1&student_name={data.get('student_name', '')}&class_name={data.get('class_name', '')}",
                    status_code=302
                )
            else:
                error_detail = res.json().get("detail", "Attendance failed")
                return RedirectResponse(
                    url=f"/attendance-machine?error=1&error_msg={error_detail}",
                    status_code=302
                )
    except Exception as e:
        print(f"Attendance submission error: {e}")
        return RedirectResponse(
            url="/attendance-machine?error=1&error_msg=Service unavailable",
            status_code=302
        )

# Back to Admin - Login again
@router.get("/attendance-machine/exit")
async def exit_attendance_machine(response: Response):
    redirect = RedirectResponse(url="/login", status_code=302)
    redirect.delete_cookie("attendance_token")
    return redirect