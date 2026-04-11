"""D-DATA-02 LFPDPPP — FastAPI dependency + helper para audit de acceso a PII.

Usage:

    @router.get("/ciudadanos-legacy/{cid}/pii")
    async def get_pii(
        cid: int,
        db: Annotated[AsyncSession, Depends(get_db)],
        auditor: Annotated[PiiAuditor, Depends(require_pii_clearance)],
    ):
        fields = await read_pii_fields(db, cid, ["email", "phone_01"])
        await auditor.log(
            db=db,
            table_name="ciudadanos_legacy",
            row_id=str(cid),
            action="read_pii",
            fields=list(fields.keys()),
        )
        return fields

El flujo es explícito por diseño:
1. `require_pii_clearance` chequea que `current_user.role == admin`
2. Retorna un `PiiAuditor` con contexto (user, IP, UA)
3. El endpoint DEBE llamar `auditor.log(...)` para registrar qué leyó
4. Sin log → el endpoint está mal implementado (pero el dependency sí
   loggea una entrada `access_attempt` solo por el hecho de pasar)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, get_current_user
from app.models.user import User


@dataclass
class PiiAuditor:
    """Contexto de auditoría inyectado por `require_pii_clearance`."""

    user_id: int | None
    org_id: int | None
    role: str
    request_ip: str | None
    user_agent: str | None

    async def log(
        self,
        db: AsyncSession,
        *,
        table_name: str,
        action: str,
        row_id: str | None = None,
        fields: list[str] | None = None,
        metadata: dict | None = None,
    ) -> None:
        """INSERT a row into data_access_log. Never fails silently on the
        audit side — if the insert raises, the caller sees it.
        """
        import json as _json

        await db.execute(
            text(
                """
                INSERT INTO data_access_log (
                    user_id, org_id, table_name, row_id, action,
                    fields, metadata_json, request_ip, user_agent
                )
                VALUES (
                    :user_id, :org_id, :table_name, :row_id, :action,
                    CAST(:fields AS VARCHAR[]), CAST(:metadata AS JSONB),
                    :request_ip, :user_agent
                )
                """
            ),
            {
                "user_id": self.user_id,
                "org_id": self.org_id,
                "table_name": table_name,
                "row_id": row_id,
                "action": action,
                "fields": fields or [],
                "metadata": _json.dumps(metadata) if metadata else None,
                "request_ip": self.request_ip,
                "user_agent": self.user_agent,
            },
        )
        await db.commit()


async def require_pii_clearance(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PiiAuditor:
    """Dependency que autoriza y loggea el acceso a PII.

    Reglas:
    - Solo `Role.ADMIN` puede pasar.
    - Cada invocación loggea un row `access_attempt` en `data_access_log`.
    - Retorna un `PiiAuditor` con contexto del request.
    """
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso a PII restringido a administradores (D-DATA-02 LFPDPPP).",
        )

    auditor = PiiAuditor(
        user_id=current_user.id,
        org_id=current_user.org_id,
        role=current_user.role.value,
        request_ip=(request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
    )

    # Log the access attempt itself (before the endpoint body runs).
    # If the endpoint then decrypts, it calls auditor.log(action="read_pii").
    await auditor.log(
        db=db,
        table_name="ciudadanos_legacy",
        action="access_attempt",
        metadata={"endpoint": str(request.url.path)},
    )
    return auditor
