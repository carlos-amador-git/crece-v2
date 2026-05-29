"""Sprint S2 · Editor HITL evaluación NLP — endpoints.

Permite que actores políticos confirmen/modifiquen las clasificaciones NLP del
sistema desde `/dashboard/settings/evaluacion-nlp`. Edit aplica DIRECTO sin
queue de approval. Cada edit escribe a `hitl_edits_log` y dispara recompute del
score del comment/post afectado.

RBAC:
- VIEWER → sólo opera sobre `user.dirigente_id` propio (403 si pide otro).
- ADMIN/ANALYST → cualquier dirigente.

Endpoints:
    GET    /hitl/sample
    PATCH  /hitl/comments/{id}
    POST   /hitl/comments/{id}/confirm
    PATCH  /hitl/posts/{id}
    POST   /hitl/posts/{id}/confirm
    GET    /hitl/audit/{dirigente_id}
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, get_current_user
from app.models.hitl_audit import HitlEditsLog
from app.models.social import Platform
from app.models.user import User
from app.utils.social_urls import compose_post_url
from app.services.score_recompute import (
    recompute_score_comment,
    recompute_score_post,
)

router = APIRouter()

# ──────────────────────────────────────────────────────────────────────────────
# Constantes de validación
# ──────────────────────────────────────────────────────────────────────────────

# Vocab v2 (alineado con matriz política framework_matrix_defaults + frontend dropdowns)
# Definido en docs/POLITICAL-FRAMEWORK-DEFAULTS.md y backend/app/nlp/matriz_v3_mapper.py
VALID_TONO = {
    "critico",
    "propositivo",
    "celebratorio",
    "informativo",
    "solidario",
    "ataque",
    "personal",
}
VALID_TARGET = {
    "gobierno",
    "oposicion",
    "ciudadania",
    "medios",
    "autopromocion",
    "tema_especifico",
    "dirigente",
}
PRIVILEGED_ROLES = {Role.ADMIN, Role.ANALYST}


# ──────────────────────────────────────────────────────────────────────────────
# Helpers RBAC + lookups
# ──────────────────────────────────────────────────────────────────────────────


def _check_dirigente_access(user: User, dirigente_id: int) -> None:
    """403 si VIEWER intenta operar sobre un dirigente ajeno."""
    if user.role in PRIVILEGED_ROLES:
        return
    if user.dirigente_id is None or user.dirigente_id != dirigente_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para este dirigente",
        )


async def _get_comment_dirigente(db: AsyncSession, comment_id: int) -> tuple[int, dict[str, Any]]:
    """Retorna (dirigente_id, {tono, target, off_topic}) del comment.

    Hace JOIN comment → social_posts → social_profiles → dirigente_id.
    Lanza 404 si no existe.
    """
    row = (
        await db.execute(
            text(
                """
                SELECT sp.dirigente_id,
                       sc.nlp_tono,
                       sc.nlp_target
                  FROM social_comments sc
                  JOIN social_posts spo ON spo.id = sc.parent_post_id
                  JOIN social_profiles sp ON sp.id = spo.profile_id
                 WHERE sc.id = :cid
                """
            ),
            {"cid": comment_id},
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Comment no encontrado")
    return row[0], {"tono": row[1], "target": row[2]}


async def _get_post_dirigente(db: AsyncSession, post_id: int) -> tuple[int, dict[str, Any]]:
    """Retorna (dirigente_id, {tono, target}) del post."""
    row = (
        await db.execute(
            text(
                """
                SELECT sp.dirigente_id,
                       spo.target_politico
                  FROM social_posts spo
                  JOIN social_profiles sp ON sp.id = spo.profile_id
                 WHERE spo.id = :pid
                """
            ),
            {"pid": post_id},
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    return row[0], {"tono": None, "target": row[1]}


# ──────────────────────────────────────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────────────────────────────────────


class CommentEditBody(BaseModel):
    tono: str | None = Field(default=None, max_length=20)
    target: str | None = Field(default=None, max_length=30)
    off_topic: bool | None = None
    reason: str | None = Field(default=None, max_length=2000)


class PostEditBody(BaseModel):
    tono: str | None = Field(default=None, max_length=20)
    target: str | None = Field(default=None, max_length=30)
    off_topic: bool | None = None
    reason: str | None = Field(default=None, max_length=2000)


# ──────────────────────────────────────────────────────────────────────────────
# GET /hitl/sample
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/sample")
async def get_sample(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    dirigente_id: int = Query(..., gt=0),
    scope: Literal["cronologico", "estratificado"] = "cronologico",
    days: int = Query(30, ge=1, le=365),
    platform: str = "all",
    include_reviewed: bool = False,
    n_comments: int = Query(50, ge=1, le=500),
    n_posts: int = Query(20, ge=1, le=200),
) -> dict[str, Any]:
    _check_dirigente_access(current_user, dirigente_id)

    platform_filter_posts = ""
    params: dict[str, Any] = {
        "did": dirigente_id,
        "days": str(days),
        "n_posts": n_posts,
        "n_comments": n_comments,
    }
    if platform != "all":
        platform_filter_posts = " AND sp.platform = :plat "
        params["plat"] = platform.upper()

    review_filter_posts = "" if include_reviewed else " AND COALESCE(spo.review_status,'unreviewed') = 'unreviewed' "
    review_filter_comments = "" if include_reviewed else " AND COALESCE(sc.review_status,'unreviewed') = 'unreviewed' "

    if scope == "estratificado":
        order_posts = "ORDER BY md5(spo.id::text || '42')"
        order_comments = "ORDER BY md5(sc.id::text || '42')"
    else:
        order_posts = "ORDER BY spo.published_at DESC"
        order_comments = "ORDER BY sc.published_at DESC NULLS LAST"

    posts_sql = text(
        f"""
        SELECT spo.id, spo.platform_post_id, spo.content, spo.published_at,
               spo.tono_discurso, spo.target_politico,
               COALESCE(spo.review_status,'unreviewed') AS review_status,
               sp.platform, sp.handle
          FROM social_posts spo
          JOIN social_profiles sp ON sp.id = spo.profile_id
         WHERE sp.dirigente_id = :did
           AND spo.published_at >= NOW() - (CAST(:days AS TEXT) || ' days')::INTERVAL
           {platform_filter_posts}
           {review_filter_posts}
         {order_posts}
         LIMIT :n_posts
        """
    )
    posts_rows = (await db.execute(posts_sql, params)).fetchall()

    comments_sql = text(
        f"""
        SELECT sc.id, sc.parent_post_id, sc.content, sc.published_at,
               sc.nlp_tono, sc.nlp_target,
               COALESCE(sc.review_status,'unreviewed') AS review_status,
               sp.platform, sp.handle, spo.platform_post_id, spo.content AS parent_content
          FROM social_comments sc
          JOIN social_posts spo ON spo.id = sc.parent_post_id
          JOIN social_profiles sp ON sp.id = spo.profile_id
         WHERE sp.dirigente_id = :did
           AND COALESCE(sc.published_at, sc.created_at) >= NOW() - (CAST(:days AS TEXT) || ' days')::INTERVAL
           {platform_filter_posts}
           {review_filter_comments}
         {order_comments}
         LIMIT :n_comments
        """
    )
    comments_rows = (await db.execute(comments_sql, params)).fetchall()

    # Progress + system_proposal_summary (sobre la muestra)
    progress_sql = text(
        """
        SELECT
            SUM(CASE WHEN COALESCE(sc.review_status,'unreviewed') <> 'unreviewed' THEN 1 ELSE 0 END) AS reviewed,
            SUM(CASE WHEN COALESCE(sc.review_status,'unreviewed') = 'unreviewed' THEN 1 ELSE 0 END) AS pending
          FROM social_comments sc
          JOIN social_posts spo ON spo.id = sc.parent_post_id
          JOIN social_profiles sp ON sp.id = spo.profile_id
         WHERE sp.dirigente_id = :did
        """
    )
    prog = (await db.execute(progress_sql, {"did": dirigente_id})).first()
    reviewed_total = int(prog[0] or 0) if prog else 0
    pending_total = int(prog[1] or 0) if prog else 0

    tono_dist: dict[str, int] = {}
    target_dist: dict[str, int] = {}
    for r in comments_rows:
        t = r[4] or "none"
        tg = r[5] or "none"
        tono_dist[t] = tono_dist.get(t, 0) + 1
        target_dist[tg] = target_dist.get(tg, 0) + 1

    def _platform_enum(name: str | None) -> Platform | None:
        if not name:
            return None
        try:
            return Platform(name)
        except ValueError:
            return None

    def _snippet(text_val: str | None, n: int = 120) -> str | None:
        if not text_val:
            return None
        clean = text_val.strip().replace("\n", " ")
        return clean if len(clean) <= n else clean[:n].rstrip() + "…"

    return {
        "posts": [
            {
                "id": r[0],
                "platform_post_id": r[1],
                "content": r[2],
                "published_at": r[3].isoformat() if r[3] else None,
                "nlp_tono": r[4],
                "nlp_target": r[5],
                "review_status": r[6],
                "platform": r[7],
                "url": compose_post_url(_platform_enum(r[7]), r[8], r[1]),
            }
            for r in posts_rows
        ],
        "comments": [
            {
                "id": r[0],
                "parent_post_id": r[1],
                "content": r[2],
                "published_at": r[3].isoformat() if r[3] else None,
                "nlp_tono": r[4],
                "nlp_target": r[5],
                "review_status": r[6],
                "platform": r[7],
                "parent_post_url": compose_post_url(_platform_enum(r[7]), r[8], r[9]),
                "parent_post_snippet": _snippet(r[10]),
            }
            for r in comments_rows
        ],
        "progress": {
            "reviewed_total": reviewed_total,
            "pending_total": pending_total,
        },
        "system_proposal_summary": {
            "tono_dist": tono_dist,
            "target_dist": target_dist,
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# Helpers de mutación
# ──────────────────────────────────────────────────────────────────────────────


def _validate_tono(tono: str | None) -> None:
    if tono is not None and tono not in VALID_TONO:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"tono inválido. Valores: {sorted(VALID_TONO)}",
        )


def _validate_target(target: str | None) -> None:
    if target is not None and target not in VALID_TARGET:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"target inválido. Valores: {sorted(VALID_TARGET)}",
        )


async def _write_audit_and_update_review(
    db: AsyncSession,
    *,
    entity_type: str,
    entity_id: int,
    dirigente_id: int,
    from_tono: str | None,
    to_tono: str | None,
    from_target: str | None,
    to_target: str | None,
    off_topic: bool,
    actor_id: int,
    reason: str | None,
    review_status: str,
) -> HitlEditsLog:
    audit = HitlEditsLog(
        entity_type=entity_type,
        entity_id=entity_id,
        dirigente_id=dirigente_id,
        from_tono=from_tono,
        to_tono=to_tono,
        from_target=from_target,
        to_target=to_target,
        off_topic=off_topic,
        actor_id=actor_id,
        reason=reason,
    )
    db.add(audit)

    table = "social_comments" if entity_type == "comment" else "social_posts"
    await db.execute(
        text(
            f"""
            UPDATE {table}
               SET last_reviewed_by = :uid,
                   last_reviewed_at = :now,
                   review_status = :rs
             WHERE id = :eid
            """
        ),
        {
            "uid": actor_id,
            "now": datetime.now(UTC).replace(tzinfo=None),
            "rs": review_status,
            "eid": entity_id,
        },
    )
    await db.flush()
    return audit


# ──────────────────────────────────────────────────────────────────────────────
# PATCH /hitl/comments/{id}
# ──────────────────────────────────────────────────────────────────────────────


@router.patch("/comments/{comment_id}")
async def patch_comment(
    comment_id: int,
    body: CommentEditBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    _validate_tono(body.tono)
    _validate_target(body.target)

    dirigente_id, current = await _get_comment_dirigente(db, comment_id)
    _check_dirigente_access(current_user, dirigente_id)

    new_tono = body.tono if body.tono is not None else current["tono"]
    new_target = body.target if body.target is not None else current["target"]
    off_topic = bool(body.off_topic) if body.off_topic is not None else False

    set_parts = []
    params: dict[str, Any] = {"cid": comment_id}
    if body.tono is not None:
        set_parts.append("nlp_tono = :tono")
        params["tono"] = new_tono
    if body.target is not None:
        set_parts.append("nlp_target = :target")
        params["target"] = new_target
    if set_parts:
        await db.execute(
            text(f"UPDATE social_comments SET {', '.join(set_parts)} WHERE id = :cid"),
            params,
        )

    audit = await _write_audit_and_update_review(
        db,
        entity_type="comment",
        entity_id=comment_id,
        dirigente_id=dirigente_id,
        from_tono=current["tono"],
        to_tono=new_tono,
        from_target=current["target"],
        to_target=new_target,
        off_topic=off_topic,
        actor_id=current_user.id,
        reason=body.reason,
        review_status="edited",
    )

    # S8 audit log centralizado · cruz-referencia con hitl_audit
    if set_parts:
        from app.core.audit_listeners import log_destructive_op
        await log_destructive_op(
            db,
            action="UPDATE",
            model="social_comments",
            record_id=comment_id,
            changes_summary={
                "changed_columns": [c.split(" = ")[0].strip() for c in set_parts],
                "source": "hitl_evaluation.patch_comment",
                "linked_hitl_audit_id": audit.id,
            },
        )

    new_score = await recompute_score_comment(db, comment_id)

    return {
        "ok": True,
        "comment_id": comment_id,
        "audit_id": audit.id,
        "new_score": new_score,
        "review_status": "edited",
    }


# ──────────────────────────────────────────────────────────────────────────────
# POST /hitl/comments/{id}/confirm
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/comments/{comment_id}/confirm")
async def confirm_comment(
    comment_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    dirigente_id, current = await _get_comment_dirigente(db, comment_id)
    _check_dirigente_access(current_user, dirigente_id)

    audit = await _write_audit_and_update_review(
        db,
        entity_type="comment",
        entity_id=comment_id,
        dirigente_id=dirigente_id,
        from_tono=current["tono"],
        to_tono=current["tono"],
        from_target=current["target"],
        to_target=current["target"],
        off_topic=False,
        actor_id=current_user.id,
        reason=None,
        review_status="confirmed",
    )
    return {"ok": True, "comment_id": comment_id, "audit_id": audit.id, "review_status": "confirmed"}


# ──────────────────────────────────────────────────────────────────────────────
# PATCH /hitl/posts/{id}
# ──────────────────────────────────────────────────────────────────────────────


@router.patch("/posts/{post_id}")
async def patch_post(
    post_id: int,
    body: PostEditBody,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    _validate_tono(body.tono)
    _validate_target(body.target)

    dirigente_id, current = await _get_post_dirigente(db, post_id)
    _check_dirigente_access(current_user, dirigente_id)

    new_target = body.target if body.target is not None else current["target"]
    off_topic = bool(body.off_topic) if body.off_topic is not None else False

    target_was_updated = body.target is not None
    if target_was_updated:
        await db.execute(
            text("UPDATE social_posts SET target_politico = :target WHERE id = :pid"),
            {"pid": post_id, "target": new_target},
        )

    audit = await _write_audit_and_update_review(
        db,
        entity_type="post",
        entity_id=post_id,
        dirigente_id=dirigente_id,
        from_tono=None,
        to_tono=body.tono,
        from_target=current["target"],
        to_target=new_target,
        off_topic=off_topic,
        actor_id=current_user.id,
        reason=body.reason,
        review_status="edited",
    )

    # S8 audit log centralizado · cruz-referencia con hitl_audit
    if target_was_updated:
        from app.core.audit_listeners import log_destructive_op
        await log_destructive_op(
            db,
            action="UPDATE",
            model="social_posts",
            record_id=post_id,
            changes_summary={
                "changed_columns": ["target_politico"],
                "source": "hitl_evaluation.patch_post",
                "linked_hitl_audit_id": audit.id,
            },
        )

    new_score = await recompute_score_post(db, post_id)
    return {
        "ok": True,
        "post_id": post_id,
        "audit_id": audit.id,
        "new_score": new_score,
        "review_status": "edited",
    }


# ──────────────────────────────────────────────────────────────────────────────
# POST /hitl/posts/{id}/confirm
# ──────────────────────────────────────────────────────────────────────────────


@router.post("/posts/{post_id}/confirm")
async def confirm_post(
    post_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    dirigente_id, current = await _get_post_dirigente(db, post_id)
    _check_dirigente_access(current_user, dirigente_id)

    audit = await _write_audit_and_update_review(
        db,
        entity_type="post",
        entity_id=post_id,
        dirigente_id=dirigente_id,
        from_tono=None,
        to_tono=None,
        from_target=current["target"],
        to_target=current["target"],
        off_topic=False,
        actor_id=current_user.id,
        reason=None,
        review_status="confirmed",
    )
    return {"ok": True, "post_id": post_id, "audit_id": audit.id, "review_status": "confirmed"}


# ──────────────────────────────────────────────────────────────────────────────
# GET /hitl/audit/{dirigente_id}
# ──────────────────────────────────────────────────────────────────────────────


@router.get("/audit/{dirigente_id}")
async def get_audit(
    dirigente_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    since: datetime | None = None,
    limit: int = Query(200, ge=1, le=2000),
) -> dict[str, Any]:
    _check_dirigente_access(current_user, dirigente_id)

    where = "WHERE dirigente_id = :did"
    params: dict[str, Any] = {"did": dirigente_id, "lim": limit}
    if since is not None:
        where += " AND edited_at >= :since"
        params["since"] = since.replace(tzinfo=None) if since.tzinfo else since

    rows = (
        await db.execute(
            text(
                f"""
                SELECT id, entity_type, entity_id, dirigente_id,
                       from_tono, to_tono, from_target, to_target,
                       off_topic, actor_id, source, reason, edited_at
                  FROM hitl_edits_log
                  {where}
                 ORDER BY edited_at DESC
                 LIMIT :lim
                """
            ),
            params,
        )
    ).fetchall()

    return {
        "dirigente_id": dirigente_id,
        "count": len(rows),
        "rows": [
            {
                "id": r[0],
                "entity_type": r[1],
                "entity_id": r[2],
                "dirigente_id": r[3],
                "from_tono": r[4],
                "to_tono": r[5],
                "from_target": r[6],
                "to_target": r[7],
                "off_topic": r[8],
                "actor_id": r[9],
                "source": r[10],
                "reason": r[11],
                "edited_at": r[12].isoformat() if r[12] else None,
            }
            for r in rows
        ],
    }
