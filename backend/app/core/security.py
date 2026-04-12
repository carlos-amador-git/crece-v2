from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


class Role(StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    FIELD_OPERATOR = "field_operator"
    VIEWER = "viewer"


# ── Password hashing ─────────────────────────────────────


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT tokens ────────────────────────────────────────────


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from None


# ── Dependencies ──────────────────────────────────────────


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme_optional)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Authenticate via JWT token OR X-API-Key header.

    1. If Authorization: Bearer <token> is present -> JWT flow.
    2. Else if X-API-Key header is present -> API key lookup.
    3. Otherwise -> 401.

    This unified dependency replaces the former split between
    get_current_user (JWT-only) and get_current_user_or_api_key.
    """
    from app.models.api_key import ApiKey  # avoid circular import
    from app.models.user import User  # avoid circular import

    # ── Path 1: JWT bearer token ────────────────────────────
    if token:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        return user

    # ── Path 2: X-API-Key header ────────────────────────────
    api_key_raw = request.headers.get("X-API-Key")
    if api_key_raw:
        key_hash = hashlib.sha256(api_key_raw.encode()).hexdigest()
        result = await db.execute(
            select(ApiKey).where(
                ApiKey.key_hash == key_hash,
                ApiKey.is_active.is_(True),
            )
        )
        api_key_record = result.scalar_one_or_none()
        if api_key_record is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        # Update last_used_at
        api_key_record.last_used_at = datetime.now(UTC)
        # Return the user associated with this key
        user = await db.get(User, api_key_record.user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User associated with API key is inactive",
            )
        return user

    # ── No credentials provided ─────────────────────────────
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


class RoleChecker:
    """Dependency factory: require that the current user has one of the allowed roles.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(RoleChecker([Role.ADMIN]))])
    """

    def __init__(self, allowed_roles: list[Role]) -> None:
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        current_user: Annotated[Any, Depends(get_current_user)],
    ) -> Any:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user


# get_current_user_or_api_key has been merged into get_current_user above.
# Keep this alias for any imports that haven't been updated yet.
get_current_user_or_api_key = get_current_user
