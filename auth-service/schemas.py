from pydantic import BaseModel

class RegisterRequest(BaseModel):
    name: str
    password: str

class LoginRequest(BaseModel):
    name: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"