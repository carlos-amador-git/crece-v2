from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    Role,
    RoleChecker,
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserResponse

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Token:
    """Authenticate user and return JWT access token."""
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    token_data = {"sub": str(user.id), "role": user.role.value}
    if user.dirigente_id is not None:
        token_data["dirigente_id"] = str(user.dirigente_id)
    token = create_access_token(data=token_data)
    return Token(access_token=token)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def register(
    payload: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Register a new user. Admin only."""
    # Check for existing email
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


class ForgotPasswordRequest(BaseModel):
    email: str


class ForgotPasswordResponse(BaseModel):
    message: str


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ForgotPasswordResponse:
    """Request password reset email.

    Always returns success to prevent email enumeration.
    In production, this would dispatch an email via Celery.
    """
    # Verify user exists (for future email dispatch) but always return success
    _result = await db.execute(select(User).where(User.email == payload.email))
    # TODO: dispatch password reset email via Celery task
    return ForgotPasswordResponse(
        message="Si existe una cuenta con ese correo, recibirás instrucciones para restablecer tu contraseña."
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Return current authenticated user's profile."""
    return current_user


# ── Impersonate (D-S5-03) ──────────────────────────────────


class ImpersonateResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    impersonating_user_id: int
    impersonator_id: int
    expires_minutes: int = 15


@router.post(
    "/impersonate/{user_id}",
    response_model=ImpersonateResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def impersonate_user(
    user_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ImpersonateResponse:
    """Generate a temporary JWT to view the dashboard as another user.

    Admin-only. The token includes `impersonator_id` claim so audit trails
    track both the real admin and the impersonated user (Gemini G5).
    Token expires in 15 minutes.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot impersonate yourself",
        )

    target = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    expires = timedelta(minutes=15)
    token = create_access_token(
        data={
            "sub": str(target.id),
            "role": target.role,
            "org_id": target.org_id,
            "impersonator_id": current_user.id,
        },
        expires_delta=expires,
    )

    # Audit log — use raw connection to avoid asyncpg cast issues
    import json as _json

    meta_str = _json.dumps({"target_email": target.email, "target_role": target.role})
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "unknown")

    raw = await db.connection()
    await raw.exec_driver_sql(
        "INSERT INTO data_access_log "
        "(user_id, org_id, table_name, row_id, action, fields, metadata_json, request_ip, user_agent, created_at) "
        "VALUES ($1, $2, 'users', $3, 'impersonate', $4::varchar[], $5::jsonb, $6, $7, NOW())",
        (current_user.id, current_user.org_id or 3, str(user_id), ["*"], meta_str, ip, ua),
    )
    await db.commit()

    return ImpersonateResponse(
        access_token=token,
        impersonating_user_id=user_id,
        impersonator_id=current_user.id,
    )
