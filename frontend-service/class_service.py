from fastapi import APIRouter, Request, Form, Cookie
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import httpx
import os

CLASS_SERVICE_URL = os.getenv("CLASS_SERVICE_URL", "http://localhost:8000")

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
    name: str = Form(...),
    grade: str = Form(...)
):
    if not check_auth(jwt_token):
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(
                f"{CLASS_SERVICE_URL}/classes",
                headers={"Authorization": f"Bearer {jwt_token}"},
                json={"classes": [{"name": name, "grade": grade}]}
            )
            
            if res.status_code != 200:
                return RedirectResponse(url="/classes/create?error=1", status_code=302)
            
            return RedirectResponse(
                url=f"/classes?success=1&class_name={name}",
                status_code=302
            )
    except Exception:
        return RedirectResponse(url="/classes/create?error=1", status_code=302)
