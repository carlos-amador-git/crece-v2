from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker
from app.models.api_key import ApiKey, generate_api_key

router = APIRouter()

require_admin = RoleChecker([Role.ADMIN])


# ── Schemas ──────────────────────────────────────────────


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Descriptive name for the key")
    user_id: int = Field(..., description="User ID this key acts as")
    permissions: dict[str, bool] = Field(
        default_factory=dict,
        description="Permission map, e.g. {'campaigns': true, 'content': true}",
    )


class ApiKeyCreateResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    raw_key: str = Field(
        ..., description="The full API key. Only shown ONCE at creation time."
    )
    permissions: dict[str, Any]
    created_at: datetime


class ApiKeyListItem(BaseModel):
    id: int
    name: str
    key_prefix: str
    permissions: dict[str, Any]
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime


class ApiKeyListResponse(BaseModel):
    items: list[ApiKeyListItem]


# ── Endpoints ────────────────────────────────────────────


@router.post(
    "",
    response_model=ApiKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key (admin only)",
)
async def create_api_key(
    body: ApiKeyCreateRequest,
    current_user: Annotated[Any, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiKeyCreateResponse:
    """Create a new API key for external integrations.

    The raw key is returned ONCE in this response and cannot be recovered.
    Store it securely in your n8n credentials or secrets manager.
    """
    raw_key, key_hash = generate_api_key()

    api_key = ApiKey(
        org_id=current_user.org_id,
        user_id=body.user_id,
        key_hash=key_hash,
        key_prefix=raw_key[:12],
        name=body.name,
        permissions=body.permissions,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db.add(api_key)
    await db.flush()

    return ApiKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        raw_key=raw_key,
        permissions=api_key.permissions or {},
        created_at=api_key.created_at,
    )


@router.get(
    "",
    response_model=ApiKeyListResponse,
    summary="List all API keys (admin only)",
)
async def list_api_keys(
    current_user: Annotated[Any, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiKeyListResponse:
    """List all API keys for the current organization.

    Returns prefix and metadata only; never exposes the hash.
    """
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.org_id == current_user.org_id)
        .order_by(ApiKey.created_at.desc())
    )
    keys = result.scalars().all()

    return ApiKeyListResponse(
        items=[
            ApiKeyListItem(
                id=k.id,
                name=k.name,
                key_prefix=k.key_prefix,
                permissions=k.permissions or {},
                is_active=k.is_active,
                last_used_at=k.last_used_at,
                created_at=k.created_at,
            )
            for k in keys
        ]
    )


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke an API key (admin only)",
)
async def revoke_api_key(
    key_id: int,
    current_user: Annotated[Any, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Revoke (deactivate) an API key. This is irreversible."""
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.id == key_id,
            ApiKey.org_id == current_user.org_id,
        )
    )
    api_key = result.scalar_one_or_none()
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    api_key.is_active = False
    await db.flush()
