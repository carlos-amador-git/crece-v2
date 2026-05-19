"""D-23-G' · Day 2 · Clasificador Gemini API target_politico (4-cat).

Plan: .context/PLAN-D-23-G-actividad-alineada-2026-04-24.md (Day 2).

Responsabilidad: clasifica posts en social_posts con la columna target_politico
usando Gemini CLI. Idempotente con WHERE filter sobre nlp_model_version.

Modos:
    --dry-run         no escribe a DB, solo imprime predicciones
    --limit N         solo N posts (default todos los pendientes)
    --dirigente-id N  solo posts de un dirigente específico
    --golden-set      modo "generar golden set" · imprime JSON para CEO

Uso:
    docker exec crece-backend python scripts/classify_target_politico.py --limit 5 --dry-run
    docker exec crece-backend python scripts/classify_target_politico.py --dirigente-id 1
    docker exec crece-backend python scripts/classify_target_politico.py --golden-set > /tmp/gs.json

Idempotencia:
    Filtro `WHERE target_politico IS NULL OR nlp_model_version != MODEL_VERSION`.
    Posts ya clasificados con la versión actual del prompt se saltan.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Permite ejecutar desde scripts/ sin instalar el package
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, text

from app.nlp.target_politico_prompt import (
    VALID_TARGETS,
    build_prompt,
    parse_response,
)

MODEL_VERSION = "crece-political-v1"

# Default URL para ejecutar desde host (gemini CLI vive en /opt/homebrew/bin/).
# Override con env SYNC_DATABASE_URL si se ejecuta dentro del container.
DEFAULT_DB_URL = os.getenv(
    "SYNC_DATABASE_URL",
    "postgresql://crece:crece_dev@localhost:5438/crece",
).replace("+asyncpg", "")

# Comando Gemini CLI · usa wrapper instalado en host.
# Allowlist explícita de basenames aceptables para defeat env-injection.
_ALLOWED_BIN_BASENAMES = {"gemini", "gemini-clean"}


def _resolve_gemini_bin() -> str:
    raw = os.getenv("GEMINI_BIN", "gemini")
    base = os.path.basename(raw)
    if base not in _ALLOWED_BIN_BASENAMES:
        raise RuntimeError(
            f"GEMINI_BIN basename {base!r} no está en allowlist {_ALLOWED_BIN_BASENAMES}"
        )
    return raw


GEMINI_BIN = _resolve_gemini_bin()


def call_gemini(prompt: str, timeout: int = 90) -> str:
    """Invoca Gemini CLI con prompt y retorna stdout."""
    r = subprocess.run(  # nosec B603  # allowlisted basename, no shell=True
        [GEMINI_BIN, "-p", prompt],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if r.returncode != 0:
        # Log a stderr pero no falla · posts con error quedan sin clasificar (NULL)
        sys.stderr.write(f"gemini error rc={r.returncode}: {r.stderr[:200]}\n")
    return r.stdout or ""


def classify_post(post: dict[str, Any], retries: int = 1) -> dict[str, Any] | None:
    """Llama Gemini con backoff. Retorna dict con target+razon o None."""
    prompt = build_prompt(
        texto=post.get("content") or "",
        plataforma=post.get("platform") or "desconocida",
        dirigente_nombre=post.get("dirigente_nombre") or "",
        partido=post.get("partido") or "INDEPENDIENTE",
        cargo=post.get("cargo") or "",
    )

    last_raw = ""
    for attempt in range(retries + 1):
        try:
            raw = call_gemini(prompt)
            last_raw = raw
            parsed = parse_response(raw)
            if parsed:
                return parsed
        except subprocess.TimeoutExpired:
            sys.stderr.write(f"  timeout post={post['id']} attempt={attempt}\n")
        except Exception as e:
            sys.stderr.write(f"  err {type(e).__name__} post={post['id']}: {e}\n")
        if attempt < retries:
            time.sleep(2 ** attempt)
    sys.stderr.write(f"  failed post={post['id']} raw_last={last_raw[:120]}\n")
    return None


def fetch_pending_posts(
    engine,
    *,
    dirigente_id: int | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Lee posts pendientes de clasificar con datos del dirigente."""
    sql = """
    SELECT
        sp.id,
        sp.content,
        sp.platform_post_id,
        prof.platform::text AS platform,
        prof.dirigente_id,
        d.full_name AS dirigente_nombre,
        d.partido,
        d.cargo,
        sp.target_politico,
        sp.nlp_model_version
    FROM social_posts sp
    JOIN social_profiles prof ON prof.id = sp.profile_id
    JOIN dirigentes d ON d.id = prof.dirigente_id
    WHERE (sp.target_politico IS NULL OR sp.nlp_model_version IS NULL OR sp.nlp_model_version != :model_v)
      AND sp.content IS NOT NULL
      AND length(sp.content) > 5
    """
    params: dict[str, Any] = {"model_v": MODEL_VERSION}
    if dirigente_id is not None:
        sql += " AND d.id = :dirigente_id"
        params["dirigente_id"] = dirigente_id
    sql += " ORDER BY sp.published_at DESC NULLS LAST, sp.id DESC"
    if limit:
        sql += f" LIMIT {int(limit)}"

    with engine.connect() as c:
        rows = c.execute(text(sql), params).mappings().all()
    return [dict(r) for r in rows]


