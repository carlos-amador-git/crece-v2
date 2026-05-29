"""Political framework — 3-layer sentiment classification.

Architecture (D-NLP-01):
- Layer 1: NLP technical (pysentimiento + HF models) → raw sentiment
- Layer 2: LLM contextual (Gemma3) → tono_discurso + target_politico
- Layer 3: Framework rules (this module) → sentimiento_politico_ajustado

The matrix is configurable per tenant via framework_overrides_org,
bounded to ±1 from defaults. Default matrix is published in v1 with
suave scale +1/-1/0 (Gemini recommendation).
"""
from __future__ import annotations

from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

Rol = Literal["oficialismo", "oposicion", "independiente"]
Tono = Literal[
    "critico", "propositivo", "celebratorio", "informativo",
    "solidario", "ataque", "personal",
]
Target = Literal[
    "gobierno", "oposicion", "ciudadania", "medios",
    "autopromocion", "tema_especifico", "otro",
]


async def get_political_score(
    db: AsyncSession,
    org_id: int | None,
    rol: Rol,
    tono: Tono,
    target: Target,
    *,
    version: str = "v1",
) -> dict:
    """Resolve the political score for (rol, tono, target) combination.

    Returns dict with both tenant-specific and default scores:
        {
            "score_tenant": int,       # Applied (either override or default)
            "score_default": int,      # Published default
            "is_override": bool,       # True if tenant modified default
            "descripcion": str,
        }

    Fallback: if combination not found, returns score=0 with is_override=False.
    """
    # 1. Get default
    default_row = (await db.execute(
        select_text_default(version, rol, tono, target)
    )).fetchone()
    score_default = default_row[0] if default_row else 0
    descripcion = default_row[1] if default_row else None

    # 2. Check org override
    score_tenant = score_default
    is_override = False
    if org_id is not None:
        override_row = (await db.execute(
            select_text_override(org_id, rol, tono, target)
        )).fetchone()
        if override_row is not None:
            score_tenant = override_row[0]
            is_override = True

    return {
        "score_tenant": score_tenant,
        "score_default": score_default,
        "is_override": is_override,
        "descripcion": descripcion,
    }


def select_text_default(version: str, rol: str, tono: str, target: str):
    from sqlalchemy import text
    return text(
        """SELECT score_politico, descripcion FROM framework_matrix_defaults
           WHERE version = :version AND rol = :rol AND tono = :tono AND target = :target
           LIMIT 1"""
    ).bindparams(version=version, rol=rol, tono=tono, target=target)


def select_text_override(org_id: int, rol: str, tono: str, target: str):
    from sqlalchemy import text
    return text(
        """SELECT score_politico FROM framework_overrides_org
           WHERE org_id = :org_id AND rol = :rol AND tono = :tono AND target = :target
           LIMIT 1"""
    ).bindparams(org_id=org_id, rol=rol, tono=tono, target=target)


async def set_override(
    db: AsyncSession,
    org_id: int,
    rol: Rol,
    tono: Tono,
    target: Target,
    new_score: int,
    user_id: int,
    razon: str | None = None,
) -> dict:
    """Set or update a tenant override for the matrix.

    Guardrails:
    - Score must be in [-2, +2] absolute range
    - Must be within ±1 of the default (soft tenant mode)
    - Records audit log
    """
    if not -2 <= new_score <= 2:
        raise ValueError(f"score must be in [-2, +2], got {new_score}")

    # Get default for bounds check
    from sqlalchemy import text
    default_row = (await db.execute(
        text("""SELECT score_politico FROM framework_matrix_defaults
                WHERE version = 'v1' AND rol = :rol AND tono = :tono AND target = :target""")
        .bindparams(rol=rol, tono=tono, target=target)
    )).fetchone()

    if default_row is None:
        raise ValueError(f"No default for ({rol}, {tono}, {target})")

    score_default = default_row[0]
    if abs(new_score - score_default) > 1:
        raise ValueError(
            f"Override score {new_score} is more than ±1 from default {score_default}. "
            f"Requires admin MD approval for larger changes."
        )

    # Get existing override for audit
    existing = (await db.execute(
        text("""SELECT score_politico FROM framework_overrides_org
                WHERE org_id = :org_id AND rol = :rol AND tono = :tono AND target = :target""")
        .bindparams(org_id=org_id, rol=rol, tono=tono, target=target)
    )).fetchone()
    score_before = existing[0] if existing else None

    # Upsert override
    await db.execute(
        text("""INSERT INTO framework_overrides_org
                (org_id, rol, tono, target, score_politico, modified_by_user_id)
                VALUES (:org_id, :rol, :tono, :target, :score, :user_id)
                ON CONFLICT (org_id, rol, tono, target)
                DO UPDATE SET score_politico = :score, modified_by_user_id = :user_id, modified_at = NOW()""")
        .bindparams(
            org_id=org_id, rol=rol, tono=tono, target=target,
            score=new_score, user_id=user_id,
        )
    )

    # Audit log
    await db.execute(
        text("""INSERT INTO framework_audit_log
                (org_id, rol, tono, target, score_before, score_after, score_default, changed_by_user_id, razon)
                VALUES (:org_id, :rol, :tono, :target, :score_before, :score_after, :score_default, :user_id, :razon)""")
        .bindparams(
            org_id=org_id, rol=rol, tono=tono, target=target,
            score_before=score_before, score_after=new_score, score_default=score_default,
            user_id=user_id, razon=razon,
        )
    )
    await db.commit()

    return {
        "rol": rol,
        "tono": tono,
        "target": target,
        "score_before": score_before,
        "score_after": new_score,
        "score_default": score_default,
    }


async def get_effective_matrix(db: AsyncSession, org_id: int) -> list[dict]:
    """Return full matrix with overrides applied for this org.

    Useful for the settings UI to show current effective configuration.
    """
    from sqlalchemy import text
    result = await db.execute(
        text("""
            SELECT
                d.rol, d.tono, d.target,
                d.score_politico AS score_default,
                COALESCE(o.score_politico, d.score_politico) AS score_effective,
                (o.id IS NOT NULL) AS is_override,
                d.descripcion
            FROM framework_matrix_defaults d
            LEFT JOIN framework_overrides_org o
                ON o.org_id = :org_id
                AND o.rol = d.rol
                AND o.tono = d.tono
                AND o.target = d.target
            WHERE d.version = 'v1'
            ORDER BY d.rol, d.tono, d.target
        """).bindparams(org_id=org_id)
    )
    rows = result.fetchall()
    return [
        {
            "rol": r[0],
            "tono": r[1],
            "target": r[2],
            "score_default": r[3],
            "score_effective": r[4],
            "is_override": r[5],
            "descripcion": r[6],
        }
        for r in rows
    ]
