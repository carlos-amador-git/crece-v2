"""S5 reporte delta · impacto de matriz v2 poblada sobre scores políticos.

Hallazgo en S1-S2 (2026-05-09): la tabla `framework_matrix_defaults` estaba
VACÍA en BD. `get_political_score()` retornaba fallback 0 para todo comment.
Después de poblar 53 reglas (32 post + 21 comment), los scores son reales.

Este reporte muestra:
1. Cuántos comments cambian de score (de 0 → ≠0)
2. Distribución antes/después por (rol, tono, target)
3. KPI agregado por dirigente piloto (impacto que vería el usuario)

Output: /tmp/REPORTE-DELTA-SCORE-2026-05-09.md
"""
from __future__ import annotations

import asyncio
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, "/app")

OUT_MD = "/tmp/REPORTE-DELTA-SCORE-2026-05-09.md"


async def main() -> int:
    eng = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    S = async_sessionmaker(eng, expire_on_commit=False)

    async with S() as db:
        # 1. Sample 500 comments con nlp_tono populated + dirigente_rol
        rows = (await db.execute(text("""
            SELECT
                sc.id, sc.nlp_tono, sc.nlp_target, sc.content,
                sp.profile_id,
                pr.handle, pr.dirigente_id,
                d.full_name, d.rol_politico
            FROM social_comments sc
            JOIN social_posts sp ON sp.id = sc.parent_post_id
            JOIN social_profiles pr ON pr.id = sp.profile_id
            LEFT JOIN dirigentes d ON d.id = pr.dirigente_id
            WHERE sc.nlp_tono IS NOT NULL
              AND d.rol_politico IS NOT NULL
            ORDER BY sc.created_at DESC
            LIMIT 500
        """))).all()

        print(f"Sample: {len(rows)} comments con nlp_tono + dirigente rol")

        # 2. Para cada comment, lookup score en matriz v2 (contexto=comment_tercero)
        scored = []
        misses = 0
        for r in rows:
            score_row = (await db.execute(text("""
                SELECT score_politico
                FROM framework_matrix_defaults
                WHERE version = 'v1'
                  AND rol = :rol
                  AND tono = :tono
                  AND target = :target
                  AND contexto = 'comment_tercero'
                LIMIT 1
            """), {
                "rol": r.rol_politico,
                "tono": r.nlp_tono,
                "target": r.nlp_target,
            })).first()
            score = score_row[0] if score_row else None
            if score is None:
                misses += 1
            scored.append({
                "id": r.id,
                "tono": r.nlp_tono,
                "target": r.nlp_target,
                "rol": r.rol_politico,
                "dirigente_id": r.dirigente_id,
                "dirigente_nombre": r.full_name,
                "score_pre": 0,        # antes de S2 todo era 0 (matriz vacía)
                "score_post": score if score is not None else 0,
                "matched": score is not None,
            })

        # 3. Métricas agregadas
        changed = sum(1 for s in scored if s["score_post"] != s["score_pre"])
        positive = sum(1 for s in scored if s["score_post"] > 0)
        negative = sum(1 for s in scored if s["score_post"] < 0)
        zero = sum(1 for s in scored if s["score_post"] == 0)

        # 4. Por dirigente
        per_dirigente = defaultdict(lambda: {"n": 0, "sum_pre": 0, "sum_post": 0,
                                              "name": "", "rol": ""})
        for s in scored:
            d = per_dirigente[s["dirigente_id"]]
            d["n"] += 1
            d["sum_pre"] += s["score_pre"]
            d["sum_post"] += s["score_post"]
            d["name"] = s["dirigente_nombre"]
            d["rol"] = s["rol"]

        # 5. Combinaciones más frecuentes sin match
        miss_combos = Counter(
            (s["rol"], s["tono"], s["target"])
            for s in scored if not s["matched"]
        )

        # 6. Reporte
        md = []
        md.append("# Delta Score Político · Impacto matriz v2 poblada\n\n")
        md.append("**Fecha:** 2026-05-09  \n")
        md.append("**Sprint:** S5 post-/sprint-implement v3 mapper  \n\n")

        md.append("## Hallazgo crítico\n\n")
        md.append("La tabla `framework_matrix_defaults` estaba **VACÍA** en BD ")
        md.append("hasta hoy 2026-05-09. La migración `f7a8b9c0d1e2_political_framework.py` ")
        md.append("estaba huérfana del chain alembic — nunca se aplicó. Como resultado, ")
        md.append("`get_political_score()` retornaba **fallback 0 para todo comment**, ")
        md.append("invalidando silenciosamente el KPI \"Sentimiento Político Ajustado\".\n\n")
        md.append("Después de S1+S2: 53 reglas pobladas (32 post + 21 comment).\n\n")

        md.append("## Resumen ejecutivo\n\n")
        md.append(f"- **Comments sample:** {len(rows)} (los 500 más recientes con NLP + dirigente)\n")
        md.append(f"- **Comments con score que CAMBIA (pre 0 → post ≠0):** {changed} ({changed/len(rows)*100:.1f}%)\n")
        md.append(f"- **Score positivo:** {positive} ({positive/len(rows)*100:.1f}%)\n")
        md.append(f"- **Score negativo:** {negative} ({negative/len(rows)*100:.1f}%)\n")
        md.append(f"- **Score 0 / sin match en matriz:** {zero - 0} ({zero/len(rows)*100:.1f}%)\n")
        md.append(f"- **Misses (combinación rol/tono/target sin regla):** {misses} ({misses/len(rows)*100:.1f}%)\n\n")

        md.append("## KPI agregado por dirigente\n\n")
        md.append("| Dirigente | rol | comments | Σscore pre | Σscore post | Δ |\n")
        md.append("|---|---|---:|---:|---:|---:|\n")
        for d_id, info in sorted(per_dirigente.items(), key=lambda kv: -kv[1]["n"]):
            delta = info["sum_post"] - info["sum_pre"]
            md.append(f"| {info['name'] or '?'} | {info['rol']} | {info['n']} | {info['sum_pre']} | {info['sum_post']} | {delta:+d} |\n")

        md.append("\n## Combinaciones (rol, tono, target) sin regla en matriz\n\n")
        md.append("Top 15 combinaciones más frecuentes que retornan 0 por falta de regla:\n\n")
        md.append("| rol | tono | target | count |\n|---|---|---|---:|\n")
        for combo, n in miss_combos.most_common(15):
            md.append(f"| {combo[0]} | {combo[1]} | {combo[2]} | {n} |\n")

        md.append("\n## Implicación para piloto §9.8\n\n")
        md.append("- **Pre-S2 (hasta hoy):** dashboards mostraban score=0 para todos los comments. ")
        md.append("KPI 'Actividad Política Alineada' computado contra base 0 — métricas distorsionadas.\n")
        md.append("- **Post-S2:** scores reales aplicados. Los dirigentes con engagement positivo ")
        md.append("(propositivo + dirigente target) reciben +1, los con ataque + gobierno reciben -1, etc.\n")
        md.append("- **Recomendación:** pasar batch `recompute_actividad_alineada.py` ")
        md.append("sobre los 2696 comments populated para que el dashboard refleje scores reales antes del gate.\n\n")

        md.append("## Pendiente D+1\n\n")
        md.append("- Ground truth humano 100 rows (validar concordancia v3 mapper vs anotación)\n")
        md.append("- UI dual labels opción B (frontend, 1.5h)\n")
        md.append("- Recomputar `actividad_politica_alineada` con scores nuevos sobre 2696 comments\n")

        Path(OUT_MD).write_text("".join(md))
        print(f"\nReporte → {OUT_MD}")
        print("=" * 60)
        print(f"Sample: {len(rows)} | Changed: {changed} | Positive: {positive} | Negative: {negative} | Misses: {misses}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
