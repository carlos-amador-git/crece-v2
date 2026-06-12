from __future__ import annotations

import hashlib
import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# ── Watermark (PLAN-2026-06-11 §3 · prioridad #1 Gemini) ──────────────────

_WATERMARK_POSTS_SQL = text(
    """
    SELECT sp.platform, MAX(p.published_at) AS last_ts
    FROM social_posts p
    JOIN social_profiles sp ON sp.id = p.profile_id
    WHERE sp.dirigente_id = :dirigente_id
    GROUP BY sp.platform
    """
)

# social_comments no tiene modelo SQLAlchemy (FK a nivel DB) → SQL crudo.
# FK verificado contra el INSERT real de los adapters: parent_post_id (NO post_id).
_WATERMARK_COMMENTS_SQL = text(
    """
    SELECT sp.platform, MAX(c.published_at) AS last_ts
    FROM social_comments c
    JOIN social_posts p ON p.id = c.parent_post_id
    JOIN social_profiles sp ON sp.id = p.profile_id
    WHERE sp.dirigente_id = :dirigente_id
    GROUP BY sp.platform
    """
)


async def get_watermark(db: AsyncSession, dirigente_id: int) -> dict:
    """Último timestamp ingerido por plataforma para un dirigente."""
    posts = {
        row.platform: row.last_ts
        for row in (await db.execute(_WATERMARK_POSTS_SQL, {"dirigente_id": dirigente_id})).all()
    }
    comments = {
        row.platform: row.last_ts
        for row in (
            await db.execute(_WATERMARK_COMMENTS_SQL, {"dirigente_id": dirigente_id})
        ).all()
    }
    return {"dirigente_id": dirigente_id, "posts": posts, "comments": comments}


# ── Validación de bundle (Tainted gate · Gemini Q2) ───────────────────────


def _count_records(path: Path) -> int:
    """Cuenta items de un archivo del bundle según su shape (D-041).

    - listas planas → len(lista)
    - envelope {"reactors": [...], "export_meta": ...} → len(reactors)
    - followers.json {"FACEBOOK": N, ...} → número de plataformas
    - dict con "posts"/"comments" → len de esa lista
    """
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("reactors", "posts", "comments"):
            if isinstance(data.get(key), list):
                return len(data[key])
        return len(data)  # followers.json: {PLATFORM: count}
    raise ValueError(f"shape no reconocido en {path.name}")


def validate_bundle(workdir: Path, manifest_files: list[dict]) -> list[str]:
    """Valida sha256 + record_count de cada archivo vs manifest.

    Devuelve lista de discrepancias (vacía = bundle limpio). Cualquier
    discrepancia → bundle Tainted, NO se ingesta (PLAN §5.3).
    """
    problems: list[str] = []
    for mf in manifest_files:
        path = workdir / mf["name"]
        if not path.exists():
            problems.append(f"{mf['name']}: falta en bundle")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != mf["sha256"]:
            problems.append(f"{mf['name']}: sha256 no cuadra")
            continue
        try:
            actual = _count_records(path)
        except (ValueError, json.JSONDecodeError) as exc:
            problems.append(f"{mf['name']}: ilegible ({exc})")
            continue
        if actual != mf["record_count"]:
            problems.append(
                f"{mf['name']}: record_count manifest={mf['record_count']} real={actual}"
            )
    return problems


# ── Gate de cobertura por fecha (SOP-INGEST-RADAR-HANDOFF §2.5) ────────────

_COVERAGE_GATE_SQL = text(
    """
    WITH posts AS (
      SELECT sp.platform plat, p.id pid, p.published_at::date dia
      FROM social_posts p JOIN social_profiles sp ON sp.id = p.profile_id
      WHERE sp.dirigente_id = :dirigente_id
        AND sp.platform IN ('FACEBOOK','INSTAGRAM')
        AND p.published_at::date >= (NOW()::date - interval '45 days')
    )
    SELECT plat, count(*) dias_sin_react, sum(posts) posts_sin_react,
           string_agg(to_char(dia,'MM-DD'),',' ORDER BY dia) dias
    FROM (
      SELECT po.plat, po.dia, count(DISTINCT po.pid) posts,
             count(DISTINCT po.pid) FILTER (WHERE wle.id IS NOT NULL) con_react
      FROM posts po LEFT JOIN watched_like_events wle ON wle.post_id = po.pid
      GROUP BY 1, 2
    ) c WHERE con_react = 0 GROUP BY plat ORDER BY plat
    """
)


def coverage_gaps_sync(session, dirigente_id: int) -> list[dict]:
    """Versión sync (Celery worker). Días con posts FB/IG sin reactors."""
    rows = session.execute(_COVERAGE_GATE_SQL, {"dirigente_id": dirigente_id}).all()
    return [
        {
            "platform": r.plat,
            "dias_sin_react": int(r.dias_sin_react),
            "posts_sin_react": int(r.posts_sin_react),
            "dias": r.dias,
        }
        for r in rows
    ]
