from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    age: Optional[int] = Field(default=None, ge=18, le=100)
    risk_tolerance: Optional[Literal["conservative", "moderate", "aggressive"]] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str

    model_config = {"from_attributes": True}


class UserProfileResponse(BaseModel):
    age: Optional[int] = None
    risk_tolerance: Optional[str] = None
    default_currency: str

    model_config = {"from_attributes": True}


class MeResponse(UserResponse):
    profile: Optional[UserProfileResponse] = None
