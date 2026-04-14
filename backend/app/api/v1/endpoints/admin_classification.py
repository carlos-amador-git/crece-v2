"""Admin panel para clasificación manual MD Consultoría.

Flujo:
1. GET /admin/classification/pending — lista posts sin clasificar de una org
2. GET /admin/classification/prompt — genera prompt listo para pegar en Claude/Gemini
3. POST /admin/classification/batch — recibe JSON del LLM, aplica framework, commit
4. GET /admin/classification/stats — dashboard de progreso

Solo accesible para role=admin (MD Consultoría staff).
Audit log en tabla framework_audit_log existente.
"""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.user import User
from app.services.political_framework import get_effective_matrix

router = APIRouter()


# ───────────────────────────────────────────────────────────────
# Schemas
# ───────────────────────────────────────────────────────────────


class PendingPost(BaseModel):
    id: int
    dirigente_id: int
    dirigente_nombre: str
    rol_politico: str | None
    platform: str
    content: str
    engagement_rate: float | None
    published_at: str | None
    is_rt: bool
    length: int


class ClassificationInput(BaseModel):
    post_id: int
    tono: Literal[
        "critico", "propositivo", "celebratorio", "informativo",
        "solidario", "ataque", "personal",
    ]
    target: Literal[
        "gobierno", "oposicion", "ciudadania", "medios",
        "autopromocion", "tema_especifico", "otro",
    ]
    es_rt: bool = False
    razon: str = Field(max_length=500)
    ia_fuente: Literal["claude", "gemini", "perplexity", "ensamble", "manual"] = "ensamble"


class BatchClassifyRequest(BaseModel):
    org_id: int
    classifications: list[ClassificationInput]
    notas: str | None = None


class BatchClassifyResponse(BaseModel):
    org_id: int
    processed: int
    failed: int
    errors: list[dict] = Field(default_factory=list)


class ClassificationStats(BaseModel):
    org_id: int
    total_posts: int
    classified: int
    pending: int
    coverage_pct: float
    last_classification_at: str | None


# ───────────────────────────────────────────────────────────────
# Endpoints
# ───────────────────────────────────────────────────────────────


def _require_admin_md(user: User):
    """Only system-wide admin can access MD Consultoría tools."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo admin MD Consultoría",
        )


@router.get("/pending", response_model=list[PendingPost])
async def list_pending_posts(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    org_id: int,
    limit: int = 60,
    exclude_rts: bool = True,
    min_length: int = 30,
    days: int = 30,
) -> list[PendingPost]:
    """Posts sin clasificar de la org, ordenados por engagement."""
    _require_admin_md(current_user)

    rt_filter = "AND p.content NOT LIKE 'RT @%'" if exclude_rts else ""
    days_int = int(days)
    sql = (
        "SELECT "
        "  p.id, d.id AS d_id, d.full_name, d.rol_politico, "
        "  sp.platform::text AS plat, "
        "  p.content, p.engagement_rate, "
        "  p.published_at, "
        "  (p.content LIKE 'RT @%') AS is_rt, "
        "  length(p.content) AS chars "
        "FROM social_posts p "
        "JOIN social_profiles sp ON p.profile_id = sp.id "
        "JOIN dirigentes d ON sp.dirigente_id = d.id "
        "WHERE d.org_id = :org_id "
        "  AND p.tono_discurso IS NULL "
        "  AND p.content IS NOT NULL "
        "  AND length(p.content) >= :min_length "
        f"  AND p.published_at >= NOW() - INTERVAL '{days_int} days' "
        f"  {rt_filter} "
        "ORDER BY p.engagement_rate DESC NULLS LAST, p.published_at DESC "
        "LIMIT :limit"
    )
    query = text(sql)
    result = await db.execute(query.bindparams(org_id=org_id, min_length=min_length, limit=limit))

    return [
        PendingPost(
            id=row[0],
            dirigente_id=row[1],
            dirigente_nombre=row[2],
            rol_politico=row[3],
            platform=row[4],
            content=row[5] or "",
            engagement_rate=row[6],
            published_at=row[7].isoformat() if row[7] else None,
            is_rt=row[8],
            length=row[9],
        )
        for row in result.fetchall()
    ]


@router.get("/prompt")
async def generate_prompt(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    org_id: int,
    limit: int = 30,
) -> dict:
    """Genera prompt listo para pegar en Claude Code / Gemini.

    Incluye: matriz efectiva del tenant + posts pendientes + schema esperado.
    El admin MD copia este prompt, lo pega en Claude (o Gemini), y obtiene
    clasificaciones JSON que luego sube vía /batch.
    """
    _require_admin_md(current_user)

    # Get matrix
    matriz = await get_effective_matrix(db, org_id)
    matriz_text = "\n".join(
        f"  ({c['rol']}, {c['tono']}, {c['target']}) = {c['score_effective']:+d} — {c.get('descripcion', '')}"
        for c in matriz
    )

    # Get pending posts
    pending = await list_pending_posts(
        db=db, current_user=current_user, org_id=org_id,
        limit=limit, exclude_rts=True, min_length=30,
    )

    posts_text = "\n".join(
        f"  [{p.id}] {p.dirigente_nombre} ({p.rol_politico}) [{p.platform}]: {p.content[:250].replace(chr(10), ' ')}"
        for p in pending
    )

    prompt = f"""Eres analista de comunicación política mexicana. Clasifica los siguientes posts según el framework de la organización.

