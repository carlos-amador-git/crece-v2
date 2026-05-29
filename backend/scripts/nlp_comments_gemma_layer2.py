"""nlp_comments_gemma_layer2.py — Reclasificación Layer 2 con Gemma3:12b via Ollama.

Target: comments con nlp_tono='personal' del keyword-detector que son en realidad
celebratorios (+1). El keyword-detector falla aquí porque 'personal' es su fallback.

Gemma3:12b distingue:
  - "❤️ excelente trabajo" → celebratorio → +1
  - "sígueme en TikTok" → personal (autopromoción) → 0
  - "saludos desde Oaxaca 🙏" → celebratorio/solidario → +1

Uso:
    docker exec crece-backend python scripts/nlp_comments_gemma_layer2.py
    docker exec crece-backend python scripts/nlp_comments_gemma_layer2.py --limit 50 --dry-run
    docker exec crece-backend python scripts/nlp_comments_gemma_layer2.py --concurrency 2
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging

import httpx
from sqlalchemy import text

from app.core.database import async_session_factory

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"
MODEL = "gemma3:12b"

_SYSTEM = (
    "Eres un clasificador político mexicano. Dado un comentario de redes sociales, "
    "responde SOLO con JSON.\n\n"
    "Clasifica el tono en UNA de estas categorías:\n"
    "- celebratorio: apoyo, felicitaciones, emojis positivos (❤🙏👏), admiración al dirigente\n"
    "- critico: crítica negativa a gestión o propuestas del dirigente\n"
    "- ataque: insultos, agresión, violencia verbal\n"
    "- propositivo: sugerencias o propuestas de acción\n"
    "- solidario: apoyo emocional, acompañamiento\n"
    "- informativo: comparte datos, cifras o noticias\n"
    "- personal: spam, autopromoción, off-topic sin relación política\n\n"
    "Formato: {\"tono\": \"<categoria>\", \"razon\": \"<max 8 palabras>\"}"
)

_VALID_TONOS = {
    "celebratorio", "critico", "ataque", "propositivo",
    "solidario", "informativo", "personal",
}


def _parse_ollama(raw: str) -> dict[str, str] | None:
    try:
        cleaned = raw.strip()
        if "```" in cleaned:
            parts = cleaned.split("```")
            cleaned = parts[1].lstrip("json").strip() if len(parts) > 1 else cleaned
        data = json.loads(cleaned)
        tono = str(data.get("tono", "")).strip().lower()
        if tono in _VALID_TONOS:
            return {"tono": tono, "razon": str(data.get("razon", ""))}
    except Exception:
        pass
    return None


async def _call_ollama(client: httpx.AsyncClient, comment: str) -> dict[str, str] | None:
    prompt = f'{_SYSTEM}\n\nComentario: "{comment[:300]}"'
    try:
        r = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.05, "num_predict": 80},
            },
            timeout=90.0,
        )
        r.raise_for_status()
        return _parse_ollama(r.json().get("response", ""))
    except Exception as e:
        logger.debug(f"ollama error: {e}")
        return None


async def main(limit: int = 500, dry_run: bool = False, concurrency: int = 3) -> None:
    # ── 1. Cargar matriz desde BD ──────────────────────────────────────────────
    async with async_session_factory() as session:
        matrix_rows = (await session.execute(text(
            "SELECT contexto, rol, tono, target, score_politico "
            "FROM framework_matrix_defaults WHERE version='v1'"
        ))).fetchall()

        matrix: dict[str, dict[tuple, int]] = {}
        for ctx, rol, tono, target, score in matrix_rows:
            matrix.setdefault(ctx, {})[(rol, tono, target)] = score

        # ── 2. Target: tono='personal' clasificado por keyword-detector ────────
        rows = (await session.execute(text("""
            SELECT sc.id, sc.content, sc.nlp_tono, sc.nlp_target,
                   COALESCE(d.rol_politico, 'independiente') AS rol
            FROM social_comments sc
            JOIN social_posts sp   ON sp.id   = sc.parent_post_id
            JOIN social_profiles p ON p.id    = sp.profile_id
            JOIN dirigentes d      ON d.id    = p.dirigente_id
            WHERE sc.nlp_tono = 'personal'
              AND sc.nlp_model_version = 'comment-framework-v2'
              AND sc.content IS NOT NULL
              AND length(sc.content) > 2
            ORDER BY sc.id
            LIMIT :lim
        """), {"lim": limit})).fetchall()

    n = len(rows)
    print(f"🎯 {n} comments con tono='personal' para reclasificar{' [DRY RUN]' if dry_run else ''}")
    if not n:
        print("✅ Sin pendientes.")
        return

    # ── helper: lookup matriz ──────────────────────────────────────────────────
    def lookup(rol: str, tono: str, target: str) -> int:
        comment_rules = matrix.get("comment_tercero", {})
        post_rules    = matrix.get("post_dirigente", {})
        key = (rol, tono, target)
        return comment_rules.get(key, post_rules.get(key, 0))

    # ── 3. Reclasificar con Gemma3 ─────────────────────────────────────────────
    semaphore = asyncio.Semaphore(concurrency)
    results: list[tuple[int, str, int] | None] = []

    async def process_one(row: tuple) -> tuple[int, str, int] | None:
        cid, content, orig_tono, orig_target, rol = row
        async with semaphore:
            gemma = await _call_ollama(client, content or "")
        if gemma is None:
            return None
        new_tono = gemma["tono"]
        new_pol  = lookup(rol, new_tono, orig_target or "dirigente")
        return (cid, new_tono, new_pol)

    async with httpx.AsyncClient() as client:
        tasks = [process_one(row) for row in rows]
        results = await asyncio.gather(*tasks)

    # ── 4. Aplicar actualizaciones ─────────────────────────────────────────────
    updated = changed = errors = 0
    async with async_session_factory() as session:
        for i, (row, res) in enumerate(zip(rows, results)):
            if res is None:
                errors += 1
                continue
            cid, new_tono, new_pol = res
            orig_tono = row[2]
            if new_tono != orig_tono:
                changed += 1
            updated += 1

            if dry_run:
                orig_pol = lookup(row[4], orig_tono, row[3] or "dirigente")
                print(f"  [{cid:6}] {orig_tono!r:15} → {new_tono!r:15}  pol {orig_pol:+d} → {new_pol:+d}  | {(row[1] or '')[:60]!r}")
            else:
                await session.execute(text("""
                    UPDATE social_comments
                    SET nlp_tono          = :tono,
                        nlp_polaridad     = :pol,
                        nlp_model_version = 'comment-gemma3-layer2-v1'
                    WHERE id = :id
                """), {"tono": new_tono, "pol": new_pol, "id": cid})

            if (i + 1) % 100 == 0:
                pct = 100 * (i + 1) // n
                print(f"  ··· {i+1}/{n} ({pct}%)")

        if not dry_run:
            await session.commit()

    tag = " [DRY RUN]" if dry_run else ""
    print(f"\n{'🔍' if dry_run else '✅'} Batch Gemma3 Layer 2{tag}")
    print(f"  Procesados : {updated}")
    print(f"  Cambiaron  : {changed} ({100*changed//max(updated,1)}%) — de 'personal' a otro tono")
    print(f"  Errores    : {errors}")
    if not dry_run and changed:
        print(f"\n  Ejecuta para recalcular overview:")
        print(f"  curl -s http://localhost:8002/social/aceptacion/overview | python -m json.tool | head -20")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Reclasifica comments 'personal' con Gemma3 Layer 2")
    p.add_argument("--limit",       type=int,  default=500,  help="Máximo de comments a procesar")
    p.add_argument("--dry-run",     action="store_true",      help="Solo imprime, no escribe en BD")
    p.add_argument("--concurrency", type=int,  default=3,    help="Requests paralelos a Ollama")
    args = p.parse_args()
    asyncio.run(main(limit=args.limit, dry_run=args.dry_run, concurrency=args.concurrency))
