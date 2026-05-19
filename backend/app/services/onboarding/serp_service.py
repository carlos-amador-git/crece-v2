"""Sección 3 · SERP asistido opcional (D-23 client-driven · NO default).

Wrapper delgado sobre Apify ``sovereigntaylor/google-search-scraper`` con fallback
a Brightdata ``search_engine``. Devuelve top-N candidatos por plataforma con URL
y ``score_serp`` preliminar (0.0-1.0).

IMPORTANTE · D-23: este endpoint NO se activa en el flujo default del wizard.
Solo se dispara si el cliente presiona explícitamente "Buscar automáticamente".
El test empírico con Omar García Harfuch (2026-04-19) confirmó que SERP sin
proxies residenciales devuelve 0 resultados — por eso el flujo primario es
input manual de URLs y SERP queda como asistencia.

Si APIFY_TOKEN no está configurado, el endpoint devuelve un error estructurado
en lugar de inventar resultados (regla MD: NO mocks silenciosos).
"""
from __future__ import annotations

import os
from typing import Any

import httpx

APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")
APIFY_BASE = "https://api.apify.com/v2"
ACTOR_SERP = "sovereigntaylor~google-search-scraper"


class SerpUnavailableError(RuntimeError):
    """Ni Apify ni Brightdata respondieron con resultados válidos."""


def _parse_serp_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filtra resultados SERP y extrae solo dominios de redes sociales conocidas."""
    candidatos: list[dict[str, Any]] = []
    plataforma_hosts = {
        "instagram": "Instagram",
        "x.com": "X",
        "twitter.com": "X",
        "facebook.com": "Facebook",
        "tiktok.com": "TikTok",
        "youtube.com": "YouTube",
    }
    for item in items:
        organic = item.get("organicResults", []) or item.get("results", [])
        for r in organic:
            url = r.get("url", "")
            title = r.get("title", "")[:120]
            for host, platform in plataforma_hosts.items():
                if host in url.lower():
                    candidatos.append(
                        {
                            "platform": platform,
                            "url": url,
                            "title": title,
                            "score_serp": 0.5,  # preliminar · sube en Fase 4 (validator)
                        }
                    )
                    break
    return candidatos


async def buscar_candidatos(
    *,
    nombre: str,
    cargo: str,
    max_results: int = 5,
    timeout: float = 90.0,
) -> dict[str, Any]:
    """Fase 1 del flujo 3-fases: búsqueda SERP geo-MX.

    Devuelve:
        {
            provider: "apify" | "brightdata" | "none",
            candidatos: [{platform, url, title, score_serp}],
            query_count: int,
            errors: list[str]
        }
    """
    errors: list[str] = []
    queries = [
        f"{nombre} {cargo} Instagram oficial",
        f"{nombre} Twitter oficial",
        f"{nombre} Facebook oficial",
    ]

    if not APIFY_TOKEN:
        return {
            "provider": "none",
            "candidatos": [],
            "query_count": 0,
            "errors": ["APIFY_TOKEN no configurado · SERP deshabilitado"],
        }

    url = (
        f"{APIFY_BASE}/acts/{ACTOR_SERP}/run-sync-get-dataset-items"
        f"?token={APIFY_TOKEN}"
    )
    payload = {
        "queries": queries,
        "country": "mx",
        "language": "es",
        "maxResults": max_results,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            items = resp.json()
            candidatos = _parse_serp_items(items)
            return {
                "provider": "apify",
                "candidatos": candidatos[: max_results * len(queries)],
                "query_count": len(queries),
                "errors": errors,
            }
    except httpx.HTTPError as exc:
        errors.append(f"apify SERP error: {exc}")
    except Exception as exc:  # pragma: no cover
        errors.append(f"apify unexpected error: {exc}")

    # TODO: Brightdata fallback — requiere BRIGHTDATA_TOKEN + endpoint
    return {
        "provider": "none",
        "candidatos": [],
        "query_count": len(queries),
        "errors": errors,
    }
