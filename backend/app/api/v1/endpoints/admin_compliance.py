"""Admin Compliance — ARCO LFPDPPP purge endpoint (D-18, Sprint S1 T7).

POST /api/v1/admin/compliance/purge-hash
    Elimina recursivamente comments/posts/vectores asociados a un
    `author_hash` SHA-256 y persiste audit row en `compliance_purge_audit`.

Diferencia con `privacy_arco.py` (endpoint público):
- `privacy_arco.py`  → canal titular. Calcula hash desde commenter_public_id
  y hace cancelacion simple de social_comments (sin audit log dedicado).
- `admin_compliance.py` (este) → canal operativo interno. Consume el hash
  YA calculado por el equipo MD, ejecuta purga integral multi-tabla,
  y persiste trazabilidad LFPDPPP art. 32 en `compliance_purge_audit`.

Cumplimiento:
- Plazo 20 días hábiles (art. 32 LFPDPPP) — el endpoint es paso final
  tras validación legal manual.
- Audit row es inmutable y sobrevive a toda solicitud ARCO posterior
  (§3.1 tabla NO purgable — es su propio log).

Schema purgado (honesto, sin counts simulados):
- `social_comments` WHERE author_hash = :hash  → count real
- `social_posts` → 0 (la tabla no tiene columna author_hash; los posts
  pertenecen al dirigente, no al comentarista). Se registra 0.
- vectores/embeddings → 0 hoy (no existe tabla `comment_embeddings`
  todavía). Se registra 0. Cuando se agregue embeddings-por-comment
  en S2+, basta con ampliar esta función sin cambiar el contrato.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.compliance_purge_audit import CompliancePurgeAudit
from app.models.user import User

router = APIRouter()


# ───────────────────────────────────────────────────────────────
# Schemas
# ───────────────────────────────────────────────────────────────


_HASH64_RE = re.compile(r"^[0-9a-f]{64}$")


class PurgeHashRequest(BaseModel):
    author_hash: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description="SHA-256 hex lowercase — 64 caracteres [0-9a-f]",
    )
    justificacion: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description=(
            "Justificación legal obligatoria: folio ARCO, resolución INAI, "
            "solicitud del titular (al menos 10 caracteres)."
        ),
    )

    @field_validator("author_hash")
    @classmethod
    def _validate_hex_sha256(cls, v: str) -> str:
        v_lc = v.lower()
        if not _HASH64_RE.match(v_lc):
            raise ValueError(
                "author_hash debe ser SHA-256 hexadecimal de 64 chars en [0-9a-f]"
            )
        return v_lc


class PurgedCounts(BaseModel):
    social_comments: int
    social_posts: int
    vectors: int


class PurgeHashResponse(BaseModel):
    purged: PurgedCounts
    audit_id: int
    author_hash: str
    timestamp: str


# ───────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────


def _require_admin(user: User) -> None:
    """ARCO purge es operación privilegiada — solo role=admin MD Consultoría."""
    if getattr(user, "role", None) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operación restringida a role=admin (MD Consultoría compliance)",
        )


# ───────────────────────────────────────────────────────────────
# Endpoint
# ───────────────────────────────────────────────────────────────


@router.post(
    "/purge-hash",
    response_model=PurgeHashResponse,
    status_code=status.HTTP_200_OK,
    summary="ARCO LFPDPPP — purga recursiva por author_hash",
)
async def purge_by_hash(
    payload: PurgeHashRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PurgeHashResponse:
    """Purga recursiva + audit log para solicitud ARCO LFPDPPP (D-18).

    Flujo transaccional:
    1. DELETE FROM social_comments WHERE author_hash = :hash
    2. social_posts / vectors: 0 (no hay author_hash cross-ref hoy)
    3. INSERT INTO compliance_purge_audit (inmutable)
    4. COMMIT

    Idempotente: si no hay filas, retorna 200 con counts=0 + audit row
    también registrado (útil para rastrear solicitudes sin data).
    """
    _require_admin(current_user)

    author_hash = payload.author_hash

    # 1. Purge social_comments (única tabla con author_hash hoy)
    comments_result = await db.execute(
        text(
            "DELETE FROM social_comments "
            "WHERE author_hash = :hash "
            "RETURNING id"
        ),
        {"hash": author_hash},
    )
    rows_comments = len(comments_result.fetchall())

    # 2. social_posts — no tiene author_hash (posts son del dirigente).
    #    Se reporta 0 honestamente. Regla MD: no inventar counts.
    rows_posts = 0

    # 3. vectores/embeddings — no existe tabla `comment_embeddings` aún.
    #    Cuando se agregue (Sprint S2+ con pgvector por comment),
    #    basta ampliar esta sección. Hoy: 0 honesto.
    rows_vectors = 0

    # 4. Audit row inmutable (LFPDPPP art. 32 — trazabilidad)
    audit = CompliancePurgeAudit(
        admin_user_id=current_user.id,
        author_hash=author_hash,
        rows_deleted_social_comments=rows_comments,
        rows_deleted_social_posts=rows_posts,
        rows_deleted_vectors=rows_vectors,
        justificacion=payload.justificacion,
    )
    db.add(audit)
    await db.flush()
    await db.commit()
    await db.refresh(audit)

    return PurgeHashResponse(
        purged=PurgedCounts(
            social_comments=rows_comments,
            social_posts=rows_posts,
            vectors=rows_vectors,
        ),
        audit_id=audit.id,
        author_hash=author_hash,
        timestamp=audit.created_at.astimezone(UTC).isoformat(),
    )


@router.get(
    "/purge-audit",
    summary="Listar audit log de purgas ARCO (admin only)",
)
async def list_purge_audit(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Consulta audit log de purgas. Admin only.

    Retorna las últimas `limit` entradas ordenadas por created_at DESC.
    Útil para dashboards de compliance y auditoría INAI.
    """
    _require_admin(current_user)

    result = await db.execute(
        text(
            "SELECT id, admin_user_id, author_hash, "
            "rows_deleted_social_comments, rows_deleted_social_posts, "
            "rows_deleted_vectors, justificacion, created_at "
            "FROM compliance_purge_audit "
            "ORDER BY created_at DESC "
            "LIMIT :limit"
        ),
        {"limit": limit},
    )
    return [
        {
            "id": row[0],
            "admin_user_id": row[1],
            "author_hash_prefix": (row[2] or "")[:16] + "…",
            "rows_deleted_social_comments": row[3],
            "rows_deleted_social_posts": row[4],
            "rows_deleted_vectors": row[5],
            "justificacion": row[6],
            "created_at": row[7].astimezone(UTC).isoformat() if row[7] else None,
        }
        for row in result.fetchall()
    ]
