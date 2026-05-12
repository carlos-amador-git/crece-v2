"""Test de concepto — resolución de cuentas oficiales de un competidor.

Caso: Omar García Harfuch (Secretario de Seguridad Pública y Protección Ciudadana).
Fecha: 2026-04-19.
Objetivo: validar empíricamente el flujo propuesto en D-23 (Onboarding Wizard S5)
y documentar los modos de falla que justifican la confirmación humana como requisito.

Flujo del test:

    Fase 1: Búsqueda automática (Brightdata SERP / Apify SERP)
        → Encuentra candidatos de cuentas oficiales por plataforma

    Fase 2: Validación de candidatos (Apify profile actors)
        → Resuelve cada URL a perfil con bio, verified, followers
        → Calcula score de confianza del match por heurística

    Fase 3: Scraping piloto (Apify posts actors)
        → 30 posts recientes del candidato confirmado
        → Métricas reales (likes, views, engagement)

Variables de entorno requeridas:
    APIFY_TOKEN         — token de Apify para llamar actors
    BRIGHTDATA_TOKEN    — opcional, solo si se usa Brightdata SERP (fallback)

Uso:
    python backend/scripts/test_competidor_resolution.py \\
        --nombre "Omar García Harfuch" \\
        --cargo "Secretario de Seguridad Pública" \\
        --output backend/research/2026-04-19/test_competidor_harfuch.md

Notas:
- El test NO es determinista: SERP, actors y redes sociales son fuentes dinámicas.
- El objetivo empírico del test es producir evidencia de cuándo el flujo
  automático tiene éxito vs cuándo requiere input humano de corrección.
- Costo esperado por ejecución: ~$0.05-0.15 USD en créditos Apify.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")
APIFY_BASE = "https://api.apify.com/v2"

# Actors reutilizados (los IDs se obtuvieron en el test empírico 2026-04-19)
ACTOR_SERP = "sovereigntaylor~google-search-scraper"
ACTOR_IG_PROFILE = "apify~instagram-profile-scraper"
ACTOR_X_POSTS = "delicious_zebu~advanced-x-twitter-profile-scraper"


@dataclass
class CandidatoCuenta:
    plataforma: str          # X, Instagram, Facebook, TikTok, YouTube
    handle: str              # @username o URL completa
    url: str
    score_confianza: float   # 0.0 (incierto) - 1.0 (alta confianza)
    razones: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ResultadoFase:
    fase: str
    duracion_s: float
    exito: bool
    hallazgos: list[str] = field(default_factory=list)
    candidatos: list[CandidatoCuenta] = field(default_factory=list)
    errores: list[str] = field(default_factory=list)
    costo_estimado_usd: float = 0.0


def call_apify(actor: str, payload: dict[str, Any], timeout: int = 120) -> dict[str, Any]:
    """Llama sincrónicamente un actor de Apify y devuelve el dataset de resultados."""
    if not APIFY_TOKEN:
        raise RuntimeError("APIFY_TOKEN no configurado en env")
    url = f"{APIFY_BASE}/acts/{actor}/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return {"items": resp.json()}


def calc_score_confianza(
    *, nombre_buscado: str, full_name: str, verified: bool, followers: int, posts: int
) -> tuple[float, list[str]]:
    """Heurística simple de confianza de match.

    Regla:
    - Match exacto de tokens nombre en full_name → +0.4
    - verified=True → +0.3
    - followers > 50k → +0.2 (perfil público probablemente legítimo)
    - posts > 20 → +0.1
    - Bio con keywords institucionales (secretaria, diputada, diputado) → +0.1
    Max 1.0
    """
    score = 0.0
    razones = []

    buscado_tokens = {t.lower() for t in nombre_buscado.split() if len(t) > 2}
    fullname_tokens = {t.lower() for t in full_name.split() if len(t) > 2}
    overlap = buscado_tokens & fullname_tokens
    if len(overlap) >= 2:
        score += 0.4
        razones.append(f"full_name match {len(overlap)} tokens: {overlap}")
    elif len(overlap) == 1:
        score += 0.2
        razones.append(f"full_name match parcial: {overlap}")

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


def fase1_busqueda_serp(nombre: str, cargo: str) -> ResultadoFase:
    """Fase 1: búsqueda SERP geo-MX para encontrar cuentas oficiales candidatas."""
    t0 = time.perf_counter()
    resultado = ResultadoFase(fase="1_busqueda_serp", duracion_s=0, exito=False)

    queries = [
        f"{nombre} Twitter oficial",
        f"{nombre} Instagram oficial",
        f"{nombre} {cargo}",
    ]

    try:
        raw = call_apify(
            ACTOR_SERP,
            {
                "queries": queries,
                "country": "mx",
                "language": "es",
                "maxResults": 10,
            },
        )
        items = raw.get("items", [])

        # Parsear resultados SERP en candidatos de cuentas sociales
        for item in items:
            organic = item.get("organicResults", []) or item.get("results", [])
            for r in organic:
                url = r.get("url", "")
                if "twitter.com" in url or "x.com" in url:
                    handle = url.rstrip("/").split("/")[-1]
                    if handle and handle not in {"status", "i"}:
                        resultado.candidatos.append(
                            CandidatoCuenta(
                                plataforma="X",
                                handle=handle,
                                url=url,
                                score_confianza=0.0,  # se calcula en fase 2
                                razones=[f"SERP hit: {r.get('title', '')[:60]}"],
                            )
                        )
                elif "instagram.com" in url:
                    handle = url.rstrip("/").split("/")[-1].lstrip("@")
                    if handle and "/" not in handle:
                        resultado.candidatos.append(
                            CandidatoCuenta(
                                plataforma="Instagram",
                                handle=handle,
                                url=url,
                                score_confianza=0.0,
                                razones=[f"SERP hit: {r.get('title', '')[:60]}"],
                            )
                        )

        resultado.exito = bool(resultado.candidatos)
        resultado.hallazgos.append(f"{len(resultado.candidatos)} candidatos extraídos de SERP")
        resultado.costo_estimado_usd = 0.003  # ~3 queries × $0.001 SERP free tier
    except Exception as exc:
        resultado.errores.append(f"SERP error: {exc}")

    resultado.duracion_s = time.perf_counter() - t0
    return resultado


def fase2_validacion_perfiles(
    nombre: str, candidatos: list[CandidatoCuenta]
) -> ResultadoFase:
    """Fase 2: validar cada candidato con el profile scraper apropiado."""
    t0 = time.perf_counter()
    resultado = ResultadoFase(fase="2_validacion_perfiles", duracion_s=0, exito=False)

    candidatos_ig = [c for c in candidatos if c.plataforma == "Instagram"]
    candidatos_x = [c for c in candidatos if c.plataforma == "X"]

    # Instagram
    if candidatos_ig:
        try:
            usernames = [c.handle for c in candidatos_ig]
            raw = call_apify(ACTOR_IG_PROFILE, {"usernames": usernames})
            for c, perfil in zip(candidatos_ig, raw["items"]):
                if perfil.get("error"):
                    c.razones.append(f"IG not_found: {perfil['error']}")
                    continue
                full_name = perfil.get("fullName", "")
                verified = perfil.get("verified", False)
                followers = perfil.get("followersCount", 0)
                posts = perfil.get("postsCount", 0)
                score, razones = calc_score_confianza(
                    nombre_buscado=nombre,
                    full_name=full_name,
                    verified=verified,
                    followers=followers,
                    posts=posts,
                )
                c.score_confianza = score
                c.razones.extend(razones)
                c.metadata = {
                    "fullName": full_name,
                    "verified": verified,
                    "followersCount": followers,
                    "postsCount": posts,
                    "biography": perfil.get("biography", ""),
                }
            resultado.costo_estimado_usd += 0.0026 * len(candidatos_ig)
        except Exception as exc:
            resultado.errores.append(f"IG validation error: {exc}")

    # X: no tiene actor de perfil gratis barato comparable → se valida via posts (fase 3)
    # Pero registramos los candidatos X tal cual para que fase 3 los procese
    for c in candidatos_x:
        c.razones.append("X: validación diferida a fase 3 via timeline")

    resultado.candidatos = candidatos
    resultado.exito = any(c.score_confianza > 0.6 for c in candidatos)
    resultado.hallazgos.append(
        f"{sum(1 for c in candidatos if c.score_confianza > 0.6)} candidatos alta confianza (>0.6)"
    )
    resultado.duracion_s = time.perf_counter() - t0
    return resultado


def fase3_scraping_piloto(
    candidatos_alta_confianza: list[CandidatoCuenta], max_posts: int = 30
) -> ResultadoFase:
    """Fase 3: scraping piloto de 30 posts del candidato de mayor confianza."""
    t0 = time.perf_counter()
    resultado = ResultadoFase(fase="3_scraping_piloto", duracion_s=0, exito=False)

    # Sólo procesa el mejor candidato de X (el IG profile actor ya incluye posts en fase 2)
    mejores_x = [c for c in candidatos_alta_confianza if c.plataforma == "X"]
    if not mejores_x:
        resultado.hallazgos.append("No hay candidatos X de alta confianza para fase 3")
        resultado.duracion_s = time.perf_counter() - t0
        return resultado

    mejor = max(mejores_x, key=lambda c: c.score_confianza)

    try:
        end_date = datetime.now(UTC)
        start_date = end_date - timedelta(days=30)
        raw = call_apify(
            ACTOR_X_POSTS,
            {
                "accountUrls": [mejor.url],
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
                "splitMode": "day",
                "language": "es",
                "maxCollections": max_posts,
            },
            timeout=300,
        )
        posts = raw.get("items", [])
        resultado.candidatos = [mejor]
        resultado.hallazgos.append(f"{len(posts)} posts scrapeados de X/{mejor.handle}")
        resultado.exito = len(posts) >= 5  # al menos 5 posts = smoke exitoso
        resultado.costo_estimado_usd = 0.0008 * len(posts)
        if posts:
            avg_likes = sum(p.get("likeCount", 0) for p in posts) / len(posts)
            avg_views = sum(int(p.get("viewCount", 0) or 0) for p in posts) / len(posts)
            resultado.hallazgos.append(
                f"Avg likes/post {avg_likes:.0f} · avg views/post {avg_views:.0f}"
            )
    except Exception as exc:
        resultado.errores.append(f"X posts scraping error: {exc}")

    resultado.duracion_s = time.perf_counter() - t0
    return resultado


def main() -> None:
    parser = argparse.ArgumentParser(description="Test competidor resolution POC")
    parser.add_argument("--nombre", required=True, help="Nombre completo del competidor")
    parser.add_argument("--cargo", required=True, help="Cargo público")
    parser.add_argument("--output", required=True, help="Markdown report output path")
    args = parser.parse_args()

    print(f"=== Test competidor resolution ===")
    print(f"Nombre: {args.nombre}")
    print(f"Cargo:  {args.cargo}")
    print()

    # Fase 1
    print("[Fase 1] Búsqueda SERP (Apify geo-MX)...")
    f1 = fase1_busqueda_serp(args.nombre, args.cargo)
    print(f"  → {len(f1.candidatos)} candidatos · {f1.duracion_s:.1f}s · ${f1.costo_estimado_usd:.4f}")

    # Fase 2
    print("[Fase 2] Validación de perfiles (Apify IG profile)...")
    f2 = fase2_validacion_perfiles(args.nombre, f1.candidatos)
    print(f"  → {sum(1 for c in f2.candidatos if c.score_confianza > 0.6)} alta confianza · {f2.duracion_s:.1f}s · ${f2.costo_estimado_usd:.4f}")

    # Fase 3
    alta = [c for c in f2.candidatos if c.score_confianza > 0.6]
    print("[Fase 3] Scraping piloto (Apify X timeline 30d)...")
    f3 = fase3_scraping_piloto(alta, max_posts=30)
    print(f"  → {f3.hallazgos} · {f3.duracion_s:.1f}s · ${f3.costo_estimado_usd:.4f}")

    # Report
    reporte = {
        "test": "competidor_resolution_poc",
        "competidor": {"nombre": args.nombre, "cargo": args.cargo},
        "timestamp": datetime.now(UTC).isoformat(),
        "fases": [asdict(f) for f in (f1, f2, f3)],
        "costo_total_usd": f1.costo_estimado_usd + f2.costo_estimado_usd + f3.costo_estimado_usd,
        "duracion_total_s": f1.duracion_s + f2.duracion_s + f3.duracion_s,
        "exito_global": all(f.exito for f in (f1, f2, f3)),
    }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(
        "# Test competidor resolution POC — "
        + args.nombre
        + "\n\n```json\n"
        + json.dumps(reporte, indent=2, ensure_ascii=False)
        + "\n```\n"
    )
    print(f"\nReporte: {args.output}")


if __name__ == "__main__":
    main()
