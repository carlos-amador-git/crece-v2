"""Multi-tenant scope helpers.

Patrón canónico D-SEC-WATCHED-SCOPE-1 (DECISIONS.md 2026-05-14) extraído de
`watched_profiles.py` para reuso en todos los endpoints que aceptan
`dirigente_id` (path o query).

Reglas:
- admin → bypass (devuelve org_id sin chequeo).
- resto → user.org_id debe coincidir con dirigente.org_id, else 403.
- dirigente inexistente → 404.

Usage:
    from app.core.scope import assert_dirigente_access
    await assert_dirigente_access(db, current_user, dirigente_id)
"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


def check_org(user: User, dirigente_org_id: int | None) -> None:
    """Verifica que user pertenezca a la org dueña del dirigente.

    Admin bypass. None or mismatch → 403.
    """
    if user.role == "admin":
        return
    if dirigente_org_id is None or user.org_id != dirigente_org_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Sin acceso a esta organización"
        )


async def assert_dirigente_access(
    db: AsyncSession, user: User, dirigente_id: int
) -> int:
    """Resuelve dirigente.org_id y aplica check_org.

    Returns:
        org_id del dirigente (útil para queries downstream).

    Raises:
        HTTPException 404 si el dirigente no existe.
        HTTPException 403 si el user no pertenece al org.
    """
    row = (
        await db.execute(
            text("SELECT org_id FROM dirigentes WHERE id = :did"),
            {"did": dirigente_id},
        )
    ).first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dirigente no existe")
    check_org(user, row[0])
    return row[0]
