from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.core.security import Role


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Role = Role.VIEWER


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: Role | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: Role
    is_active: bool
    dirigente_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    exp: datetime
