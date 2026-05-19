"""Triangulación NLP posts 2026-05-09.

Sample 60 posts (20 × 3 dirigentes piloto: Piña, Solano, Ballesteros)
de los últimos 90 días. Clasifica cada uno con Gemma3:12b vía Ollama Coolify (VPS).

REGLA DURA: las llamadas a Gemma SIEMPRE van por endpoint Coolify remoto, NUNCA local.
El Mac corre 6-7 entornos del CEO y no debe consumir RAM por LLM. Override únicamente
vía env vars OLLAMA_BASE_URL y OLLAMA_MODEL (defaults: VPS + gemma3:12b).

Salida: sample.csv, results_gemma.csv, posts_for_claude.md, triangulacion-2026-05-09.md
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import psycopg2
import requests

# ---------- Config ----------
DB_DSN = os.getenv(
    "DATABASE_URL_RAW",
    "host=localhost port=5438 dbname=crece user=crece password=crece_dev",
)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://163.245.208.96:11434").rstrip("/")
OLLAMA_URL = f"{OLLAMA_BASE_URL}/api/generate"
MODEL = os.getenv("OLLAMA_MODEL", "gemma3:12b")
DIRIGENTE_IDS = [1, 2, 8]  # Piña, Solano, Ballesteros
POSTS_PER_DIRIGENTE = 20
MAX_CONTENT_CHARS = 800
TIMEOUT_S = 180
RETRIES = 0
RANDOM_SEED = 42

OUT_DIR = Path(__file__).resolve().parent.parent / "evaluations" / "triangulacion-posts-2026-05-09"
SAMPLE_CSV = OUT_DIR / "sample.csv"
RESULTS_CSV = OUT_DIR / "results_gemma.csv"
POSTS_MD = OUT_DIR / "posts_for_claude.md"
SUMMARY_MD = OUT_DIR / "triangulacion-2026-05-09.md"

VALID_TONOS = {"critico", "propositivo", "celebratorio", "informativo", "solidario", "ataque", "personal"}
VALID_TARGETS = {"gobierno", "oposicion", "ciudadania", "medios", "autopromocion", "tema_especifico", "dirigente"}
VALID_SENTIMENTS = {"positivo", "neutro", "negativo"}

PROMPT_TEMPLATE = (
    "Eres un clasificador NLP político en español mexicano. Analiza el siguiente post "
    "de un dirigente político y devuelve SOLO JSON válido (sin markdown, sin texto adicional):\n"
    '{{"tono": "<uno de: critico, propositivo, celebratorio, informativo, solidario, ataque, personal>", '
    '"target": "<uno de: gobierno, oposicion, ciudadania, medios, autopromocion, tema_especifico, dirigente>", '
    '"sentimiento": "<positivo|neutro|negativo>", '
    '"razon": "<frase corta justificando>"}}\n\n'
    "Post: {content}"
)


# ---------- DB helpers ----------
def _parse_dsn(dsn: str) -> dict:
    """Convierte 'host=... port=... dbname=...' a kwargs psycopg2."""
    if dsn.startswith(("postgresql://", "postgres://")):
        return {"dsn": dsn}
    if dsn.startswith("postgresql+psycopg2://"):
        return {"dsn": dsn.replace("postgresql+psycopg2://", "postgresql://", 1)}
    return {"dsn": dsn}


def fetch_sample() -> list[dict]:
    """Sample estratificado: 20 posts random_state=42 por dirigente."""
    conn = psycopg2.connect(**_parse_dsn(DB_DSN))
    sample: list[dict] = []
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT setseed({1.0 / 42})")  # determinista
            for did in DIRIGENTE_IDS:
                cur.execute(
                    """
                    SELECT sp.id,
                           d.id AS dirigente_id,
                           d.full_name AS dirigente_nombre,
                           spr.platform,
                           sp.content,
                           sp.published_at
                      FROM social_posts sp
                      JOIN social_profiles spr ON spr.id = sp.profile_id
                      JOIN dirigentes d ON d.id = spr.dirigente_id
                     WHERE d.id = %s
                       AND sp.content IS NOT NULL
                       AND length(sp.content) > 30
                       AND sp.published_at > NOW() - INTERVAL '90 days'
                     ORDER BY random()
                     LIMIT %s
                    """,
                    (did, POSTS_PER_DIRIGENTE),
                )
                rows = cur.fetchall()
                for r in rows:
                    sample.append(
                        {
                            "post_id": r[0],
                            "dirigente_id": r[1],
                            "dirigente_nombre": r[2],
                            "plataforma": r[3],
                            "content": (r[4] or "")[:MAX_CONTENT_CHARS],
                            "published_at": r[5].isoformat() if r[5] else "",
                        }
                    )
    finally:
        conn.close()
    return sample


# ---------- Ollama ----------
def classify_with_gemma(content: str) -> tuple[dict, str]:
    """Llama a Ollama y parsea JSON. Devuelve (parsed_dict|{}, raw_text)."""
    prompt = PROMPT_TEMPLATE.format(content=content)
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1, "num_predict": 200},
    }
    last_err = ""
    raw = ""
    for attempt in range(RETRIES + 1):
        try:
            resp = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT_S)
            resp.raise_for_status()
            raw = resp.json().get("response", "")
            break
        except requests.exceptions.RequestException as e:
            last_err = f"HTTP_ERROR (try {attempt + 1}/{RETRIES + 1}): {e}"
            if attempt < RETRIES:
                time.sleep(2)
                continue
            return {}, last_err

    raw_clean = raw.strip()
    # Extraer primer bloque JSON si viene envuelto en markdown
    m = re.search(r"\{.*\}", raw_clean, re.DOTALL)
    if not m:
        return {}, raw_clean
    try:
        parsed = json.loads(m.group(0))
        return parsed, raw_clean
    except json.JSONDecodeError:
        return {}, raw_clean


# ---------- I/O ----------
def write_sample_csv(sample: list[dict]) -> None:
    with SAMPLE_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["post_id", "dirigente_id", "dirigente_nombre", "plataforma", "content", "published_at"],
        )
        w.writeheader()
        w.writerows(sample)


def write_results_csv(results: list[dict]) -> None:
    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "post_id",
                "dirigente_id",
                "tono_gemma",
                "target_gemma",
                "sentimiento_gemma",
                "razon_gemma",
                "raw_response",
            ],
        )
        w.writeheader()
        w.writerows(results)


def write_posts_md(sample: list[dict]) -> None:
    lines = ["# Triangulación posts 2026-05-09 — para clasificación Claude\n"]
    lines.append(f"**Total:** {len(sample)} posts · 3 dirigentes piloto · 90 días\n")
    lines.append(
        "Tono: critico | propositivo | celebratorio | informativo | solidario | ataque | personal\n"
    )
    lines.append(
        "Target: gobierno | oposicion | ciudadania | medios | autopromocion | tema_especifico | dirigente\n"
    )
    lines.append("Sentimiento: positivo | neutro | negativo\n\n---\n")
    for i, p in enumerate(sample, 1):
        fecha = p["published_at"][:10] if p["published_at"] else "—"
        lines.append(
            f"## Post {i} · {p['dirigente_nombre']} · {p['plataforma']} · {fecha} · id={p['post_id']}\n"
        )
        lines.append(f"\n{p['content']}\n\n")
        lines.append("→ Tu clasificación: tono=___ target=___ sentimiento=___\n\n---\n")
    POSTS_MD.write_text("\n".join(lines), encoding="utf-8")


def write_summary_md(sample: list[dict], results: list[dict], elapsed_s: float) -> None:
    ok = sum(1 for r in results if r["tono_gemma"] != "ERROR")
    err = len(results) - ok
    tonos = Counter(r["tono_gemma"] for r in results)
    targets = Counter(r["target_gemma"] for r in results)
    sentimientos = Counter(r["sentimiento_gemma"] for r in results)

    by_id = {p["post_id"]: p for p in sample}

    lines = [
        "# Triangulación NLP posts · 2026-05-09\n",
        "## Resumen ejecutivo\n",
        f"- **Total:** {len(results)} posts procesados",
        f"- **Parseados OK por Gemma:** {ok}",
        f"- **Errores Gemma:** {err}",
        f"- **Modelo:** `{MODEL}`",
        f"- **Tiempo total:** {elapsed_s:.1f}s ({elapsed_s/max(len(results),1):.2f}s/post)",
        f"- **Dirigentes piloto:** {DIRIGENTE_IDS}",
        f"- **Random seed:** {RANDOM_SEED}",
        "",
        "## Distribución tono Gemma",
        "",
        "| tono | n |",
        "|------|---|",
    ]
    for k, v in tonos.most_common():
        lines.append(f"| {k or '—'} | {v} |")
    lines.append("\n## Distribución target Gemma\n")
    lines.append("| target | n |")
    lines.append("|--------|---|")
    for k, v in targets.most_common():
        lines.append(f"| {k or '—'} | {v} |")
    lines.append("\n## Distribución sentimiento Gemma\n")
    lines.append("| sentimiento | n |")
    lines.append("|-------------|---|")
    for k, v in sentimientos.most_common():
        lines.append(f"| {k or '—'} | {v} |")
    lines.append("\n## Preview 10 posts\n")
    lines.append("| id | dirigente | content_preview | tono | target | sentimiento |")
    lines.append("|----|-----------|-----------------|------|--------|-------------|")
    for r in results[:10]:
        p = by_id.get(r["post_id"], {})
        preview = (p.get("content", "")[:80] or "").replace("\n", " ").replace("|", "/")
        nombre = (p.get("dirigente_nombre") or "—").split()[0]
        lines.append(
            f"| {r['post_id']} | {nombre} | {preview} | {r['tono_gemma']} | {r['target_gemma']} | {r['sentimiento_gemma']} |"
        )
    lines.append("\n## Archivos generados\n")
    lines.append(f"- `{SAMPLE_CSV.name}` — sample crudo")
    lines.append(f"- `{RESULTS_CSV.name}` — clasificación Gemma")
    lines.append(f"- `{POSTS_MD.name}` — posts formateados para Claude")
    lines.append(f"- `{SUMMARY_MD.name}` — este reporte")
    lines.append("\n## Notas de validez\n")
    out_of_vocab_tono = sum(
        1 for r in results if r["tono_gemma"] not in VALID_TONOS and r["tono_gemma"] != "ERROR"
    )
    out_of_vocab_target = sum(
        1 for r in results if r["target_gemma"] not in VALID_TARGETS and r["target_gemma"] != "ERROR"
    )
    lines.append(f"- Tonos fuera de vocabulario v2: {out_of_vocab_tono}")
    lines.append(f"- Targets fuera de vocabulario v2: {out_of_vocab_target}")
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


# ---------- Main ----------
def _load_sample_csv() -> list[dict]:
    rows: list[dict] = []
    with SAMPLE_CSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append(
                {
                    "post_id": int(r["post_id"]),
                    "dirigente_id": int(r["dirigente_id"]),
                    "dirigente_nombre": r["dirigente_nombre"],
                    "plataforma": r["plataforma"],
                    "content": r["content"],
                    "published_at": r["published_at"],
                }
            )
    return rows


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[+] Output dir: {OUT_DIR}", file=sys.stderr)
    print(f"[+] Endpoint: {OLLAMA_URL} model={MODEL}", file=sys.stderr)

    if SAMPLE_CSV.exists() and os.getenv("REGEN_SAMPLE") != "1":
        print(f"[+] Reusing existing sample.csv (set REGEN_SAMPLE=1 to refresh)", file=sys.stderr)
        sample = _load_sample_csv()
    else:
        print("[+] Sampling DB...", file=sys.stderr)
        sample = fetch_sample()
        write_sample_csv(sample)
    print(f"[+] Sample size: {len(sample)}", file=sys.stderr)
    if not POSTS_MD.exists() or os.getenv("REGEN_MD") == "1":
        write_posts_md(sample)
        print(f"[+] posts_for_claude.md written", file=sys.stderr)

    if not sample:
        print("[!] Empty sample — abort", file=sys.stderr)
        return 1

    print(f"[+] Classifying with {MODEL} via Ollama...", file=sys.stderr)
    results: list[dict] = []
    t0 = time.time()
    for i, p in enumerate(sample, 1):
        parsed, raw = classify_with_gemma(p["content"])
        if parsed:
            row = {
                "post_id": p["post_id"],
                "dirigente_id": p["dirigente_id"],
                "tono_gemma": str(parsed.get("tono", "")).strip().lower(),
                "target_gemma": str(parsed.get("target", "")).strip().lower(),
                "sentimiento_gemma": str(parsed.get("sentimiento", "")).strip().lower(),
                "razon_gemma": str(parsed.get("razon", "")).strip(),
                "raw_response": "",
            }
        else:
            row = {
                "post_id": p["post_id"],
                "dirigente_id": p["dirigente_id"],
                "tono_gemma": "ERROR",
                "target_gemma": "ERROR",
                "sentimiento_gemma": "ERROR",
                "razon_gemma": "",
                "raw_response": raw[:500],
            }
        results.append(row)
        if i % 10 == 0 or i == len(sample):
            elapsed = time.time() - t0
            rate = elapsed / i
            ok_so_far = sum(1 for r in results if r["tono_gemma"] != "ERROR")
            print(
                f"  Post {i}/{len(sample)} OK={ok_so_far} ERR={i - ok_so_far} elapsed={elapsed:.1f}s avg={rate:.2f}s/post",
                file=sys.stderr,
                flush=True,
            )

    elapsed = time.time() - t0
    write_results_csv(results)
    write_summary_md(sample, results, elapsed)

    ok = sum(1 for r in results if r["tono_gemma"] != "ERROR")
    print(
        f"[+] Done · {ok}/{len(results)} OK · {elapsed:.1f}s",
        file=sys.stderr,
    )
    print(f"[+] {SUMMARY_MD}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
