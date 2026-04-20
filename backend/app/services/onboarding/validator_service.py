"""Sección 4 · Validación de profiles con heurística de confianza.

Implementa la lógica documentada en test_competidor_harfuch.md §Fase 2.
Stack probado: Apify ``apify/instagram-profile-scraper`` + actor X.

Score formula (max 1.0):
    full_name match ≥2 tokens del nombre buscado : +0.4
    full_name match 1 token                      : +0.2
    verified badge                               : +0.3
    followers > 50K                              : +0.2
    followers > 5K                               : +0.1
    posts > 20                                   : +0.1

Umbral auto-aceptación: ≥ 0.7 (D-23)

Sin APIFY_TOKEN el endpoint devuelve estructura válida con
``score_confianza=0`` y ``metadata={"skipped": True}`` para que el wizard
pueda igualmente proceder con confirmación manual (NO se inventan datos).
"""
from __future__ import annotations

import os
from typing import Any

import httpx


APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")
APIFY_BASE = "https://api.apify.com/v2"
ACTOR_IG_PROFILE = "apify~instagram-profile-scraper"
ACTOR_X_PROFILE = "delicious_zebu~advanced-x-twitter-profile-scraper"

THRESHOLD_AUTO_ACCEPT = 0.7


def calcular_score_confianza(
    *,
    nombre_buscado: str,
    full_name: str,
    verified: bool,
    followers: int,
    posts: int,
) -> tuple[float, list[str]]:
    """Heurística documentada en test_competidor_harfuch.md."""
    score = 0.0
    razones: list[str] = []

    buscado_tokens = {
        t.lower() for t in nombre_buscado.split() if len(t) > 2
    }
    fullname_tokens = {t.lower() for t in full_name.split() if len(t) > 2}
    overlap = buscado_tokens & fullname_tokens
    if len(overlap) >= 2:
        score += 0.4
        razones.append(f"full_name match {len(overlap)} tokens: {sorted(overlap)}")
    elif len(overlap) == 1:
        score += 0.2
        razones.append(f"full_name match parcial: {sorted(overlap)}")

    if verified:
        score += 0.3
        razones.append("verified badge")

    if followers and followers > 50_000:
        score += 0.2
        razones.append(f"followers {followers:,} > 50K")
    elif followers and followers > 5_000:
        score += 0.1
        razones.append(f"followers {followers:,} > 5K")

    if posts and posts > 20:
        score += 0.1
        razones.append(f"posts {posts} > 20")

    return min(score, 1.0), razones


async def _call_apify(
    actor: str, payload: dict[str, Any], timeout: float = 120.0
) -> list[dict[str, Any]]:
    url = (
        f"{APIFY_BASE}/acts/{actor}/run-sync-get-dataset-items"
        f"?token={APIFY_TOKEN}"
    )
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, list) else data.get("items", [])


async def validar_cuenta(
    *, platform: str, handle: str, nombre_buscado: str = ""
) -> dict[str, Any]:
    """Valida un perfil concreto y devuelve score + metadata.

    Retorna:
        {
            platform, handle, fullName, verified, followersCount, postsCount,
            score_confianza, razones, metadata, auto_accept: bool
        }
    """
    platform = platform.upper().strip()
    handle = handle.strip().lstrip("@")

    if not APIFY_TOKEN:
        return {
            "platform": platform,
            "handle": handle,
            "fullName": None,
            "verified": False,
            "followersCount": 0,
            "postsCount": 0,
            "score_confianza": 0.0,
            "razones": [],
            "metadata": {"skipped": True, "reason": "APIFY_TOKEN no configurado"},
            "auto_accept": False,
        }

    try:
        if platform == "INSTAGRAM":
            items = await _call_apify(ACTOR_IG_PROFILE, {"usernames": [handle]})
            if not items:
                return {
                    "platform": platform,
                    "handle": handle,
                    "fullName": None,
                    "verified": False,
                    "followersCount": 0,
                    "postsCount": 0,
                    "score_confianza": 0.0,
                    "razones": [],
                    "metadata": {"error": "not_found"},
                    "auto_accept": False,
                }
            profile = items[0]
            full_name = profile.get("fullName", "") or ""
            verified = bool(profile.get("verified", False))
            followers = int(profile.get("followersCount") or 0)
            posts = int(profile.get("postsCount") or 0)
            score, razones = calcular_score_confianza(
                nombre_buscado=nombre_buscado,
                full_name=full_name,
                verified=verified,
                followers=followers,
                posts=posts,
            )
            return {
                "platform": platform,
                "handle": handle,
                "fullName": full_name,
                "verified": verified,
                "followersCount": followers,
                "postsCount": posts,
                "score_confianza": score,
                "razones": razones,
                "metadata": {
                    "biography": profile.get("biography", ""),
                    "url": profile.get("url"),
                    "private": profile.get("private", False),
                },
                "auto_accept": score >= THRESHOLD_AUTO_ACCEPT,
            }

        # TikTok, Facebook Page, YouTube — stubs explícitos en MVP.
        # Devolvemos estructura válida con skipped=True para que el wizard
        # sepa que requiere confirmación humana manual (D-23 regla dura).
        return {
            "platform": platform,
            "handle": handle,
            "fullName": None,
            "verified": False,
            "followersCount": 0,
            "postsCount": 0,
            "score_confianza": 0.0,
            "razones": [],
            "metadata": {
                "skipped": True,
                "reason": f"validator actor para {platform} pendiente MVP",
            },
            "auto_accept": False,
        }
    except httpx.HTTPError as exc:
        return {
            "platform": platform,
            "handle": handle,
            "fullName": None,
            "verified": False,
            "followersCount": 0,
            "postsCount": 0,
            "score_confianza": 0.0,
            "razones": [],
            "metadata": {"error": f"apify_http_error: {exc}"},
            "auto_accept": False,
        }
