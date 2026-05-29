"""Clasificación de posts con Gemma3:12b vía Coolify VPS · pre-reunión 2026-05-10.

REGLA DURA: Gemma SIEMPRE vía Coolify (http://163.245.208.96:11434).
NUNCA local Mac — consume RAM y detiene los 6-7 entornos de trabajo del CEO.

Lee últimos N posts por dirigente MC (Piña, Solano, Ballesteros) sin clasificar
y popula social_posts.tono_discurso + target_politico via mapper v3.0.1.

Vocabulario runner Gemma (igual al script original layer2_gemma_bg.py):
  - tono: elogio | critica | pregunta | ataque | informativo | personal | autopromocion
  - target: dirigente_post | gobierno | oposicion | ciudadania | institucion | otros

Tras Gemma, aplicar mapper v3.0.1 → vocab v2 (lo que la matriz política espera):
  - tono v2: critico | propositivo | celebratorio | informativo | solidario | ataque | personal
  - target v2: gobierno | oposicion | ciudadania | medios | autopromocion | tema_especifico | dirigente

Update SQL: social_posts.tono_discurso = tono_v2, social_posts.target_politico = target_v2

Usage:
  docker exec -e DATABASE_URL='postgresql://crece:crece_dev@db:5432/crece' \\
    crece-backend python /app/scripts/classify_posts_gemma_coolify.py \\
    --per-dirigente 20 --dirigentes 1,2,8

Args:
  --per-dirigente N : N posts más recientes sin clasificar por cada dirigente (default 20)
  --dirigentes IDs  : lista CSV de dirigente_id (default 1,2,8 = Piña, Solano, Ballesteros)
  --dry-run         : muestra qué procesaría sin tocar Ollama ni BD
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import datetime

import requests
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, "/app")
from app.nlp.matriz_v3_mapper import map_runner_to_v2  # noqa: E402

OLLAMA_URL = os.environ.get("OLLAMA_BASE_URL", "http://163.245.208.96:11434") + "/api/generate"
MODEL = os.environ.get("OLLAMA_MODEL", "gemma3:12b")

PROMPT_TEMPLATE = """Eres un analista de sentimiento político mexicano. Clasifica este POST de un dirigente.

CONTEXTO:
- Autor del post (dirigente): {dirigente_nombre} ({rol})
- Plataforma: {plataforma}
- Fecha: {published}

POST:
"{post_text}"

