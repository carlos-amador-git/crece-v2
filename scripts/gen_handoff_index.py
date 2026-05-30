#!/usr/bin/env python3
"""gen_handoff_index.py — Regenera el índice de handoffs de CRECE v2.

Resuelve la deuda de tener decenas de HANDOFF-*.md sueltos en .context/ sin punto
de entrada. Adaptado de cfdi-platform (ver docs/adr/0006). A diferencia de cfdi,
los handoffs de CRECE NO tienen frontmatter YAML estructurado → se infiere la fecha
del nombre (HANDOFF-YYYY-MM-DD-*.md) y el título del primer encabezado `#`.
Sin dependencia de PyYAML (corre en el host sin venv).

Uso:
    python scripts/gen_handoff_index.py
    python scripts/gen_handoff_index.py --context-dir .context
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def first_header(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            if s.startswith("#"):
                return s.lstrip("# ").strip()[:80]
    except Exception:
        pass
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--context-dir", type=Path, default=Path(".context"))
    args = ap.parse_args()

    d = args.context_dir
    if not d.exists():
        print(f"ERROR: no existe {d}", file=sys.stderr)
        return 2

    entries = []
    for path in d.glob("HANDOFF*.md"):
        if path.name.upper() in ("HANDOFF-INDEX.MD",):
            continue
        m = DATE_RE.search(path.name)
        entries.append({
            "file": path.name,
            "date": m.group(1) if m else "",
            "title": first_header(path),
        })

    # Orden por fecha descendente (más reciente primero); sin fecha al final.
    entries.sort(key=lambda e: e["date"] or "0000-00-00", reverse=True)

    lines = [
        "# Índice de handoffs — CRECE v2",
        "",
        "> **Generado automáticamente** por `scripts/gen_handoff_index.py`. No editar a mano.",
        f"> {len(entries)} handoffs. Regenerar: `python scripts/gen_handoff_index.py`.",
        "",
        "| # | Fecha | Título | Archivo |",
        "|---|-------|--------|---------|",
    ]
    for i, e in enumerate(entries, 1):
        lines.append(f"| {i} | {e['date']} | {e['title']} | [`{e['file']}`]({e['file']}) |")
    lines.append("")

    out = d / "HANDOFF-INDEX.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"✅ Índice regenerado: {out} ({len(entries)} handoffs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
