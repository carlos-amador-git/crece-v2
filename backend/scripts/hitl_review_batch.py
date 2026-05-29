"""S6 · HITL Review Batch · genera reporte de patrones para Claude+Gemini.

Lee `hitl_edits_log` (tabla creada por S1) y produce dos artefactos:
- `/tmp/HITL-REVIEW-PATTERNS-{YYYY-MM-DD}.md` — legible para Linda/CEO
- `/tmp/HITL-REVIEW-PATTERNS-{YYYY-MM-DD}.json` — input estructurado para LLMs

Métricas:
1. Matriz confusión tono (sistema vs humano)
2. Matriz confusión target
3. Top 20 patrones repetidos (from_tono, to_tono, from_target, to_target)
4. Off-topic agrupado por (from_tono, from_target)
5. Tasa de calidad: confirmaciones implícitas / ediciones / off-topic / acuerdo
6. Sugerencias automáticas (mapper rules, blacklist runner, ambigüedad criterio)

CLI:
    python /app/scripts/hitl_review_batch.py [--since YYYY-MM-DD] [--dirigente-id N]

Default `--since`: hoy menos 7 días. Default `--dirigente-id`: todos.

Si la tabla `hitl_edits_log` no existe (S1 aún no corrió), imprime aviso y exit 0.
Si la tabla existe pero está vacía en el rango, genera MD/JSON vacíos consistentes.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

sys.path.insert(0, "/app")

# Heurísticas — umbrales para sugerencias automáticas
SUGG_MAPPER_MIN_COUNT = 5      # patrón ataque→informativo ≥5 con mismo target
SUGG_OFFTOPIC_MIN_RATIO = 0.10  # off-topic ≥10% por combo runner+target
SUGG_AMBIG_RATIO = 0.20         # confusión propositivo↔celebratorio >20%

CAMPOS_NULABLES = ("from_tono", "to_tono", "from_target", "to_target")


def _norm(v: Any) -> str:
    """Normaliza valor para comparación/llaves: None → '∅'."""
    if v is None:
        return "∅"
    return str(v)


async def _table_exists(db, table_name: str) -> bool:
    res = await db.execute(text("""
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = :t
        LIMIT 1
    """), {"t": table_name})
    return res.first() is not None


def _build_confusion(rows, from_field: str, to_field: str) -> dict[str, dict[str, int]]:
    """Matriz de confusión: matrix[from_value][to_value] = count."""
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in rows:
        f = _norm(getattr(r, from_field))
        t = _norm(getattr(r, to_field))
        matrix[f][t] += 1
    return {k: dict(v) for k, v in matrix.items()}


def _confusion_to_md(matrix: dict[str, dict[str, int]], title: str) -> list[str]:
    if not matrix:
        return [f"### {title}\n\n_Sin datos en rango._\n\n"]
    cols = sorted({c for row in matrix.values() for c in row.keys()})
    rows_keys = sorted(matrix.keys())
    md = [f"### {title}\n\n"]
    md.append("Filas = sistema (`from_*`) · Columnas = humano (`to_*`)\n\n")
    md.append("| sistema \\ humano | " + " | ".join(cols) + " | total |\n")
    md.append("|" + "---|" * (len(cols) + 2) + "\n")
    for rk in rows_keys:
        cells = [str(matrix[rk].get(c, 0)) for c in cols]
        total = sum(matrix[rk].values())
        md.append(f"| {rk} | " + " | ".join(cells) + f" | {total} |\n")
    md.append("\n")
    return md


def _heuristic_suggestions(
    rows,
    total: int,
    confusion_tono: dict[str, dict[str, int]],
) -> list[str]:
    """Genera sugerencias basadas en patrones repetidos.

    Reglas implementadas:
    - Mapper G6: from_tono='ataque' → to_tono='informativo' por mismo to_target ≥5
    - Blacklist runner: combo (from_tono, from_target) con off_topic=TRUE ≥10% del total
    - Ambigüedad criterio: confusión propositivo↔celebratorio >20% del eje
    """
    suggestions: list[str] = []
    if total == 0:
        return suggestions

    # 1. Mapper rule G6 — ataque → informativo
    ataque_inf_target: Counter[str] = Counter()
    for r in rows:
        if (
            r.from_tono == "ataque"
            and r.to_tono == "informativo"
            and r.to_target is not None
        ):
            ataque_inf_target[str(r.to_target)] += 1
    for tgt, n in ataque_inf_target.items():
        if n >= SUGG_MAPPER_MIN_COUNT:
            suggestions.append(
                f"Posible regla mapper G6: target=`{tgt}` reduce `ataque`→`informativo` "
                f"({n} ocurrencias). Considerar añadir override en matriz v2."
            )

    # 2. Blacklist runner — off_topic ≥10% por combo runner
    offtopic_combos: Counter[tuple[str, str]] = Counter()
    for r in rows:
        if r.off_topic:
            offtopic_combos[(_norm(r.from_tono), _norm(r.from_target))] += 1
    for (tono, target), n in offtopic_combos.items():
        ratio = n / total
        if ratio >= SUGG_OFFTOPIC_MIN_RATIO:
            suggestions.append(
                f"Considerar blacklist runner: combo tono=`{tono}` + target=`{target}` "
                f"marcado off-topic en {n}/{total} ({ratio*100:.1f}%)."
            )

    # 3. Ambigüedad propositivo ↔ celebratorio
    ambig_keys = ("propositivo", "celebratorio")
    ambig_count = 0
    eje_total = 0
    for f, row in confusion_tono.items():
        for t, n in row.items():
            if f in ambig_keys or t in ambig_keys:
                eje_total += n
                if {f, t} == set(ambig_keys):
                    ambig_count += n
    if eje_total > 0:
        ratio = ambig_count / eje_total
        if ratio > SUGG_AMBIG_RATIO:
            suggestions.append(
                f"Ambigüedad criterio: confusión `propositivo`↔`celebratorio` "
                f"= {ambig_count}/{eje_total} ({ratio*100:.1f}%) del eje. "
                f"Considerar merge o redefinir guía de anotación."
            )

    return suggestions


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Fecha mínima ISO (YYYY-MM-DD). Default: hace 7 días.",
    )
    parser.add_argument(
        "--dirigente-id",
        type=int,
        default=None,
        help="Filtrar por dirigente. Default: todos.",
    )
    args = parser.parse_args()

    if args.since:
        try:
            since = datetime.fromisoformat(args.since).date()
        except ValueError:
            print(f"ERROR: --since debe ser YYYY-MM-DD, recibido: {args.since}")
            return 2
    else:
        since = date.today() - timedelta(days=7)

    today_iso = date.today().isoformat()
    out_md = Path(f"/tmp/HITL-REVIEW-PATTERNS-{today_iso}.md")
    out_json = Path(f"/tmp/HITL-REVIEW-PATTERNS-{today_iso}.json")

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR: DATABASE_URL no definida en environment.")
        return 2

    eng = create_async_engine(dsn, echo=False)
    S = async_sessionmaker(eng, expire_on_commit=False)

    async with S() as db:
        if not await _table_exists(db, "hitl_edits_log"):
            print("Tabla hitl_edits_log no existe. Esperar a que S1 termine.")
            await eng.dispose()
            return 0

        params: dict[str, Any] = {"since": since}
        sql = """
            SELECT id, entity_type, entity_id, dirigente_id,
                   from_tono, to_tono, from_target, to_target,
                   off_topic, actor_id, source, reason, edited_at
            FROM hitl_edits_log
            WHERE edited_at >= :since
        """
        if args.dirigente_id is not None:
            sql += " AND dirigente_id = :did"
            params["did"] = args.dirigente_id
        sql += " ORDER BY edited_at ASC"

        rows = (await db.execute(text(sql), params)).all()
        total = len(rows)

        # Métricas básicas
        confirmaciones_implicitas = sum(
            1
            for r in rows
            if r.from_tono == r.to_tono
            and r.from_target == r.to_target
            and not r.off_topic
        )
        ediciones_con_cambio = sum(
            1
            for r in rows
            if (r.from_tono != r.to_tono) or (r.from_target != r.to_target)
        )
        off_topic_marcadas = sum(1 for r in rows if r.off_topic)
        acuerdo = (confirmaciones_implicitas / total) if total else 0.0

        # Matrices
        confusion_tono = _build_confusion(rows, "from_tono", "to_tono")
        confusion_target = _build_confusion(rows, "from_target", "to_target")

        # Top 20 patrones repetidos
        pattern_counter: Counter[tuple[str, str, str, str]] = Counter()
        for r in rows:
            key = (
                _norm(r.from_tono),
                _norm(r.to_tono),
                _norm(r.from_target),
                _norm(r.to_target),
            )
            pattern_counter[key] += 1
        top_patterns = [
            {
                "from_tono": k[0],
                "to_tono": k[1],
                "from_target": k[2],
                "to_target": k[3],
                "count": n,
            }
            for k, n in pattern_counter.most_common(50)
            if n >= 2
        ][:20]

        # Off-topic combos
        offtopic_groups: Counter[tuple[str, str]] = Counter()
        for r in rows:
            if r.off_topic:
                offtopic_groups[(_norm(r.from_tono), _norm(r.from_target))] += 1
        offtopic_list = [
            {"from_tono": k[0], "from_target": k[1], "count": n}
            for k, n in offtopic_groups.most_common()
        ]

        # Sugerencias
        sugerencias = _heuristic_suggestions(rows, total, confusion_tono)

        # JSON
        payload = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "filters": {
                "since": since.isoformat(),
                "dirigente_id": args.dirigente_id,
            },
            "totals": {
                "audit_rows": total,
                "confirmaciones_implicitas": confirmaciones_implicitas,
                "ediciones_con_cambio": ediciones_con_cambio,
                "off_topic_marcadas": off_topic_marcadas,
                "acuerdo_sistema_humano": round(acuerdo, 4),
            },
            "confusion_tono": confusion_tono,
            "confusion_target": confusion_target,
            "top_patterns": top_patterns,
            "off_topic_groups": offtopic_list,
            "suggestions": sugerencias,
        }
        out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

        # Markdown
        md: list[str] = []
        md.append("# HITL Review · Patrones de edición humana sobre NLP\n\n")
        md.append(f"**Generado:** {datetime.utcnow().isoformat()}Z  \n")
        md.append(f"**Rango:** desde `{since.isoformat()}` (UTC)  \n")
        if args.dirigente_id is not None:
            md.append(f"**Filtro dirigente_id:** `{args.dirigente_id}`  \n")
        md.append(f"**Total audit rows:** {total}\n\n")

        if total == 0:
            md.append("> 0 audit rows en rango — nada que reportar.\n\n")
            md.append("Si la tabla recién se creó, esperar a que los actores ")
            md.append("(Solano/Piña/Ballesteros) realicen sus primeras ediciones ")
            md.append("via `/dashboard/settings/evaluacion-nlp`.\n")
            out_md.write_text("".join(md))
            print(f"Reporte (vacío) → {out_md}")
            print(f"JSON     (vacío) → {out_json}")
            await eng.dispose()
            return 0

        md.append("## Resumen ejecutivo\n\n")
        md.append(f"- **Confirmaciones implícitas (sistema = humano):** "
                  f"{confirmaciones_implicitas} ({confirmaciones_implicitas/total*100:.1f}%)\n")
        md.append(f"- **Ediciones con cambio:** {ediciones_con_cambio} "
                  f"({ediciones_con_cambio/total*100:.1f}%)\n")
        md.append(f"- **Off-topic marcadas:** {off_topic_marcadas} "
                  f"({off_topic_marcadas/total*100:.1f}%)\n")
        md.append(f"- **Acuerdo sistema↔humano:** {acuerdo*100:.1f}%\n\n")

        md.append("## Matrices de confusión\n\n")
        md.extend(_confusion_to_md(confusion_tono, "Tono"))
        md.extend(_confusion_to_md(confusion_target, "Target"))

        md.append("## Top 20 patrones repetidos (count ≥ 2)\n\n")
        if top_patterns:
            md.append("| from_tono | to_tono | from_target | to_target | count |\n")
            md.append("|---|---|---|---|---:|\n")
            for p in top_patterns:
                md.append(
                    f"| {p['from_tono']} | {p['to_tono']} | "
                    f"{p['from_target']} | {p['to_target']} | {p['count']} |\n"
                )
            md.append("\n")
        else:
            md.append("_Ningún patrón con ≥2 ocurrencias._\n\n")

        md.append("## Off-topic agrupado por (from_tono, from_target)\n\n")
        if offtopic_list:
            md.append("| from_tono | from_target | count | % del total |\n")
            md.append("|---|---|---:|---:|\n")
            for g in offtopic_list:
                ratio = g["count"] / total * 100
                md.append(
                    f"| {g['from_tono']} | {g['from_target']} | "
                    f"{g['count']} | {ratio:.1f}% |\n"
                )
            md.append("\n")
        else:
            md.append("_Sin off-topic en el rango._\n\n")

        md.append("## Sugerencias automáticas\n\n")
        if sugerencias:
            for s in sugerencias:
                md.append(f"- {s}\n")
            md.append("\n")
        else:
            md.append("_Sin sugerencias activadas (umbrales no alcanzados)._\n\n")

        md.append("## Cómo usar este reporte\n\n")
        md.append(
            "1. **Linda/CEO** revisan el MD para validar patrones.\n"
            "2. El JSON se pega en sesión IDE con Claude+Gemini para destilar:\n"
            "   - Reglas mapper v3 candidatas\n"
            "   - Ajustes a runner Gemma (blacklist, prompt)\n"
            "   - Cambios a guía de anotación humana\n"
            "3. Las propuestas se aterrizan via `/dashboard/admin/framework` "
            "y se versionan en `framework_matrix_defaults`.\n"
        )

        out_md.write_text("".join(md))
        print(f"Reporte → {out_md}")
        print(f"JSON    → {out_json}")
        print("=" * 60)
        print(
            f"Total: {total} | Confirmaciones: {confirmaciones_implicitas} | "
            f"Ediciones: {ediciones_con_cambio} | Off-topic: {off_topic_marcadas} | "
            f"Acuerdo: {acuerdo*100:.1f}%"
        )

    await eng.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
