"""Pydantic schemas for API validation (auth + projects)."""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


# --- Auth ---
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Projects ---
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    language: str = "python"  # python | typescript
    framework: str = "fastapi"  # fastapi | express
    environment: str = "mock"  # mock | sandbox


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    language: str | None = None
    framework: str | None = None
    environment: str | None = None


class ProjectOut(BaseModel):
    id: int
    user_id: int
    name: str
    description: str
    language: str
    framework: str
    environment: str
    created_at: datetime

    model_config = {"from_attributes": True}