Responde SOLO en JSON válido:
{{
  "tono": "elogio|critica|pregunta|ataque|informativo|personal|autopromocion",
  "target": "dirigente_post|gobierno|oposicion|ciudadania|institucion|otros",
  "intensidad": -3 a 3,
  "polaridad_preliminar": "aprobacion|neutral|rechazo",
  "razon_corta": "frase corta"
}}
"""


def classify_post(post_text: str, dirigente_nombre: str, rol: str, plataforma: str, published: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        dirigente_nombre=dirigente_nombre,
        rol=rol,
        plataforma=plataforma,
        published=published,
        post_text=(post_text or "(sin contenido)")[:1500],
    )
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1, "num_predict": 200},
            },
            timeout=240,
        )
        if r.status_code != 200:
            return {"_err": f"HTTP {r.status_code}"}
        resp_text = r.json().get("response", "")
        try:
            return json.loads(resp_text)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", resp_text, re.DOTALL)
            return json.loads(m.group()) if m else {"_err": "parse fail", "_raw": resp_text[:200]}
    except Exception as e:
        return {"_err": f"{type(e).__name__}: {e}"}


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-dirigente", type=int, default=20)
    parser.add_argument("--dirigentes", default="1,2,8")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    dirigente_ids = [int(x) for x in args.dirigentes.split(",")]

    eng = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    S = async_sessionmaker(eng, expire_on_commit=False)

    async with S() as db:
        # Sample posts: por cada dirigente, los N más recientes sin tono_discurso
        rows = (await db.execute(text("""
            WITH ranked AS (
                SELECT
                    sp.id,
                    sp.content,
                    sp.platform_post_id,
                    sp.published_at,
                    sp.post_type::text as plataforma,
                    d.id as dirigente_id,
                    d.full_name as dirigente_nombre,
                    d.rol_politico,
                    ROW_NUMBER() OVER (PARTITION BY d.id ORDER BY sp.published_at DESC) as rn
                FROM social_posts sp
                JOIN social_profiles sprof ON sprof.id = sp.profile_id
                JOIN dirigentes d ON d.id = sprof.dirigente_id
                WHERE d.id = ANY(:diris)
                  AND sp.tono_discurso IS NULL
                  AND sp.content IS NOT NULL
                  AND length(sp.content) > 30
            )
            SELECT id, content, platform_post_id, published_at, plataforma,
                   dirigente_id, dirigente_nombre, rol_politico
              FROM ranked
             WHERE rn <= :n
             ORDER BY dirigente_id, published_at DESC
        """), {"diris": dirigente_ids, "n": args.per_dirigente})).all()

        print(f"Posts a procesar: {len(rows)} (target {args.per_dirigente} × {len(dirigente_ids)} dirigentes)")
        per_diri: dict = {}
        for r in rows:
            per_diri[r.dirigente_nombre] = per_diri.get(r.dirigente_nombre, 0) + 1
        for nombre, n in per_diri.items():
            print(f"  - {nombre}: {n}")

        if args.dry_run:
            print("[DRY-RUN] No se ejecuta clasificación ni UPDATE.")
            return 0

        t0 = time.time()
        ok = 0
        err = 0
        miss_mapper = 0
        for i, r in enumerate(rows, 1):
            cls = classify_post(
                post_text=r.content or "",
                dirigente_nombre=r.dirigente_nombre,
                rol=r.rol_politico or "?",
                plataforma=r.plataforma,
                published=str(r.published_at)[:10],
            )

            if "_err" in cls:
                err += 1
                elapsed = time.time() - t0
                avg = elapsed / i
                print(f"  [{i}/{len(rows)}] ERR · {cls.get('_err')} · avg {avg:.1f}s/post")
                continue

            tono_runner = cls.get("tono", "")
            target_runner = cls.get("target", "")
            # NO is_self_authored: R3 (G2) está pensado para COMMENTS donde
            # author == dirigente, no para POSTS del propio dirigente. Forzar
            # autopromocion runtime aquí descarta la señal real (critico,
            # propositivo, ataque, etc.) que Gemma sí detecta en posts.
            mapped = map_runner_to_v2(
                tono_runner=tono_runner,
                target_runner=target_runner,
                comment_text=r.content or "",
                is_self_authored=False,
            )
            if mapped.fallback:
                miss_mapper += 1

            tono_v2 = mapped.tono_v2
            target_v2 = mapped.target_v2

            await db.execute(text("""
                UPDATE social_posts
                   SET tono_discurso = :tono,
                       target_politico = :target,
                       nlp_model_version = 'gemma3:12b-coolify+mapper_v3.0.1',
                       llm_razon = :razon,
                       clasificacion_origen = 'ai_suggested'
                 WHERE id = :pid
            """), {
                "tono": tono_v2,
                "target": target_v2,
                "razon": (cls.get("razon_corta") or "")[:500],
                "pid": r.id,
            })
            await db.commit()
            ok += 1

            elapsed = time.time() - t0
            avg = elapsed / i
            eta_min = (len(rows) - i) * avg / 60
            if i % 5 == 0 or i == 1 or i == len(rows):
                print(f"  [{i}/{len(rows)}] {r.dirigente_nombre} · "
                      f"runner={tono_runner}/{target_runner} → v2={tono_v2}/{target_v2} · "
                      f"avg {avg:.1f}s · ETA {eta_min:.0f}m")

        elapsed = time.time() - t0
        print()
        print(f"=== Done ===")
        print(f"Procesados: {len(rows)} · OK: {ok} · Errores: {err} · Mapper fallback: {miss_mapper}")
        print(f"Tiempo total: {elapsed/60:.1f} min ({elapsed/len(rows):.1f}s avg)")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
