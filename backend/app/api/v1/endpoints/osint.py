"""OSINT endpoints — social media username investigation."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.security import Role, RoleChecker, get_current_user
from app.models.user import User
from app.services.sherlock_service import (
    SherlockNotFoundError,
    SherlockTimeoutError,
    investigate_username,
)

router = APIRouter()


# ── Request / Response schemas ──────────────────────────────


class SherlockRequest(BaseModel):
    username: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Target username to investigate across social platforms",
        examples=["alejandropina_mc"],
    )


class FoundProfile(BaseModel):
    platform: str
    url: str


class SherlockResponse(BaseModel):
    username: str
    profiles_found: int
    profiles: list[FoundProfile]


# ── Endpoint ────────────────────────────────────────────────


@router.post(
    "/sherlock",
    response_model=SherlockResponse,
    summary="Investigate username across social platforms",
    description=(
        "Uses Sherlock OSINT tool to discover social media accounts "
        "matching the given username. Restricted to ADMIN and ANALYST roles."
    ),
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def sherlock_investigate(
    payload: SherlockRequest,
    _current_user: Annotated[User, Depends(get_current_user)],
) -> SherlockResponse:
    """Run Sherlock against the provided username and return discovered profiles."""
    try:
        results = await investigate_username(payload.username)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except SherlockNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sherlock tool is not installed on the server",
        )
    except SherlockTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Sherlock investigation timed out. Try again later.",
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sherlock execution failed: {exc}",
        )

    profiles = [
        FoundProfile(platform=platform, url=url) for platform, url in results.items()
    ]

    return SherlockResponse(
        username=payload.username,
        profiles_found=len(profiles),
        profiles=profiles,
    )
