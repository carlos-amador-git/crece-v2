"""Triangulacion NLP posts · Gemini CLI clasificador.

Lee sample.csv (60 posts), clasifica cada uno con Gemini CLI en modo headless,
y emite results_gemini.csv + reporte markdown.

Vocabulario v2:
  Tono   : critico | propositivo | celebratorio | informativo | solidario | ataque | personal
  Target : gobierno | oposicion | ciudadania | medios | autopromocion | tema_especifico | dirigente

Ejecucion:
    python3 backend/scripts/triangulacion_posts_gemini_2026_05_09.py
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

GEMINI_BIN = "/opt/homebrew/bin/gemini"
BASE_DIR = Path(__file__).resolve().parents[1] / "evaluations" / "triangulacion-posts-2026-05-09"
SAMPLE_CSV = BASE_DIR / "sample.csv"
RESULTS_CSV = BASE_DIR / "results_gemini.csv"
REPORT_MD = BASE_DIR / "triangulacion-gemini-2026-05-09.md"

TONOS = {"critico", "propositivo", "celebratorio", "informativo", "solidario", "ataque", "personal"}
TARGETS = {"gobierno", "oposicion", "ciudadania", "medios", "autopromocion", "tema_especifico", "dirigente"}
SENTIMIENTOS = {"positivo", "neutro", "negativo"}

PROMPT_TEMPLATE = (
    "Eres un clasificador NLP politico en espanol mexicano. Analiza el siguiente "
    "post de un dirigente politico y devuelve SOLO JSON valido (sin markdown, sin "
    "texto adicional, sin explicaciones extra):\n"
    '{{"tono":"<uno de: critico, propositivo, celebratorio, informativo, solidario, ataque, personal>",'
    '"target":"<uno de: gobierno, oposicion, ciudadania, medios, autopromocion, tema_especifico, dirigente>",'
    '"sentimiento":"<positivo|neutro|negativo>",'
    '"razon":"<frase corta justificando>"}}\n\n'
    "Post: {content}"
)

JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
NOISE_PREFIXES = (
    "YOLO mode",
    "Ripgrep is not available",
    "[STARTUP]",
    "Loaded cached credentials",
    "Data collection",
)


def clean_stdout(raw: str) -> str:
    """Elimina lineas de telemetria/logs del stdout antes de parsear."""
    lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(stripped.startswith(prefix) for prefix in NOISE_PREFIXES):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def parse_response(raw: str) -> tuple[dict | None, str]:
    """Intenta extraer un dict valido del stdout de gemini.

    Devuelve (parsed_dict_or_None, cleaned_raw).
    """
    cleaned = clean_stdout(raw)

    # 1. Intento directo
    candidates: list[str] = []
    block = JSON_BLOCK_RE.search(cleaned)
    if block:
        candidates.append(block.group(1))
    candidates.append(cleaned)
    obj = JSON_OBJECT_RE.search(cleaned)
    if obj:
        candidates.append(obj.group(0))

    for cand in candidates:
        try:
            data = json.loads(cand)
            if isinstance(data, dict):
                return data, cleaned
        except json.JSONDecodeError:
            continue
    return None, cleaned


def normalize_field(value: str | None, allowed: set[str]) -> str:
    if not value:
        return "ERROR"
    v = value.strip().lower()
    return v if v in allowed else "ERROR"


def classify_post(content: str, *, timeout: int = 120) -> tuple[dict, str, float]:
    """Llama a gemini -p y devuelve (resultado_normalizado, raw_clean, elapsed_s)."""
    prompt = PROMPT_TEMPLATE.format(content=content)
    start = time.monotonic()
    try:
        proc = subprocess.run(
            [GEMINI_BIN, "-p", prompt, "--approval-mode", "yolo"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        raw_combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        return (
            {"tono": "ERROR", "target": "ERROR", "sentimiento": "ERROR", "razon": "timeout"},
            "TIMEOUT",
            elapsed,
        )

    elapsed = time.monotonic() - start
    parsed, cleaned = parse_response(raw_combined)
    if parsed is None:
        return (
            {"tono": "ERROR", "target": "ERROR", "sentimiento": "ERROR", "razon": "parse_error"},
            cleaned,
            elapsed,
        )

    return (
        {
            "tono": normalize_field(parsed.get("tono"), TONOS),
            "target": normalize_field(parsed.get("target"), TARGETS),
            "sentimiento": normalize_field(parsed.get("sentimiento"), SENTIMIENTOS),
            "razon": str(parsed.get("razon", ""))[:300],
        },
        cleaned,
        elapsed,
    )


def main() -> int:
    if not SAMPLE_CSV.exists():
        print(f"ERROR: sample no encontrado: {SAMPLE_CSV}", file=sys.stderr)
        return 1

    with SAMPLE_CSV.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    total = len(rows)
    print(f"[gemini] Posts a clasificar: {total}")
    print(f"[gemini] Inicio: {datetime.now(timezone.utc).isoformat()}")

    results: list[dict] = []
    ok = 0
    errores = 0
    t_start = time.monotonic()

    fieldnames = [
        "post_id",
        "dirigente_id",
        "dirigente_nombre",
        "tono_gemini",
        "target_gemini",
        "sentimiento_gemini",
        "razon_gemini",
        "raw_response",
        "elapsed_s",
    ]

    # Escribir incremental para no perder progreso si falla a mitad
    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()

        for idx, row in enumerate(rows, start=1):
            content = (row.get("content") or "").strip()
            if not content:
                clf = {"tono": "ERROR", "target": "ERROR", "sentimiento": "ERROR", "razon": "empty"}
                raw_clean = "EMPTY_CONTENT"
                elapsed = 0.0
            else:
                clf, raw_clean, elapsed = classify_post(content)

            record = {
                "post_id": row.get("post_id"),
                "dirigente_id": row.get("dirigente_id"),
                "dirigente_nombre": row.get("dirigente_nombre"),
                "tono_gemini": clf["tono"],
                "target_gemini": clf["target"],
                "sentimiento_gemini": clf["sentimiento"],
                "razon_gemini": clf["razon"],
                "raw_response": raw_clean[:2000],
                "elapsed_s": f"{elapsed:.2f}",
            }
            writer.writerow(record)
            out.flush()
            results.append(record)

            is_err = clf["tono"] == "ERROR" or clf["target"] == "ERROR"
            if is_err:
                errores += 1
            else:
                ok += 1

            if idx % 5 == 0 or idx == total:
                print(
                    f"  Post {idx}/{total} {'ERR' if is_err else 'OK '} "
                    f"· tono={clf['tono']} target={clf['target']} ({elapsed:.1f}s)"
                )

            # rate-limit cortesia
            time.sleep(1)

    t_total = time.monotonic() - t_start
    avg = t_total / total if total else 0

    # Reporte markdown
    tono_counter = Counter(r["tono_gemini"] for r in results)
    target_counter = Counter(r["target_gemini"] for r in results)
    sent_counter = Counter(r["sentimiento_gemini"] for r in results)

    preview_rows = results[:15]

    lines: list[str] = []
    lines.append("# Triangulacion NLP Posts · Gemini CLI")
    lines.append("")
    lines.append(f"- Fecha: {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Modelo: Gemini CLI default (gemini -p)")
    lines.append(f"- Sample: `{SAMPLE_CSV.relative_to(BASE_DIR.parent.parent)}`")
    lines.append(f"- Resultados: `{RESULTS_CSV.relative_to(BASE_DIR.parent.parent)}`")
    lines.append("")
    lines.append("## Resumen")
    lines.append("")
    lines.append(f"- Total posts: **{total}**")
    lines.append(f"- OK: **{ok}**")
    lines.append(f"- Errores: **{errores}**")
    lines.append(f"- Tiempo total: **{t_total:.1f}s** ({t_total/60:.1f} min)")
    lines.append(f"- Promedio por post: **{avg:.2f}s**")
    lines.append("")
    lines.append("## Distribucion de tono (Gemini)")
    lines.append("")
    lines.append("| tono | count |")
    lines.append("|---|---|")
    for tono, cnt in tono_counter.most_common():
        lines.append(f"| {tono} | {cnt} |")
    lines.append("")
    lines.append("## Distribucion de target (Gemini)")
    lines.append("")
    lines.append("| target | count |")
    lines.append("|---|---|")
    for tgt, cnt in target_counter.most_common():
        lines.append(f"| {tgt} | {cnt} |")
    lines.append("")
    lines.append("## Distribucion de sentimiento (Gemini)")
    lines.append("")
    lines.append("| sentimiento | count |")
    lines.append("|---|---|")
    for s, cnt in sent_counter.most_common():
        lines.append(f"| {s} | {cnt} |")
    lines.append("")
    lines.append("## Preview (15 primeros)")
    lines.append("")
    lines.append("| post_id | dirigente | tono | target | sentimiento | razon |")
    lines.append("|---|---|---|---|---|---|")
    for r in preview_rows:
        razon = (r["razon_gemini"] or "").replace("|", "/").replace("\n", " ")[:80]
        lines.append(
            f"| {r['post_id']} | {r['dirigente_nombre']} | {r['tono_gemini']} | "
            f"{r['target_gemini']} | {r['sentimiento_gemini']} | {razon} |"
        )
    lines.append("")

    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")

    print()
    print(f"[gemini] Total: {t_total:.1f}s · avg {avg:.2f}s/post")
    print(f"[gemini] OK: {ok} · Errores: {errores}")
    print(f"[gemini] CSV    -> {RESULTS_CSV}")
    print(f"[gemini] Report -> {REPORT_MD}")

    return 0 if errores == 0 else 0  # no fallamos por errores parciales


if __name__ == "__main__":
    sys.exit(main())