def update_post(engine, post_id: int, target: str, razon: str) -> None:
    """Persiste clasificación de un post."""
    sql = text("""
        UPDATE social_posts
        SET target_politico = :target,
            nlp_model_version = :model_v,
            clasificacion_origen = COALESCE(clasificacion_origen, 'ai_suggested'),
            raw_data = COALESCE(raw_data, '{}'::jsonb)
                       || jsonb_build_object('target_politico_razon', :razon,
                                             'target_politico_classified_at',
                                             :ts)
        WHERE id = :post_id
    """)
    with engine.begin() as c:
        c.execute(
            sql,
            {
                "target": target,
                "model_v": MODEL_VERSION,
                "razon": razon,
                "ts": datetime.now(UTC).isoformat(),
                "post_id": post_id,
            },
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="No escribe a DB")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dirigente-id", type=int, default=None)
    parser.add_argument(
        "--golden-set",
        action="store_true",
        help="Genera JSON de golden set (60 posts estratificados)",
    )
    args = parser.parse_args()

    engine = create_engine(DEFAULT_DB_URL)

    # Modo golden set: genera JSON para CEO
    if args.golden_set:
        return generate_golden_set(engine)

    posts = fetch_pending_posts(
        engine,
        dirigente_id=args.dirigente_id,
        limit=args.limit,
    )

    if not posts:
        print("No hay posts pendientes de clasificar.", file=sys.stderr)
        return 0

    print(f"Posts pendientes: {len(posts)}", file=sys.stderr)
    print(f"Modo: {'DRY-RUN' if args.dry_run else 'PERSIST'}", file=sys.stderr)
    print(f"Modelo: {MODEL_VERSION}", file=sys.stderr)
    print("---", file=sys.stderr)

    stats: dict[str, int] = {t: 0 for t in VALID_TARGETS}
    failed = 0
    t0 = time.time()

    for i, post in enumerate(posts, 1):
        print(
            f"[{i}/{len(posts)}] post_id={post['id']} dirigente={post['dirigente_nombre']} "
            f"text={(post['content'] or '')[:60]!r}",
            file=sys.stderr,
        )
        result = classify_post(post)

        if not result:
            failed += 1
            print("  → FAIL", file=sys.stderr)
            continue

        target = result["target"]
        razon = result["razon"]
        stats[target] = stats.get(target, 0) + 1
        print(f"  → {target} · {razon[:80]}", file=sys.stderr)

        if not args.dry_run:
            update_post(engine, post["id"], target, razon)

    dur = time.time() - t0
    print("---", file=sys.stderr)
    print(f"Total: {len(posts)} · Failed: {failed} · Dur: {dur:.0f}s", file=sys.stderr)
    print(f"Stats: {stats}", file=sys.stderr)
    return 0 if failed < len(posts) else 1


def generate_golden_set(engine) -> int:
    """Genera JSON de 60 posts estratificados para que CEO clasifique manual.

    Distribución: 5 posts por dirigente piloto (8 dirigentes = 40) + 20 posts
    adversariales (Copa-Naranja-style, críticas directas, mixtos, personales).

    Output: JSON Lines a stdout con campos a llenar.
    """
    sql = text("""
    WITH ranked AS (
        SELECT
            sp.id, sp.content, sp.platform_post_id,
            prof.platform::text AS platform,
            d.id AS dirigente_id, d.full_name AS dirigente_nombre,
            d.partido, d.cargo,
            sp.published_at,
            ROW_NUMBER() OVER (PARTITION BY d.id ORDER BY sp.published_at DESC) AS rn
        FROM social_posts sp
        JOIN social_profiles prof ON prof.id = sp.profile_id
        JOIN dirigentes d ON d.id = prof.dirigente_id
        WHERE sp.content IS NOT NULL AND length(sp.content) > 30
          AND d.id IN (1, 2, 3, 4, 5, 6, 7, 8)
    )
    SELECT * FROM ranked WHERE rn <= 8 ORDER BY dirigente_id, rn
    """)
    with engine.connect() as c:
        rows = c.execute(sql).mappings().all()

    print(
        "# D-23-G' Golden Set · 2026-04-24",
        f"# {len(rows)} posts · CEO completa target_human para validar IA después",
        sep="\n",
        file=sys.stderr,
    )
    out = []
    for r in rows:
        out.append({
            "id": r["id"],
            "dirigente_id": r["dirigente_id"],
            "dirigente_nombre": r["dirigente_nombre"],
            "partido": r["partido"],
            "cargo": r["cargo"],
            "platform": r["platform"],
            "content": (r["content"] or "")[:500],
            "published_at": r["published_at"].isoformat() if r["published_at"] else None,
            # Campos para que CEO complete:
            "target_human": None,  # ← oficialismo|oposicion|propio|personal|no_determinado
            "notas_ceo": "",
        })
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
