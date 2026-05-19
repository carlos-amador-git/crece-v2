"""S8 · Ground truth baseline 100 rows estratificada (seed=42).

Genera muestra estratificada de 100 comments con NLP populated para servir
de baseline humano contra el output del mapper v3.

Estratificación:
- Grupos = (nlp_tono, nlp_target) del runner Gemma
- Cuota proporcional al tamaño de cada celda hasta sumar 100
- Sample dentro de cada celda con random_state=42 (numpy RNG)
- Reproducible: misma BD + seed=42 → mismo CSV

Filtros:
- nlp_tono IS NOT NULL (descarta comments sin clasificar)
- dirigentes.rol_politico = 'oposicion' (todo el roster es oposición)
- social_comments.created_at >= NOW() - INTERVAL '90 days' (recientes)

Output:
- backend/evaluations/ground_truth/2026-05-09-100rows.csv
- /tmp/SAMPLE-GROUND-TRUTH-2026-05-09.md (resumen + instrucciones anotación)

Uso:
    docker exec -e DATABASE_URL='postgresql+asyncpg://crece:crece_dev@db:5432/crece' \
        crece-backend python /app/scripts/sample_ground_truth_100.py

Después: Linda anota 30 rows como semilla. Solano/Piña/Ballesteros completan
el resto via el editor frontend (esos van a hitl_edits_log, no al CSV).
"""
from __future__ import annotations

import asyncio
import csv
import os
import random
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, "/app")

from app.nlp.matriz_v3_mapper import map_runner_to_v2  # noqa: E402

SEED = 42
TARGET_N = 100
DATE_TAG = "2026-05-09"

# Paths: el script corre dentro del contenedor (CWD /app), pero también queremos
# escribir al volumen montado para que aparezca en host.
CSV_PATH_CONTAINER = Path("/app/evaluations/ground_truth") / f"{DATE_TAG}-100rows.csv"
MD_PATH = Path(f"/tmp/SAMPLE-GROUND-TRUTH-{DATE_TAG}.md")

CSV_COLUMNS = [
    "comment_id",
    "content",
    "dirigente_id",
    "dirigente_nombre",
    "rol_politico",
    "platform",
    "runner_tono",
    "runner_target",
    "mapper_tono_v2",
    "mapper_target_v2",
    "score_actual",
    "humano_tono",
    "humano_target",
    "humano_off_topic",
    "humano_nota",
]


def _truncate(text_value: str | None, limit: int = 500) -> str:
    if not text_value:
        return ""
    if len(text_value) <= limit:
        return text_value
    return text_value[: limit - 1] + "…"


def _allocate_quotas(cell_counts: dict[tuple[str, str], int], target: int) -> dict[tuple[str, str], int]:
    """Cuota proporcional con largest-remainder para sumar exactamente target."""
    total = sum(cell_counts.values())
    if total == 0:
        return {k: 0 for k in cell_counts}

    raw: dict[tuple[str, str], float] = {
        k: (v / total) * target for k, v in cell_counts.items()
    }
    floor: dict[tuple[str, str], int] = {k: int(v) for k, v in raw.items()}
    # Cap por tamaño disponible en la celda
    floor = {k: min(floor[k], cell_counts[k]) for k in floor}

    assigned = sum(floor.values())
    remaining = target - assigned

    # Largest-remainder para repartir lo que falta
    remainders = sorted(
        (
            (k, raw[k] - int(raw[k]))
            for k in raw
            if floor[k] < cell_counts[k]
        ),
        key=lambda kv: -kv[1],
    )
    i = 0
    while remaining > 0 and remainders:
        k, _ = remainders[i % len(remainders)]
        if floor[k] < cell_counts[k]:
            floor[k] += 1
            remaining -= 1
        i += 1
        # Evitar loop infinito si todas las celdas están full
        if i > len(remainders) * 4:
            break

    return floor


