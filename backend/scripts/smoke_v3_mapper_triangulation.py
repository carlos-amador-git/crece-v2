"""S4 smoke: aplicar mapper v3 sobre 60 comments triangulados (2026-04-18)."""
from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/app")
from app.nlp.matriz_v3_mapper import MapperStats, map_runner_to_v2  # noqa: E402

TRIANG_CSV = "/tmp/triang.csv"
OUT_MD = "/tmp/SMOKE-MAPPER-2026-05-09.md"


def fetch_comment_text(comment_id: int) -> str:
    import asyncio
    import os

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    async def _get():
        eng = create_async_engine(os.environ["DATABASE_URL"])
        S = async_sessionmaker(eng, expire_on_commit=False)
        async with S() as db:
            r = await db.execute(text("SELECT content FROM social_comments WHERE id = :i"),
                                 {"i": comment_id})
            row = r.first()
            return row[0] if row else ""
    return asyncio.run(_get())


def main() -> int:
    rows = list(csv.DictReader(open(TRIANG_CSV)))
    print(f"Loaded {len(rows)} rows")

    results = []
    fallbacks = 0
    valid_v2 = 0  # mapper produjo tono_v2 NO-fallback
    tono_3of3_count = 0
    target_3of3_count = 0

    for row in rows:
        text_comment = ""
        try:
            text_comment = fetch_comment_text(int(row["id"]))
        except Exception:
            pass

        res = map_runner_to_v2(
            tono_runner=row["tono_gemma"],
            target_runner=row["target_gemma"],
            comment_text=text_comment,
        )

        tono_3of3 = (row["tono_claude"] == row["tono_gemini"] == row["tono_gemma"])
        target_3of3 = (row["target_claude"] == row["target_gemini"] == row["target_gemma"])

        if tono_3of3:
            tono_3of3_count += 1
        if target_3of3:
            target_3of3_count += 1

        if res.fallback:
            fallbacks += 1
        else:
            valid_v2 += 1

        results.append({
            "id": row["id"],
            "tono_runner": row["tono_gemma"],
            "tono_v2": res.tono_v2,
            "target_runner": row["target_gemma"],
            "target_v2": res.target_v2,
            "tono_3of3": tono_3of3,
            "target_3of3": target_3of3,
            "fallback": res.fallback,
            "flags": res.flags,
        })

    tono_v2_dist = Counter(r["tono_v2"] for r in results)
    target_v2_dist = Counter(r["target_v2"] for r in results)
    tono_runner_dist = Counter(r["tono_runner"] for r in results)
    target_runner_dist = Counter(r["target_runner"] for r in results)
    flag_dist = Counter()
    for r in results:
        for k in r["flags"]:
            flag_dist[k] += 1

    snap = MapperStats.snapshot()

    md = []
    md.append("# Smoke mapper v3 sobre triangulación 2026-04-18\n\n")
    md.append("**Fecha ejecución:** 2026-05-09  \n")
    md.append("**Mapper version:** v3.0.0  \n")
    md.append("**Input:** 60 comments triangulados (Claude+Gemini+Gemma)\n\n")

    md.append("## Resumen ejecutivo\n\n")
    md.append(f"- **Comments procesados:** {len(rows)}\n")
    md.append(f"- **Mapeos válidos (sin fallback):** {valid_v2} / {len(rows)} ({valid_v2/len(rows)*100:.0f}%)\n")
    md.append(f"- **Fallbacks:** {fallbacks} ({fallbacks/len(rows)*100:.1f}%)\n")
    md.append(f"- **Tono 3/3 acuerdo modelos:** {tono_3of3_count}/{len(rows)} ({tono_3of3_count/len(rows)*100:.0f}%)\n")
    md.append(f"- **Target 3/3 acuerdo modelos:** {target_3of3_count}/{len(rows)} ({target_3of3_count/len(rows)*100:.0f}%)\n\n")

    md.append("## Distribución tono\n\n")
    md.append("**Runner Gemma (input):**\n\n")
    for t, c in tono_runner_dist.most_common():
        md.append(f"- `{t}`: {c}\n")
    md.append("\n**Mapper v2 (output):**\n\n")
    for t, c in tono_v2_dist.most_common():
        md.append(f"- `{t}`: {c}\n")

    md.append("\n## Distribución target\n\n")
    md.append("**Runner Gemma (input):**\n\n")
    for t, c in target_runner_dist.most_common():
        md.append(f"- `{t}`: {c}\n")
    md.append("\n**Mapper v2 (output):**\n\n")
    for t, c in target_v2_dist.most_common():
        md.append(f"- `{t}`: {c}\n")

    md.append("\n## Flags activados (G1-G5)\n\n")
    if flag_dist:
        for f, c in flag_dist.most_common():
            md.append(f"- `{f}`: {c}\n")
    else:
        md.append("(ninguno)\n")

    md.append("\n## Stats mapper\n\n```\n")
    for k, v in snap.items():
        md.append(f"  {k}: {v}\n")
    md.append("```\n")

    md.append("\n## Sample 15 rows\n\n")
    md.append("| id | tono_runner→tono_v2 | target_runner→target_v2 | 3/3 | flags |\n")
    md.append("|---|---|---|---|---|\n")
    for r in results[:15]:
        flags_str = ",".join(r["flags"].keys())[:30]
        md.append(f"| {r['id']} | {r['tono_runner']}→**{r['tono_v2']}** | {r['target_runner']}→**{r['target_v2']}** | {'✓' if r['tono_3of3'] else '·'} | {flags_str} |\n")

    Path(OUT_MD).write_text("".join(md))
    print(f"\nReporte → {OUT_MD}")
    print("=" * 60)
    print(f"Comments: {len(rows)} · Fallbacks: {fallbacks} · Válidos: {valid_v2}")
    print(f"3/3 tono: {tono_3of3_count}/{len(rows)} · 3/3 target: {target_3of3_count}/{len(rows)}")
    print(f"Stats: {snap}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
