"""S7 (F-NLP-3 reformulado) · Reporte global recompute matriz v2.

Hallazgo de S3: NI `social_comments` NI `social_posts` tienen columna
`score_politico` en BD · score se computa on-the-fly. Tabla
`actividad_politica_alineada` tampoco existe · KPI agregado en runtime.

Este reporte NO persiste · solo MUESTRA qué scores asignaría la matriz v2
actual (60 reglas: 32 post + 28 comment) sobre los 2696 comments populated
y los posts con tono_discurso, agregando por dirigente. Insumo para reunión
de mañana con Solano/Piña/Ballesteros.

Outputs:
- /tmp/RECOMPUTE-GLOBAL-2026-05-09.md  (reporte humano)
- /tmp/RECOMPUTE-GLOBAL-2026-05-09.json (datos crudos)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, "/app")

from app.services.score_recompute import (  # noqa: E402
    recompute_score_comment,
    recompute_score_post,
)

OUT_MD = "/tmp/RECOMPUTE-GLOBAL-2026-05-09.md"
OUT_JSON = "/tmp/RECOMPUTE-GLOBAL-2026-05-09.json"


def _bucket(score: int) -> str:
    if score > 0:
        return "pos"
    if score < 0:
        return "neg"
    return "zero"


async def main() -> int:
    eng = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    Session = async_sessionmaker(eng, expire_on_commit=False)

    async with Session() as db:
        # ----------------------------------------------------------------
        # 1. Comments con NLP populated + dirigente
        # ----------------------------------------------------------------
        comment_rows = (
            await db.execute(
                text(
                    """
                    SELECT
                        sc.id,
                        sc.nlp_tono,
                        sc.nlp_target,
                        pr.dirigente_id,
                        d.full_name,
                        d.rol_politico
                    FROM social_comments sc
                    JOIN social_posts sp     ON sp.id = sc.parent_post_id
                    JOIN social_profiles pr  ON pr.id = sp.profile_id
                    JOIN dirigentes d        ON d.id = pr.dirigente_id
                    WHERE sc.nlp_tono IS NOT NULL
                    """
                )
            )
        ).all()
        total_comments = len(comment_rows)
        print(f"Comments con NLP + dirigente: {total_comments}")

        comment_results: list[dict] = []
        comment_combo = Counter()
        comment_match = 0
        for r in comment_rows:
            score = await recompute_score_comment(db, r.id)
            matched = score != 0
            if matched:
                comment_match += 1
            comment_combo[(r.nlp_tono, r.nlp_target)] += 1
            comment_results.append(
                {
                    "id": r.id,
                    "dirigente_id": r.dirigente_id,
                    "dirigente_nombre": r.full_name,
                    "rol": r.rol_politico,
                    "tono": r.nlp_tono,
                    "target": r.nlp_target,
                    "score": score,
                    "matched": matched,
                }
            )

        # ----------------------------------------------------------------
        # 2. Posts con clasificación + dirigente
        # ----------------------------------------------------------------
        post_rows = (
            await db.execute(
                text(
                    """
                    SELECT
                        sp.id,
                        sp.tono_discurso,
                        sp.target_politico,
                        pr.dirigente_id,
                        d.full_name,
                        d.rol_politico
                    FROM social_posts sp
                    JOIN social_profiles pr ON pr.id = sp.profile_id
                    JOIN dirigentes d       ON d.id = pr.dirigente_id
                    WHERE sp.tono_discurso IS NOT NULL
                    """
                )
            )
        ).all()
        total_posts = len(post_rows)
        print(f"Posts con clasificación + dirigente: {total_posts}")

        post_results: list[dict] = []
        post_combo = Counter()
        post_match = 0
        for r in post_rows:
            score = await recompute_score_post(db, r.id)
            matched = score != 0
            if matched:
                post_match += 1
            post_combo[(r.tono_discurso, r.target_politico)] += 1
            post_results.append(
                {
                    "id": r.id,
                    "dirigente_id": r.dirigente_id,
                    "dirigente_nombre": r.full_name,
                    "rol": r.rol_politico,
                    "tono": r.tono_discurso,
                    "target": r.target_politico,
                    "score": score,
                    "matched": matched,
                }
            )

        # ----------------------------------------------------------------
        # 3. Agregar por dirigente
        # ----------------------------------------------------------------
        per_dirigente: dict[int, dict] = defaultdict(
            lambda: {
                "name": "",
                "rol": "",
                "n_comments": 0,
                "c_pos": 0,
                "c_neg": 0,
                "c_zero": 0,
                "c_sum": 0,
                "n_posts": 0,
                "p_pos": 0,
                "p_neg": 0,
                "p_zero": 0,
                "p_sum": 0,
            }
        )

        for s in comment_results:
            d = per_dirigente[s["dirigente_id"]]
            d["name"] = s["dirigente_nombre"] or "?"
            d["rol"] = s["rol"] or "?"
            d["n_comments"] += 1
            d[f"c_{_bucket(s['score'])}"] += 1
            d["c_sum"] += s["score"]

        for s in post_results:
            d = per_dirigente[s["dirigente_id"]]
            d["name"] = s["dirigente_nombre"] or "?"
            d["rol"] = s["rol"] or "?"
            d["n_posts"] += 1
            bucket = _bucket(s["score"])
            d[f"p_{bucket}"] += 1
            d["p_sum"] += s["score"]

        # ----------------------------------------------------------------
        # 4. Métricas globales
        # ----------------------------------------------------------------
        c_match_rate = (comment_match / total_comments) if total_comments else 0.0
        p_match_rate = (post_match / total_posts) if total_posts else 0.0

        c_pos_total = sum(1 for s in comment_results if s["score"] > 0)
        c_neg_total = sum(1 for s in comment_results if s["score"] < 0)
        c_zero_total = sum(1 for s in comment_results if s["score"] == 0)
        p_pos_total = sum(1 for s in post_results if s["score"] > 0)
        p_neg_total = sum(1 for s in post_results if s["score"] < 0)
        p_zero_total = sum(1 for s in post_results if s["score"] == 0)

        # ----------------------------------------------------------------
        # 5. Top dirigente por KPI Σ
        # ----------------------------------------------------------------
        kpi_ranked = sorted(
            per_dirigente.items(),
            key=lambda kv: -(kv[1]["c_sum"] + kv[1]["p_sum"]),
        )
        top_dirigente = kpi_ranked[0] if kpi_ranked else None

        # ----------------------------------------------------------------
        # 6. JSON output
        # ----------------------------------------------------------------
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_comments": total_comments,
                "total_posts": total_posts,
                "comments_match_rate": round(c_match_rate, 4),
                "posts_match_rate": round(p_match_rate, 4),
                "comments_pos": c_pos_total,
                "comments_neg": c_neg_total,
                "comments_zero": c_zero_total,
                "posts_pos": p_pos_total,
                "posts_neg": p_neg_total,
                "posts_zero": p_zero_total,
            },
            "per_dirigente": [
                {
                    "dirigente_id": did,
                    **info,
                    "kpi_total": info["c_sum"] + info["p_sum"],
                }
                for did, info in kpi_ranked
            ],
            "top_combos_comments": [
                {"tono": t, "target": tg, "n": n}
                for (t, tg), n in comment_combo.most_common(10)
            ],
            "top_combos_posts": [
                {"tono": t, "target": tg, "n": n}
                for (t, tg), n in post_combo.most_common(10)
            ],
        }
        Path(OUT_JSON).write_text(json.dumps(payload, ensure_ascii=False, indent=2))

        # ----------------------------------------------------------------
        # 7. Markdown output
        # ----------------------------------------------------------------
        md: list[str] = []
        md.append("# Recompute Global · Matriz v2 (60 reglas)\n\n")
        md.append("**Fecha:** 2026-05-09  \n")
        md.append("**Sprint:** S7 (F-NLP-3 reformulado · reporte global, NO persiste)  \n")
        md.append("**Insumo para:** reunión Solano / Piña / Ballesteros  \n\n")

        md.append("## Resumen ejecutivo\n\n")
        md.append(f"- **Comments procesados:** {total_comments}\n")
        md.append(f"- **Comments con match en matriz (score≠0):** {comment_match} ({c_match_rate*100:.1f}%)\n")
        md.append(f"- **Comments sin match (score=0):** {c_zero_total} ({(c_zero_total/total_comments*100) if total_comments else 0:.1f}%)\n")
        md.append(f"- **Posts procesados:** {total_posts}\n")
        if total_posts:
            md.append(f"- **Posts con match en matriz (score≠0):** {post_match} ({p_match_rate*100:.1f}%)\n")
            md.append(f"- **Posts sin match (score=0):** {p_zero_total} ({p_zero_total/total_posts*100:.1f}%)\n")
        if top_dirigente:
            did, info = top_dirigente
            md.append(
                f"- **Top dirigente por KPI Σ:** {info['name']} ({info['rol']}) · "
                f"comments={info['n_comments']} posts={info['n_posts']} "
                f"Σscore={info['c_sum'] + info['p_sum']:+d}\n"
            )
        md.append("\n")

        md.append("## KPI por dirigente\n\n")
        md.append(
            "| Dirigente | rol | n_comm | c+ | c− | c0 | n_post | p+ | p− | p0 | KPI Σ |\n"
        )
        md.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
        for did, info in kpi_ranked:
            kpi = info["c_sum"] + info["p_sum"]
            md.append(
                f"| {info['name']} | {info['rol']} | {info['n_comments']} | "
                f"{info['c_pos']} | {info['c_neg']} | {info['c_zero']} | "
                f"{info['n_posts']} | {info['p_pos']} | {info['p_neg']} | "
                f"{info['p_zero']} | {kpi:+d} |\n"
            )
        md.append("\n")

        md.append("## Distribución corpus comments — Top 10 (tono × target)\n\n")
        md.append("| tono | target | count | % corpus |\n|---|---|---:|---:|\n")
        for (t, tg), n in comment_combo.most_common(10):
            pct = (n / total_comments * 100) if total_comments else 0
            md.append(f"| {t} | {tg} | {n} | {pct:.1f}% |\n")
        md.append("\n")

        md.append("## Distribución corpus posts — Top 10 (tono × target)\n\n")
        md.append("| tono | target | count | % corpus |\n|---|---|---:|---:|\n")
        for (t, tg), n in post_combo.most_common(10):
            pct = (n / total_posts * 100) if total_posts else 0
            md.append(f"| {t} | {tg} | {n} | {pct:.1f}% |\n")
        md.append("\n")

        md.append("## Hallazgos\n\n")
        md.append(
            f"- **Cobertura de matriz en comments:** {c_match_rate*100:.1f}% "
            f"({comment_match}/{total_comments}). El residual {(1-c_match_rate)*100:.1f}% "
            "queda en score=0 por una de tres razones: (a) combinación rol/tono/target "
            "sin regla en las 28 reglas comment, (b) target='no_determinado' "
            "que la matriz no evalúa por diseño, (c) el mapper v3.0.1 cae a una "
            "tupla v2 sin entrada en la matriz.\n"
        )
        if total_posts:
            md.append(
                f"- **Cobertura de matriz en posts:** {p_match_rate*100:.1f}% "
                f"({post_match}/{total_posts}). Posts ya emiten vocab v2 directo desde "
                "el clasificador LLM (D-23-G), por lo que el miss aquí indica gap real "
                "de las 32 reglas post · es la lista corta de combinaciones a discutir "
                "con Solano/Piña/Ballesteros para ampliar matriz.\n"
            )
        else:
            md.append("- **Cobertura de matriz en posts:** sin posts populated en BD.\n")
        # Top combos sin match
        miss_combos_comm = Counter(
            (s["tono"], s["target"]) for s in comment_results if not s["matched"]
        )
        if miss_combos_comm:
            md.append(
                "- **Top 5 combinaciones comment sin regla** (candidatas a ampliar matriz):\n"
            )
            for (t, tg), n in miss_combos_comm.most_common(5):
                md.append(f"  - `{t} × {tg}` → {n} comments\n")
        miss_combos_post = Counter(
            (s["tono"], s["target"]) for s in post_results if not s["matched"]
        )
        if miss_combos_post:
            md.append(
                "- **Top 5 combinaciones post sin regla** (candidatas a ampliar matriz):\n"
            )
            for (t, tg), n in miss_combos_post.most_common(5):
                md.append(f"  - `{t} × {tg}` → {n} posts\n")
        md.append("\n")

        md.append("## Insumos para reunión Solano / Piña / Ballesteros\n\n")
        md.append(
            "1. **Tasa de cobertura actual** — la matriz v2 cubre "
            f"{c_match_rate*100:.0f}% de comments y "
            f"{p_match_rate*100:.0f}% de posts populated. El resto pasa a score=0 "
            "y NO aporta a la KPI de Actividad Política Alineada.\n"
        )
        md.append(
            "2. **Decisión de producto** — ampliar matriz hasta cerrar el gap "
            "vs aceptar score=0 como categoría neutral (la mayoría del corpus "
            "MC es tono institucional/celebratorio sobre target gobierno-aliado, "
            "que la matriz NO premia ni castiga).\n"
        )
        md.append(
            "3. **Validación de signos** — confirmar con los 3 que las combinaciones "
            "que SÍ matchean asignan el signo correcto desde la lógica MC=oposición "
            "(crítica al gobierno = +1, ataque a aliado = -1, etc.).\n"
        )
        md.append(
            "4. **NO se ejecutó UPDATE en BD.** Este reporte es lectura pura sobre "
            "2696 comments + posts populated. La decisión sobre persistir scores "
            "(crear columna o tabla `actividad_politica_alineada`) queda para §9.8 "
            "post-reunión.\n"
        )

        Path(OUT_MD).write_text("".join(md))

        print("=" * 60)
        print(f"MD   → {OUT_MD}")
        print(f"JSON → {OUT_JSON}")
        print(
            f"Comments: {total_comments} (match {comment_match}, "
            f"{c_match_rate*100:.1f}%) · "
            f"Posts: {total_posts} (match {post_match}, "
            f"{p_match_rate*100:.1f}%)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
