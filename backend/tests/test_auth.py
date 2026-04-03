"""Tests for authentication endpoints: login, register, and /me."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Role, hash_password
from app.models.user import User
from tests.conftest import auth_headers


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


async def test_login_success(client: AsyncClient, admin_user: User) -> None:
    """A valid email/password pair returns a JWT access_token."""
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@crece.mx", "password": "admin123"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_login_wrong_password(client: AsyncClient, admin_user: User) -> None:
    """Wrong password returns 401."""
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@crece.mx", "password": "wrong-password"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


async def test_login_nonexistent_user(client: AsyncClient) -> None:
    """An email that does not exist returns 401."""
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@crece.mx", "password": "whatever"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password"


async def test_login_inactive_user(client: AsyncClient, db_session: AsyncSession) -> None:
    """A deactivated user gets 403 even with correct credentials."""
    user = User(
        email="inactive@crece.mx",
        hashed_password=hash_password("pass123"),
        full_name="Inactive User",
        role=Role.VIEWER,
        is_active=False,
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "inactive@crece.mx", "password": "pass123"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Account is deactivated"


# ---------------------------------------------------------------------------
# Register (admin-only)
# ---------------------------------------------------------------------------


async def test_register_as_admin(client: AsyncClient, admin_token: str) -> None:
    """An admin can register a new user."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@crece.mx",
            "password": "Strong1234",
            "full_name": "New User",
            "role": "analyst",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "newuser@crece.mx"
    assert body["role"] == "analyst"
    assert body["is_active"] is True


async def test_register_as_non_admin_forbidden(
    client: AsyncClient, viewer_token: str
) -> None:
    """A viewer cannot register users -- expects 403."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "blocked@crece.mx",
            "password": "Strong1234",
            "full_name": "Blocked",
            "role": "viewer",
        },
        headers=auth_headers(viewer_token),
    )
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Insufficient permissions"


async def test_register_duplicate_email(client: AsyncClient, admin_token: str, admin_user: User) -> None:
    """Registering an already-used email returns 409."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@crece.mx",
            "password": "whatever",
            "full_name": "Duplicate",
            "role": "viewer",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409
    assert "already registered" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# /me
# ---------------------------------------------------------------------------


async def test_get_me(client: AsyncClient, admin_token: str, admin_user: User) -> None:
    """Authenticated user gets their own profile."""
    resp = await client.get("/api/v1/auth/me", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "admin@crece.mx"
    assert body["role"] == "admin"


async def test_get_me_no_token(client: AsyncClient) -> None:
    """Request without Authorization header returns 401."""
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
