from fastapi import APIRouter, Request, Form, Cookie, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
import httpx
import os

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://13.223.192.142:8000")

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def check_auth(jwt_token: str = None):
    """Check if user is authenticated"""
    return jwt_token is not None

@router.get("/login")
def login_page(request: Request, jwt_token: str = Cookie(None)):
    if check_auth(jwt_token):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(
        "login.html",
        {"request": request}
    )

@router.post("/login")
async def login_submit(
    response: Response,
    name: str = Form(...),
    password: str = Form(...)
):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{AUTH_SERVICE_URL}/login",
                json={"name": name, "password": password}
            )
            
            if res.status_code != 200:
                return RedirectResponse(url="/login?error=1", status_code=302)
            
            data = res.json()
            token = data.get("access_token")
            
            redirect = RedirectResponse(url="/dashboard", status_code=302)
            redirect.set_cookie(
                key="jwt_token",
                value=token,
                httponly=True,
                max_age=86400,
                samesite="lax"
            )
            return redirect
    except Exception:
        return RedirectResponse(url="/login?error=1", status_code=302)

@router.get("/register")
def register_page(request: Request, jwt_token: str = Cookie(None)):
    if check_auth(jwt_token):
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(
        "register.html",
        {"request": request}
    )

@router.post("/register")
async def register_submit(
    name: str = Form(...),
    password: str = Form(...)
):
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{AUTH_SERVICE_URL}/register",
                json={"name": name, "password": password}
            )
            
            if res.status_code != 200:
                return RedirectResponse(url="/register?error=1", status_code=302)
            
            return RedirectResponse(url="/login?registered=1", status_code=302)
    except Exception:
        return RedirectResponse(url="/register?error=1", status_code=302)

@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("jwt_token")
    return response
