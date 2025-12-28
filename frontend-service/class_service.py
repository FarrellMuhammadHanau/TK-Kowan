from fastapi import APIRouter, Request, Form, Cookie
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import httpx
import os
import traceback

CLASS_SERVICE_URL = os.getenv("CLASS_SERVICE_URL", "http://3.225.88.17:8000")
ATTENDEE_SERVICE_URL = os.getenv("ATTENDEE_SERVICE_URL", "http://18.214.134.23:8000")

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def check_auth(jwt_token: str | None = None):
    """Check if user is authenticated"""
    return jwt_token is not None

@router.get("/classes")
async def classes_page(request: Request, jwt_token: str = Cookie(None)):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    classes = []
    error = None
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{CLASS_SERVICE_URL}/classes",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            
            if res.status_code == 200:
                classes = res.json()
    except Exception:
        error = "Gagal mengambil data class"
    
    success = request.query_params.get("success")
    class_name = request.query_params.get("class_name")
    
    return templates.TemplateResponse(
        "classes.html",
        {
            "request": request,
            "classes": classes,
            "error": error,
            "success": success,
            "class_name": class_name
        }
    )

@router.get("/classes/create")
def create_class_page(request: Request, jwt_token: str = Cookie(None)):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse(
        "class_create.html",
        {"request": request}
    )

@router.post("/classes/create")
async def create_class_submit(
    jwt_token: str = Cookie(None),
    code: str = Form(...),
    name: str = Form(...)
):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {"classes": [{"code": code, "name": name}]}
            res = await client.post(
                f"{CLASS_SERVICE_URL}/classes/create",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json=payload
            )
            
            if res.status_code not in [200, 201]:
                return RedirectResponse(url="/classes/create?error=1", status_code=302)
            
            return RedirectResponse(
                url=f"/classes?success=1&class_name={name}",
                status_code=302
            )
    except Exception:
        traceback.print_exc()
        return RedirectResponse(url="/classes/create?error=1", status_code=302)

# View attendees for a specific class
@router.get("/classes/{class_id}/attendees")
async def class_attendees_page(
    class_id: str,
    request: Request, 
    jwt_token: str = Cookie(None)
):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    class_info = None
    attendees = []
    error = None
    
    try:
        async with httpx.AsyncClient() as client:
            # Get class info
            res = await client.get(
                f"{CLASS_SERVICE_URL}/classes",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            if res.status_code == 200:
                classes = res.json()
                class_info = next((c for c in classes if c["id"] == class_id), None)
            
            # Get attendees for this class
            if class_info:
                attendees_res = await client.get(
                    f"{CLASS_SERVICE_URL}/classes/{class_id}/attendees",
                    headers={"Authorization": f"Bearer {jwt_token}"}
                )
                print(f"Attendees response status: {attendees_res.status_code}")
                print(f"Attendees response: {attendees_res.json()}")
                if attendees_res.status_code == 200:
                    attendees = attendees_res.json().get("attendees", [])
                    print(f"Attendees data: {attendees}")
    except Exception as e:
        print(f"Error fetching class info: {e}")
        traceback.print_exc()
        error = "Failed to fetch class information"
    
    if not class_info:
        return RedirectResponse(url="/classes", status_code=302)
    
    success = request.query_params.get("success")
    
    return templates.TemplateResponse(
        "class_attendees.html",
        {
            "request": request,
            "class_id": class_id,
            "class_name": class_info.get("name", ""),
            "class_code": class_info.get("code", ""),
            "attendees": attendees,
            "error": error,
            "success": success
        }
    )

# Page to add attendee to class
@router.get("/classes/{class_id}/attendees/add")
async def add_attendee_to_class_page(
    class_id: str,
    request: Request,
    jwt_token: str = Cookie(None)
):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    class_info = None
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{CLASS_SERVICE_URL}/classes",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            if res.status_code == 200:
                classes = res.json()
                class_info = next((c for c in classes if c["id"] == class_id), None)
    except Exception:
        pass
    
    if not class_info:
        return RedirectResponse(url="/classes", status_code=302)
    
    return templates.TemplateResponse(
        "class_attendees_add.html",
        {
            "request": request,
            "class_id": class_id,
            "class_name": class_info.get("name", "")
        }
    )

# Add attendee to class (POST)
@router.post("/classes/{class_id}/attendees/add")
async def add_attendee_to_class_submit(
    class_id: str,
    jwt_token: str = Cookie(None),
    attendee_code: str = Form(...)
):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = {
                "class_id": class_id,
                "attendees": [{"code": attendee_code}]
            }
            res = await client.post(
                f"{CLASS_SERVICE_URL}/classes/add-attendees",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json=payload
            )
            
            if res.status_code not in [200, 201]:
                error_msg = res.json().get("detail", "Failed to add attendee")
                return RedirectResponse(
                    url=f"/classes/{class_id}/attendees/add?error=1&error_msg={error_msg}",
                    status_code=302
                )
            
            return RedirectResponse(
                url=f"/classes/{class_id}/attendees?success=Attendee%20added%20successfully",
                status_code=302
            )
    except Exception as e:
        print(f"Error adding attendee: {e}")
        return RedirectResponse(
            url=f"/classes/{class_id}/attendees/add?error=1",
            status_code=302
        )

# Remove attendee from class (POST)
@router.post("/classes/{class_id}/attendees/remove")
async def remove_attendee_from_class(
    class_id: str,
    jwt_token: str = Cookie(None),
    attendee_code: str = Form(...)
):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.delete(
                f"{CLASS_SERVICE_URL}/classes/{class_id}/attendees/{attendee_code}",
                headers={"Authorization": f"Bearer {jwt_token}"}
            )
            
            if res.status_code not in [200, 204]:
                error_msg = res.json().get("detail", "Failed to remove attendee")
                return RedirectResponse(
                    url=f"/classes/{class_id}/attendees?error=1&error_msg={error_msg}",
                    status_code=302
                )
            
            return RedirectResponse(
                url=f"/classes/{class_id}/attendees?success=Attendee%20removed%20successfully",
                status_code=302
            )
    except Exception as e:
        print(f"Error removing attendee: {e}")
        return RedirectResponse(
            url=f"/classes/{class_id}/attendees?error=1",
            status_code=302
        )
