"""Mapea divergencias de la triangulación vs reglas de matriz v2 (53 reglas).

Input:
  output/triangulation_matrix.csv (producido por triangulate.py)
  BD crece.matriz_polaridad (o export JSON si la BD no disponible)

Output:
  output/rule_gaps.md

Heurística:
  - Por cada row con agreement != '3/3' en tono o polaridad:
    - Extraer (tono_majority, target_majority, polaridad_majority) si 2/3
    - Si 3-way divergence: marcar como 'alta entropía' — no hay majority
  - Intentar match a regla existente:
    - Reglas v2 están parametrizadas por (tono, target, contexto_politico) → ajuste de intensidad
  - Reportar si:
    - Regla falta (combinación no contemplada)
    - Regla existe pero modelos convergen fuera del rango esperado
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent.parent
MATRIX_CSV = EVAL_DIR / "output" / "triangulation_matrix.csv"
OUT_MD = EVAL_DIR / "output" / "rule_gaps.md"


def majority(vals: list[str]) -> str | None:
    """Returns the majority value or None if 3-way divergence."""
    cnt = Counter(v for v in vals if v)
    if not cnt:
        return None
    top, n = cnt.most_common(1)[0]
    return top if n >= 2 else None


def load_matrix() -> list[dict]:
    if not MATRIX_CSV.exists():
        raise FileNotFoundError(f"No existe {MATRIX_CSV} — corre triangulate.py primero")
    with MATRIX_CSV.open() as f:
        return list(csv.DictReader(f))


def main() -> None:
    rows = load_matrix()
    # Solo rows con 3 modelos completos
    complete = [r for r in rows if r.get("tono_claude") and r.get("tono_gemini") and r.get("tono_gemma")]

    gaps = []
    for r in complete:
        tonos = [r["tono_claude"], r["tono_gemini"], r["tono_gemma"]]
        targets = [r["target_claude"], r["target_gemini"], r["target_gemma"]]
        pols = [r["pol_claude"], r["pol_gemini"], r["pol_gemma"]]
        intensities = [r["intens_claude"], r["intens_gemini"], r["intens_gemma"]]

        tono_ag = r.get("tono_agreement", "")
        pol_ag = r.get("pol_agreement", "")

        if tono_ag == "3/3" and pol_ag == "3/3":
            continue

        tono_maj = majority(tonos)
        target_maj = majority(targets)
        pol_maj = majority(pols)

        gap_type = []
        if tono_ag == "divergence":
            gap_type.append("tono-divergence")
        elif tono_ag == "2/3":
            gap_type.append("tono-split")
        if pol_ag == "divergence":
            gap_type.append("polaridad-divergence")
        elif pol_ag == "2/3":
            gap_type.append("polaridad-split")

        gaps.append({
            "id": r["id"],
            "gap_type": " + ".join(gap_type) if gap_type else "other",
            "tono_maj": tono_maj,
            "target_maj": target_maj,
            "pol_maj": pol_maj,
            "tono_all": "/".join(tonos),
            "target_all": "/".join(targets),
            "pol_all": "/".join(pols),
            "intens_all": "/".join(str(i) for i in intensities),
        })

    lines = [
        "# Rule gaps — Triangulación NLP Layer 2 (2026-04-18)",
        "",
        f"Total rows analizados: {len(complete)}",
        f"Rows con algún disagreement: {len(gaps)}",
        "",
        "Heurística: si los 3 modelos no coinciden en tono AND polaridad, el row entra como gap.",
        "",
        "## Gaps detectados (uno por row)",
        "",
        "| ID | Gap type | Tono maj | Target maj | Pol maj | Tonos 3 modelos (C/G/M) | Pols (C/G/M) | Intens (C/G/M) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for g in gaps:
        lines.append(
            f"| {g['id'][:40]} | {g['gap_type']} | {g['tono_maj'] or '—'} | "
            f"{g['target_maj'] or '—'} | {g['pol_maj'] or '—'} | {g['tono_all']} | "
            f"{g['pol_all']} | {g['intens_all']} |"
        )

    lines.extend([
        "",
        "## Patrones observados",
        "",
        "_(llenar manualmente tras revisar la tabla)_",
        "",
        "- Falsos 0 en elogios cortos con emojis: _cuáles IDs_",
        "- Confusión personal vs informativo: _cuáles IDs_",
        "- Target ambiguo dirigente_post vs gobierno: _cuáles IDs_",
        "- 3-way divergence en sátira / sarcasmo: _cuáles IDs_",
        "",
        "## Relación con matriz v2 (53 reglas)",
        "",
        "Las reglas de matriz v2 se parametrizan por `(tono, target, contexto_politico) → ajuste ±N`.",
        "Rows con 3-way divergence en tono implican que ninguna regla v2 aplica — ni siquiera hay tono consensual.",
        "Rows con tono-split 2/3 indican que la regla existe pero el comentario cae en la frontera — ajuste de granularidad necesario.",
        "",
        "## Siguientes pasos",
        "",
        "- Revisar gaps agrupados por patrón",
        "- Escribir `PROPUESTA-MATRIZ-V3.md` con ajustes concretos",
        "- Cross-audit Gemini de la propuesta",
    ])

    OUT_MD.write_text("\n".join(lines))
    print(f"Output: {OUT_MD}")
    print(f"Rows con gap: {len(gaps)} / {len(complete)}")


if __name__ == "__main__":
    main()