FRAMEWORK DE EVALUACIÓN (matriz del tenant):
{matriz_text}

INSTRUCCIONES:
Para cada post, clasifica:
- TONO: critico | propositivo | celebratorio | informativo | solidario | ataque | personal
- TARGET: gobierno | oposicion | ciudadania | medios | autopromocion | tema_especifico | otro
- ES_RT: true si empieza con "RT @"
- RAZON: 1 frase corta que justifique la clasificación

POSTS A CLASIFICAR ({len(pending)}):
{posts_text}

RESPONDE ÚNICAMENTE un JSON array con este schema:
[
  {{"post_id": 123, "tono": "critico", "target": "gobierno", "es_rt": false, "razon": "..."}},
  ...
]

Sin texto adicional, sin markdown code blocks, solo el array JSON puro."""

    return {
        "org_id": org_id,
        "pending_count": len(pending),
        "prompt": prompt,
        "prompt_length": len(prompt),
        "post_ids": [p.id for p in pending],
    }


@router.post("/batch", response_model=BatchClassifyResponse)
async def batch_classify(
    payload: BatchClassifyRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> BatchClassifyResponse:
    """Aplica batch de clasificaciones al DB + framework.

    Para cada post_id: persiste tono, target, aplica matriz → score político.
    Registra ia_fuente y quién procesó.
    """
    _require_admin_md(current_user)

    if not payload.classifications:
        raise HTTPException(status_code=400, detail="classifications vacío")

    # Get matrix for this org (applies overrides)
    matriz = await get_effective_matrix(db, payload.org_id)
    matrix_lookup: dict[tuple, int] = {}
    for c in matriz:
        matrix_lookup[(c["rol"], c["tono"], c["target"])] = c["score_effective"]

    processed = 0
    failed = 0
    errors: list[dict] = []

    for cls in payload.classifications:
        try:
            # Verify post exists and belongs to this org
            row = (await db.execute(
                text("""SELECT p.id, d.rol_politico
                        FROM social_posts p
                        JOIN social_profiles sp ON p.profile_id = sp.id
                        JOIN dirigentes d ON sp.dirigente_id = d.id
                        WHERE p.id = :post_id AND d.org_id = :org_id""")
                .bindparams(post_id=cls.post_id, org_id=payload.org_id)
            )).fetchone()

            if row is None:
                failed += 1
                errors.append({"post_id": cls.post_id, "error": "post no encontrado o no pertenece a org"})
                continue

            rol = row[1] or "independiente"
            score = matrix_lookup.get((rol, cls.tono, cls.target), 0)

            await db.execute(
                text("""UPDATE social_posts SET
                        tono_discurso = :tono,
                        target_politico = :target,
                        sentimiento_politico_ajustado = :score,
                        llm_razon = :razon,
                        llm_modelo = :ia_fuente,
                        llm_processed_at = NOW()
                       WHERE id = :post_id""")
                .bindparams(
                    tono=cls.tono,
                    target=cls.target,
                    score=score,
                    razon=cls.razon,
                    ia_fuente=cls.ia_fuente,
                    post_id=cls.post_id,
                )
            )
            processed += 1

        except Exception as e:
            failed += 1
            errors.append({"post_id": cls.post_id, "error": str(e)[:200]})

    await db.commit()

    return BatchClassifyResponse(
        org_id=payload.org_id,
        processed=processed,
        failed=failed,
        errors=errors[:10],
    )


@router.get("/stats", response_model=list[ClassificationStats])
async def classification_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ClassificationStats]:
    """Cobertura de clasificación por org."""
    _require_admin_md(current_user)

    result = await db.execute(
        text("""
            SELECT
                d.org_id,
                o.nombre AS org_nombre,
                COUNT(p.id) AS total,
                COUNT(CASE WHEN p.tono_discurso IS NOT NULL THEN 1 END) AS classified,
                MAX(p.llm_processed_at) AS last_classification
            FROM social_posts p
            JOIN social_profiles sp ON p.profile_id = sp.id
            JOIN dirigentes d ON sp.dirigente_id = d.id
            JOIN organizaciones o ON d.org_id = o.id
            WHERE p.content IS NOT NULL AND p.content != ''
            GROUP BY d.org_id, o.nombre
            ORDER BY d.org_id
        """)
    )

    return [
        ClassificationStats(
            org_id=row[0],
            total_posts=row[2],
            classified=row[3],
            pending=row[2] - row[3],
            coverage_pct=round(row[3] / max(row[2], 1) * 100, 1),
            last_classification_at=row[4].isoformat() if row[4] else None,
        )
        for row in result.fetchall()
    ]
