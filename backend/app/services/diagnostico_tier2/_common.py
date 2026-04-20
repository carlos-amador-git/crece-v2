"""Shared helpers for Sprint S3 Tier 2 Diferenciadores (MASTER §3.2 #11-#18).

Paralelo a ``app.services.diagnostico._common`` pero con:
- ``bloque_version: "tier2-v1"``
- Helpers específicos para comments (social_comments) que Tier 2 usa pesado
- Diccionarios keyword partidista / violencia política / veda / rage click
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.social import SocialPost, SocialProfile

# ─────────────────────────────────────────────────────────────────────────
# Shape helpers (alineados con tier1 pero con version tier2-v1)
# ─────────────────────────────────────────────────────────────────────────

def build_ok(bloque: str, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "ok",
        "data": data,
        "bloque": bloque,
        "bloque_version": "tier2-v1",
        "computed_at": datetime.now(UTC).isoformat(),
    }


def build_insufficient(
    bloque: str, missing: list[str], extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "insufficient_data",
        "missing": missing,
        "bloque": bloque,
        "bloque_version": "tier2-v1",
        "computed_at": datetime.now(UTC).isoformat(),
    }
    if extra:
        payload["data"] = extra
    return payload


def build_dirigente_not_found(bloque: str, dirigente_id: int) -> dict[str, Any]:
    return build_insufficient(
        bloque, missing=[f"dirigente_id={dirigente_id} no encontrado o fuera de org"]
    )


async def load_dirigente_scoped(
    db: AsyncSession,
    dirigente_id: int,
    org_id: int | None,
) -> Dirigente | None:
    """Load dirigente with optional org_id RLS scoping (tier2 copy)."""
    stmt = select(Dirigente).where(Dirigente.id == dirigente_id)
    if org_id is not None:
        stmt = stmt.where(
            (Dirigente.org_id == org_id) | (Dirigente.org_id.is_(None))
        )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def load_profile_ids(db: AsyncSession, dirigente_id: int) -> list[int]:
    res = await db.execute(
        select(SocialProfile.id).where(SocialProfile.dirigente_id == dirigente_id)
    )
    return [r[0] for r in res.all()]


async def load_posts_ids(
    db: AsyncSession, profile_ids: list[int], since: datetime | None = None
) -> list[int]:
    if not profile_ids:
        return []
    stmt = select(SocialPost.id).where(SocialPost.profile_id.in_(profile_ids))
    if since is not None:
        stmt = stmt.where(SocialPost.published_at >= since)
    res = await db.execute(stmt)
    return [r[0] for r in res.all()]


# ─────────────────────────────────────────────────────────────────────────
# Comments loader (social_comments no está modelada SQLAlchemy — usamos text SQL)
# ─────────────────────────────────────────────────────────────────────────

async def load_comments_for_dirigente(
    db: AsyncSession,
    dirigente_id: int,
    ventana_dias: int | None = 90,
    author_hash_excluir: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Devuelve comments de los posts del dirigente en ventana.

    Cada dict: ``{id, post_id, author_hash, content, published_at,
    nlp_tono, nlp_target, nlp_polaridad, likes}``.
    """
    params: dict[str, Any] = {"dirigente_id": dirigente_id}
    sql = (
        "SELECT sc.id, sc.parent_post_id AS post_id, sc.author_hash, "
        "sc.content, sc.published_at, sc.nlp_tono, sc.nlp_target, "
        "sc.nlp_polaridad, sc.likes "
        "FROM social_comments sc "
        "JOIN social_posts sp ON sp.id = sc.parent_post_id "
        "JOIN social_profiles pr ON pr.id = sp.profile_id "
        "WHERE pr.dirigente_id = :dirigente_id"
    )
    if ventana_dias is not None:
        # ventana_dias viene del código, no del cliente — safe para format
        sql += (
            f" AND COALESCE(sc.published_at, sc.created_at) "
            f">= NOW() - INTERVAL '{int(ventana_dias)} days'"
        )
    if author_hash_excluir:
        sql += " AND sc.author_hash <> ALL(:excluir)"
        params["excluir"] = author_hash_excluir
    result = await db.execute(text(sql), params)
    return [dict(row._mapping) for row in result.all()]


# ─────────────────────────────────────────────────────────────────────────
# Diccionarios compartidos (heurísticas)
# ─────────────────────────────────────────────────────────────────────────

# B11 — afiliación partidista por keywords en content
AFILIACION_KEYWORDS: dict[str, list[str]] = {
    "MC": [
        "movimiento ciudadano", "naranja", "#mc", "@mcmovimiento",
        "dante delgado", "colosio", "alvarez maynez", "álvarez máynez",
        "samuelgarcia", "samuel garcía",
    ],
    "MORENA": [
        "morena", "4t", "cuarta transformación", "amlo",
        "claudia sheinbaum", "claudiash", "lopezobrador", "obradorismo",
    ],
    "PAN": [
        "pan", "#panmx", "acción nacional", "accion nacional",
        "marko cortes", "marko cortés", "xochitl galvez", "xóchitl gálvez",
    ],
    "PRI": [
        "pri", "#pri", "revolucionario institucional",
        "alejandro moreno", "alito", "@priistas",
    ],
    "PVEM": ["pvem", "verde", "partido verde"],
    "PT": ["partido del trabajo", "#pt"],
}

# B18 — violencia política + hate speech MX (seed conservador)
HATE_SPEECH_KEYWORDS = [
    "pendej", "imbecil", "imbécil", "estupid", "idiota", "inutil", "inútil",
    "ratero", "corrupto", "corrupta", "traidor", "traidora", "vendido",
    "puto", "puta", "maricon", "maricón", "pinche",
    "lacayo", "lameculos", "vividor",
]
VIOLENCIA_GENERO_KEYWORDS = [
    "mujerzuela", "zorra", "perra", "vieja loca", "histerica", "histérica",
    "calla putita", "feminazi", "cualquiera",
    "no sirves para esto porque eres mujer", "vete a la cocina",
]
AMENAZAS_KEYWORDS = [
    "te voy a matar", "te vamos a matar", "muerte a", "ahorca",
    "colgar", "linchar", "te van a fusilar", "pagaras", "pagarás",
    "date por muerta", "date por muerto",
]

# B17 — veda INE (palabras que activan alerta si se publican en ventana veda)
VEDA_KEYWORDS_PROHIBIDAS = [
    "voto", "vota por", "candidato", "candidata", "propuesta electoral",
    "elige", "elección", "eleccion", "boleta", "casilla",
    "#voto", "apoya al partido", "por mi partido",
]

# B15 — rage click / outrage keywords
RAGE_KEYWORDS = [
    "corrupto", "ladrón", "ladron", "renuncia", "renuncie", "fuera",
    "rata", "ratas", "vergüenza", "verguenza", "impresentable",
    "cínico", "cinico", "que se vaya", "fraude", "mentiroso",
]
