from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_org_id_from_user(request: Request) -> int | None:
    """Extract org_id from the authenticated user for RLS enforcement.

    Returns the effective org_id:
    - Admin with X-Org-Id header → use that org (tenant switching)
    - Regular user → use their own org_id from the JWT/DB
    - Unauthenticated → None (RLS allows NULL org_id rows only)
    """
    # Lazy import to avoid circular dependency
    from app.core.security import decode_access_token

    # Try JWT first
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            payload = decode_access_token(auth_header[7:])
            role = payload.get("role")
            org_id = payload.get("org_id")

            # Admin can switch org via X-Org-Id header
            if role == "admin":
                override = request.headers.get("x-org-id")
                if override and override.isdigit():
                    return int(override)

            return org_id
        except Exception:
            return None

    return None


async def get_db_rls(
    request: Request,
) -> AsyncGenerator[AsyncSession, None]:
    """DB session with RLS org_id context set.

    Use this dependency in endpoints that query RLS-protected tables.
    Falls back to regular session if no auth context is available.
    """
    org_id = await get_org_id_from_user(request)

    async with async_session_factory() as session:
        try:
            if org_id is not None:
                await session.execute(
                    text("SET LOCAL app.current_org_id = :org_id"),
                    {"org_id": str(org_id)},
                )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