async def main() -> int:
    eng = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    SessionLocal = async_sessionmaker(eng, expire_on_commit=False)

    rng = random.Random(SEED)

    async with SessionLocal() as db:
        # 1. Universo: comments con NLP + dirigente oposición + 90 días
        rows = (
            await db.execute(
                text(
                    """
                    SELECT
                        sc.id              AS comment_id,
                        sc.content         AS content,
                        sc.nlp_tono        AS runner_tono,
                        sc.nlp_target      AS runner_target,
                        pr.platform        AS platform,
                        d.id               AS dirigente_id,
                        d.full_name        AS dirigente_nombre,
                        d.rol_politico     AS rol_politico,
                        pr.handle          AS profile_handle
                    FROM social_comments sc
                    JOIN social_posts sp ON sp.id = sc.parent_post_id
                    JOIN social_profiles pr ON pr.id = sp.profile_id
                    JOIN dirigentes d ON d.id = pr.dirigente_id
                    WHERE sc.nlp_tono IS NOT NULL
                      AND sc.nlp_target IS NOT NULL
                      AND d.rol_politico = 'oposicion'
                      AND sc.created_at >= NOW() - INTERVAL '90 days'
                    ORDER BY sc.id
                    """
                )
            )
        ).all()

        if not rows:
            print("BLOCKER: universo vacío. Verificar filtros (rol_politico, 90d, nlp_tono).")
            return 1

        print(f"Universo: {len(rows)} comments candidatos")

        # 2. Estratificación por (runner_tono, runner_target)
        cells: dict[tuple[str, str], list] = defaultdict(list)
        for r in rows:
            cells[(r.runner_tono, r.runner_target)].append(r)

        cell_sizes = {k: len(v) for k, v in cells.items()}
        target_n = min(TARGET_N, len(rows))
        quotas = _allocate_quotas(cell_sizes, target_n)

        print(f"Celdas (runner_tono, runner_target): {len(cells)}")
        print(f"Cuotas asignadas suman: {sum(quotas.values())} (target {target_n})")

        # 3. Sample reproducible por celda
        sampled = []
        for cell_key, candidates in cells.items():
            quota = quotas.get(cell_key, 0)
            if quota <= 0:
                continue
            # Shuffle determinista con seed por celda
            ordered = sorted(candidates, key=lambda r: r.comment_id)
            local_rng = random.Random(SEED ^ hash(cell_key))
            local_rng.shuffle(ordered)
            sampled.extend(ordered[:quota])

        # Por si hubo celdas con quota=0 truncadas, recortar a TARGET_N
        rng.shuffle(sampled)
        sampled = sampled[:target_n]
        print(f"Sample final: {len(sampled)} rows")

        # 4. Para cada row: aplicar mapper v3 + lookup score actual
        out_rows = []
        score_lookup_cache: dict[tuple[str, str, str], int | None] = {}
        for r in sampled:
            mapper_res = map_runner_to_v2(
                r.runner_tono,
                r.runner_target,
                comment_text=r.content or "",
                is_self_authored=False,  # autopromo runtime no aplica al ground truth
            )
            tono_v2 = mapper_res.tono_v2
            target_v2 = mapper_res.target_v2

            cache_key = (r.rol_politico, tono_v2, target_v2)
            if cache_key not in score_lookup_cache:
                score_row = (
                    await db.execute(
                        text(
                            """
                            SELECT score_politico
                            FROM framework_matrix_defaults
                            WHERE version = 'v1'
                              AND rol = :rol
                              AND tono = :tono
                              AND target = :target
                              AND contexto = 'comment_tercero'
                            LIMIT 1
                            """
                        ),
                        {"rol": r.rol_politico, "tono": tono_v2, "target": target_v2},
                    )
                ).first()
                score_lookup_cache[cache_key] = score_row[0] if score_row else None
            score_actual = score_lookup_cache[cache_key]

            out_rows.append(
                {
                    "comment_id": r.comment_id,
                    "content": _truncate(r.content, 500),
                    "dirigente_id": r.dirigente_id,
                    "dirigente_nombre": r.dirigente_nombre or "",
                    "rol_politico": r.rol_politico or "",
                    "platform": r.platform or "",
                    "runner_tono": r.runner_tono,
                    "runner_target": r.runner_target,
                    "mapper_tono_v2": tono_v2,
                    "mapper_target_v2": target_v2,
                    "score_actual": score_actual if score_actual is not None else "",
                    "humano_tono": "",
                    "humano_target": "",
                    "humano_off_topic": "",
                    "humano_nota": "",
                }
            )

        # 5. Escribir CSV
        CSV_PATH_CONTAINER.parent.mkdir(parents=True, exist_ok=True)
        with CSV_PATH_CONTAINER.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=CSV_COLUMNS,
                quoting=csv.QUOTE_ALL,
            )
            writer.writeheader()
            writer.writerows(out_rows)
        print(f"CSV → {CSV_PATH_CONTAINER}  ({len(out_rows)} rows)")

        # 6. Distribución para reporte MD
        dist_runner = Counter((r["runner_tono"], r["runner_target"]) for r in out_rows)
        dist_mapper = Counter((r["mapper_tono_v2"], r["mapper_target_v2"]) for r in out_rows)
        dist_dirigente = Counter(r["dirigente_nombre"] for r in out_rows)
        dist_platform = Counter(r["platform"] for r in out_rows)
        score_dist = Counter(r["score_actual"] for r in out_rows)

        # 7. MD con instrucciones de anotación
        md = []
        md.append("# Ground truth baseline · 100 rows seed=42\n\n")
        md.append(f"**Fecha:** {DATE_TAG}  \n")
        md.append("**Sprint:** S8 · Editor HITL evaluación NLP  \n")
        md.append(f"**Seed:** {SEED}  \n")
        md.append(f"**Universo:** {len(rows)} comments (NLP populated · "
                  "rol=oposicion · ≤90 días)  \n")
        md.append(f"**Sample:** {len(out_rows)} rows estratificadas\n\n")

        md.append(f"**CSV:** `backend/evaluations/ground_truth/{DATE_TAG}-100rows.csv`\n\n")

        md.append("## Distribución por (runner_tono, runner_target)\n\n")
        md.append("| runner_tono | runner_target | n |\n|---|---|---:|\n")
        for (tono, tgt), n in dist_runner.most_common():
            md.append(f"| {tono} | {tgt} | {n} |\n")

        md.append("\n## Distribución post-mapper v3 (tono_v2, target_v2)\n\n")
        md.append("| mapper_tono_v2 | mapper_target_v2 | n |\n|---|---|---:|\n")
        for (tono, tgt), n in dist_mapper.most_common():
            md.append(f"| {tono} | {tgt} | {n} |\n")

        md.append("\n## Top 5 dirigentes representados\n\n")
        md.append("| dirigente | n |\n|---|---:|\n")
        for nombre, n in dist_dirigente.most_common(5):
            md.append(f"| {nombre or '?'} | {n} |\n")

        md.append("\n## Distribución por plataforma\n\n")
        md.append("| platform | n |\n|---|---:|\n")
        for plat, n in dist_platform.most_common():
            md.append(f"| {plat or '?'} | {n} |\n")

        md.append("\n## Score actual (lookup matriz v2 contexto=comment_tercero)\n\n")
        md.append("| score | n |\n|---|---:|\n")
        for score, n in sorted(score_dist.items(), key=lambda kv: (kv[0] == "", kv[0])):
            label = "sin match" if score == "" else str(score)
            md.append(f"| {label} | {n} |\n")

        md.append("\n## Instrucciones de anotación\n\n")
        md.append("**Para Linda (30 rows semilla):**\n\n")
        md.append("1. Abre `backend/evaluations/ground_truth/" + DATE_TAG + "-100rows.csv` "
                  "en LibreOffice/Google Sheets.\n")
        md.append("2. Por cada row, lee `content` y decide independientemente del runner:\n")
        md.append("   - `humano_tono` ∈ "
                  "`{critico, propositivo, celebratorio, informativo, solidario, ataque, personal}`\n")
        md.append("   - `humano_target` ∈ "
                  "`{gobierno, oposicion, ciudadania, medios, autopromocion, tema_especifico, dirigente}`\n")
        md.append("   - `humano_off_topic` ∈ `{TRUE, FALSE}` — TRUE si el comment "
                  "es spam/ruido/no clasificable\n")
        md.append("   - `humano_nota`: opcional, texto libre con el porqué (especialmente "
                  "si discrepa del mapper)\n")
        md.append("3. Guarda como UTF-8. NO toques `comment_id` ni las columnas runner/mapper.\n\n")

        md.append("**Para Solano/Piña/Ballesteros (reunión 2026-05-10):**\n\n")
        md.append("1. Entran a `/dashboard/settings/evaluacion-nlp` (S4 frontend).\n")
        md.append("2. Validan/editan SUS comments — esos cambios van a `hitl_edits_log`, "
                  "NO al CSV.\n")
        md.append("3. Después S6 (`hitl_review_batch.py`) cruza el CSV (anotación Linda) "
                  "+ audit_log (anotación dirigentes) → reporte unificado para "
                  "Claude+Gemini iterar mapper.\n\n")

        md.append("## Cómo se cruza con el audit log (S6 input)\n\n")
        md.append("```\n")
        md.append("CSV ground_truth (Linda, 30 rows)        ┐\n")
        md.append("                                          ├──> S6 batch_review\n")
        md.append("hitl_edits_log (dirigentes, ~70+ rows)    ┘    └─> Claude+Gemini\n")
        md.append("                                                   reporte mejoras\n")
        md.append("                                                   mapper v3.1\n")
        md.append("```\n\n")

        md.append("## Reproducibilidad\n\n")
        md.append(f"- Seed numpy/python random: `{SEED}`\n")
        md.append(f"- Filtros SQL: rol='oposicion' · 90 días · nlp_tono NOT NULL\n")
        md.append("- Re-ejecutar con la misma BD produce el mismo CSV (mod inserts/deletes posteriores)\n")

        MD_PATH.write_text("".join(md), encoding="utf-8")
        print(f"MD  → {MD_PATH}")

        # 8. Print resumen consola
        print("=" * 60)
        print(f"Universo: {len(rows)} | Sample: {len(out_rows)} | Celdas: {len(cells)}")
        print(f"Top runner cells: {dist_runner.most_common(5)}")
        print(f"Top mapper cells: {dist_mapper.most_common(5)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
