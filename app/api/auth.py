from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db.auth import authenticate_user

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    id: int
    username: str
    display_name: str
    role: str


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest) -> LoginResponse:
    user = authenticate_user(request.username, request.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return LoginResponse(**user)
