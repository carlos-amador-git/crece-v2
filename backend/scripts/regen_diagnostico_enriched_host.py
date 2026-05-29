"""regen_diagnostico_enriched_host.py · 2026-05-21

Versión host-side del enriched: usa CC subprocess local + replica
_gather_context vía HTTP + SQL (sin import de app.*).

Salida:
- planes_ia.contenido = markdown rico 10 secciones (FODA 8-10 ítems/cuadrante)
- planes_ia.estructura_json = JSON parseado del bloque ```json_diagnostico```
  · permite que el tab Concepto 3 lea hero IPD + insight bala + FODA + acciones.

Uso:
    python3 backend/scripts/regen_diagnostico_enriched_host.py \\
        --dirigente-id 3 --dirigente-email pineda@crece.mx
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import psycopg2 as psycopg
import requests

CLAUDE_BIN = "/Users/marxchavez/.local/bin/claude"
GEMINI_BIN = "/Users/marxchavez/.claude/bin/gemini-clean"
CC_EFFORT = os.environ.get("CC_EFFORT", "high")
TIMEOUT_S = int(os.environ.get("CC_TIMEOUT", "1500"))
MODEL_VERSION = "cc-diagnostico-enriched-2026-05-21"

DB_URL = os.environ.get("DATABASE_URL_SYNC", "postgresql://crece:crece_dev@localhost:5438/crece")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8002")


ENRICHED_PROMPT_HEADER = """Genera un DIAGNOSTICO COMPLETO de la presencia digital del dirigente.

## TONO Y ESTILO OBLIGATORIO:
Escribe como un consultor senior presentando ante el cliente. Usa lenguaje
evaluativo y directo, no descriptivo. Cada dato debe ir acompañado de su
JUICIO: ¿es bueno, malo, crítico, excepcional? ¿Qué significa para el
dirigente?
Usa metáforas y frases memorables. El diagnóstico debe ser MEMORABLE.

IMPORTANTE: este diagnóstico es sobre {nombre}. Puedes citar competidores
que aparezcan en el contexto provisto (top_competitors) si la data lo
justifica. PROHIBIDO mencionar dirigentes que NO estén en top_competitors
del contexto · ESPECIALMENTE prohibido cualquier nombre que pertenezca a
clientes nuestros (cross-contamination entre clientes). Si dudas, omite.

## ESTRUCTURA OBLIGATORIA (10 secciones):

### 1. Resumen Ejecutivo
3-4 oraciones que cuenten la HISTORIA del hallazgo principal. Incluye el
IPD score (Índice de Penetración Digital, escala 0-10). Menciona la brecha
principal vs competidor con ratio exacto. Cierra con la oportunidad más
importante.

### 2. Análisis por Plataforma
Para CADA plataforma con datos:
- Tabla: seguidores, posts/30d, engagement, sentimiento
- Benchmark de referencia (políticos mexicanos de cargo similar)
- Calificación: CRITICO / BAJO / ACEPTABLE / BUENO / EXCEPCIONAL
- 1 párrafo narrativo que INTERPRETE los números

### 3. Plataformas Ausentes
Cuáles faltan y por qué son críticas en el contexto del territorio.

### 4. Análisis de Sentimiento
Interpreta la distribución. Si la muestra es pequeña, advierte sobre sesgo.

### 5. Análisis FODA (CRITICAL — esta sección debe ser EXTENSA)

**REGLAS DE EXTENSIÓN OBLIGATORIAS:**
- MÍNIMO 8 ítems por cuadrante. NO ACEPTABLE menos de 6.
- CADA ítem debe tener: (a) hallazgo concreto + (b) evidencia numérica o
  cualitativa específica + (c) implicación política o táctica para el
  dirigente.
- PROHIBIDO: ítems genéricos como 'mejorar redes' o 'aumentar presencia'.

**Formato de salida en MARKDOWN (DOS tablas separadas):**

| **Fortalezas**                                         | **Debilidades**                                       |
| :----------------------------------------------------- | :---------------------------------------------------- |
| <Fortaleza 1 con dato numérico>. **Implicación:** ...  | <Debilidad 1 con dato>. **Riesgo:** ...               |
| <Fortaleza 2>... (8-10 filas)                          | <Debilidad 2>... (8-10 filas)                         |

| **Oportunidades**                                      | **Amenazas**                                          |
| :----------------------------------------------------- | :---------------------------------------------------- |
| <Oportunidad 1 con benchmark>. **Táctica:** ...        | <Amenaza 1 con escenario>. **Mitigación:** ...        |
| ... (8-10 filas)                                       | ... (8-10 filas)                                      |

### 6. Tabla Comparativa vs Competidores
Tabla lado a lado con todos los números. Calcula ratios.

### 7. Tabla de KPIs
Formato: métrica | valor actual | meta 30d | meta 90d | herramienta.

### 8. Recomendaciones (3 fases)
- INMEDIATAS (semana 1-2)
- CORTO PLAZO (mes 1-2)
- MEDIANO PLAZO (mes 2-3)
Cada recomendación: frecuencia, formato, responsable. Conecta con dato real.

### 9. Plataforma Prioritaria (ROI)
CUÁL plataforma tiene mejor retorno y por qué. Justifica con datos del
propio dirigente.

### 10. Datos Faltantes
Lista de datos que se necesitan para profundizar.

---

## BLOQUE EXTRA · JSON ESTRUCTURADO (OBLIGATORIO AL FINAL)

Después de las 10 secciones markdown, agrega este bloque exacto:

```json_diagnostico
{{
  "ipd_score": <number>,
  "ipd_bucket": "BAJO|MEDIO|ALTO",
  "insight_bala": "<1-2 frases · MAX 240 chars · síntesis del hallazgo principal>",
  "fortalezas": [
    {{"titulo": "<corto>", "evidencia": "<dato>", "implicacion": "<qué significa>"}}
  ],
  "oportunidades": [
    {{"titulo": "<corto>", "evidencia": "<benchmark>", "tactica": "<acción>"}}
  ],
  "debilidades": [
    {{"titulo": "<corto>", "evidencia": "<dato>", "riesgo": "<qué puede pasar>"}}
  ],
  "amenazas": [
    {{"titulo": "<corto>", "evidencia": "<contexto>", "mitigacion": "<cómo blindar>"}}
  ],
  "acciones_top3": [
    {{"orden": 1, "texto": "<acción 14-30d>", "cta_label": "<botón>", "cta_href": "/dashboard/..."}}
  ],
  "plataforma_prioritaria": "<FACEBOOK|INSTAGRAM|TIKTOK|YOUTUBE|TWITTER>"
}}
```

REGLAS JSON:
- Mismos ítems FODA del markdown (8-10 por cuadrante mínimo).
- Acciones: EXACTAMENTE 3.
- CTAs reales CRECE: /dashboard/hub, /dashboard/aceptacion/fans-y-perfiles, /dashboard/diagnostico, /dashboard/social/clima, /dashboard/sistema/onboarding.

## CONTEXTO REAL DEL DIRIGENTE (USAR SOLO ESTOS DATOS):

```json
{ctx_json}
```
"""


def fetch_context(dirigente_id: int, dirigente_email: str) -> dict:
    """Replica _gather_context vía HTTP + SQL."""
    # Login
    r = requests.post(
        f"{BACKEND_URL}/api/v1/auth/login",
        data={"username": dirigente_email, "password": "demo2026!"},
        timeout=10,
    )
    r.raise_for_status()
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Dirigente meta + IPD del overview
    ov = requests.get(f"{BACKEND_URL}/api/v1/aceptacion/overview", headers=headers, timeout=10).json()
    diri = next((d for d in ov.get("dirigentes", []) if d.get("dirigente_id") == dirigente_id), {})

    # B01-B18 reales
    t1 = requests.get(f"{BACKEND_URL}/api/v1/diagnostico/{dirigente_id}", headers=headers, timeout=30).json()
    t2 = requests.get(f"{BACKEND_URL}/api/v1/diagnostico_tier2/{dirigente_id}", headers=headers, timeout=30).json()

    ipd_score = (t1.get("ipd") or {}).get("score") or diri.get("ipd_score") or 6.0
    bucket = "CRITICO" if ipd_score < 3 else "BAJO" if ipd_score < 5 else "MEDIO" if ipd_score < 7 else "BUENO" if ipd_score < 9 else "EXCELENTE"

    # Social profiles + posts agregados por plataforma + sentiment 30d
    conn = psycopg.connect(DB_URL)
    with conn.cursor() as cur:
        cur.execute("SELECT full_name, cargo, partido, estado, municipio FROM dirigentes WHERE id = %s", (dirigente_id,))
        meta = cur.fetchone() or ("Dirigente", "n/a", "n/a", "", "")

        # Profiles por plataforma con métricas 30d
        cur.execute("""
            SELECT sps.platform, sps.handle, sps.followers_count,
                   COUNT(sp.id) AS posts_30d,
                   AVG(sp.likes + sp.comments * 3 + sp.shares * 5)::int AS avg_eng,
                   SUM(sp.likes) AS likes_30d,
                   SUM(sp.comments) AS comments_30d
            FROM social_profiles sps
            LEFT JOIN social_posts sp ON sp.profile_id=sps.id
              AND sp.published_at >= NOW() - INTERVAL '30 days'
            WHERE sps.dirigente_id = %s
            GROUP BY sps.platform, sps.handle, sps.followers_count
            ORDER BY sps.followers_count DESC NULLS LAST
        """, (dirigente_id,))
        profiles_data = [
            {
                "platform": r[0], "handle": r[1], "followers": r[2] or 0,
                "posts_30d": r[3] or 0,
                "avg_engagement_per_post": r[4] or 0,
                "likes_30d": r[5] or 0,
                "comments_30d": r[6] or 0,
            }
            for r in cur.fetchall()
        ]

        # Sentiment NLP 30d
        cur.execute("""
            SELECT sc.nlp_tono, COUNT(*) AS n
            FROM social_comments sc
            JOIN social_posts sp ON sp.id = sc.parent_post_id
            JOIN social_profiles sps ON sps.id = sp.profile_id
            WHERE sps.dirigente_id = %s
              AND sc.created_at >= NOW() - INTERVAL '30 days'
              AND sc.nlp_tono IS NOT NULL
            GROUP BY sc.nlp_tono
        """, (dirigente_id,))
        sentiment_dist = {r[0]: r[1] for r in cur.fetchall()}
    conn.close()

    # Top competitors del overview (otros dirigentes del rol opuesto)
    rol_actual = diri.get("rol_politico")
    competitors = [
        {
            "nombre": d["full_name"],
            "rol": d.get("rol_politico"),
            "ipd": d.get("ipd_score"),
            "audiencia": d.get("total_followers"),
        }
        for d in ov.get("dirigentes", [])
        if d.get("dirigente_id") != dirigente_id
    ][:5]

    return {
        "dirigente": {
            "nombre": meta[0], "cargo": meta[1], "partido": meta[2],
            "estado": meta[3], "municipio": meta[4], "rol": rol_actual or "n/a",
        },
        "ipd": {
            "score": round(ipd_score, 2),
            "bucket": bucket,
            "scale": "0-10 (10 = presencia digital óptima)",
        },
        "social_profiles": profiles_data,
        "sentiment_30d": sentiment_dist,
        "top_competitors": competitors,
        "tier1_b01_b10": t1.get("bloques", {}),
        "tier2_b11_b18": t2.get("bloques", {}),
        "analysis_date": datetime.now(UTC).isoformat(),
    }


def call_llm(prompt: str) -> str | None:
    if Path(CLAUDE_BIN).exists():
        print(f"[+] CC subprocess (effort={CC_EFFORT}, timeout={TIMEOUT_S}s)...", file=sys.stderr)
        try:
            r = subprocess.run(
                [CLAUDE_BIN, "--print", "--effort", CC_EFFORT, prompt],
                capture_output=True, text=True, timeout=TIMEOUT_S,
                stdin=subprocess.DEVNULL,
            )
            if r.returncode == 0 and r.stdout:
                return r.stdout
            print(f"  CC stderr: {r.stderr[:200]}", file=sys.stderr)
        except subprocess.TimeoutExpired:
            print("[warn] CC timeout", file=sys.stderr)
    if Path(GEMINI_BIN).exists():
        print("[+] Fallback gemini...", file=sys.stderr)
        try:
            r = subprocess.run(
                [GEMINI_BIN, "--mode", "plan", "--prompt", prompt],
                capture_output=True, text=True, timeout=900,
                stdin=subprocess.DEVNULL,
            )
            if r.returncode == 0 and r.stdout:
                return r.stdout
        except subprocess.TimeoutExpired:
            pass
    return None


def parse_structured_json(content: str) -> dict | None:
    m = re.search(r"```json_diagnostico\s*\n(.*?)\n```", content, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        # Try greedy match
        depth = 0
        start = None
        text = m.group(1)
        for i, ch in enumerate(text):
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        pass
        return None


def insert_plan(conn, dirigente_id: int, contenido: str, estructura: dict | None, ctx: dict) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO planes_ia (
                dirigente_id, tipo, contenido, modelo_ia, prompt_usado,
                datos_entrada, generado_por_id, aprobado, created_at, estructura_json
            )
            VALUES (%s, 'DIAGNOSTICO', %s, %s, %s, %s, 1, false, NOW(), %s)
            RETURNING id
            """,
            (
                dirigente_id, contenido, MODEL_VERSION, "enriched-host-v1",
                json.dumps({"ctx_meta": ctx.get("dirigente"), "ipd": ctx.get("ipd"), "ts": datetime.now(UTC).isoformat()}, default=str),
                json.dumps(estructura, ensure_ascii=False) if estructura else None,
            ),
        )
        new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dirigente-id", type=int, required=True)
    p.add_argument("--dirigente-email", required=True)
    args = p.parse_args()

    print(f"[1/4] Fetch context dirigente_id={args.dirigente_id}…", file=sys.stderr)
    ctx = fetch_context(args.dirigente_id, args.dirigente_email)
    print(f"  Dirigente: {ctx['dirigente']['nombre']} · IPD {ctx['ipd']['score']} · profiles={len(ctx['social_profiles'])}", file=sys.stderr)

    ctx_json = json.dumps(ctx, indent=2, ensure_ascii=False, default=str)
    prompt = ENRICHED_PROMPT_HEADER.format(nombre=ctx["dirigente"]["nombre"], ctx_json=ctx_json)
    print(f"[2/4] Prompt {len(prompt)} chars", file=sys.stderr)

    content = call_llm(prompt)
    if not content:
        print("ERROR: ambos LLMs fallaron", file=sys.stderr)
        return 1
    print(f"[3/4] Output: {len(content)} chars", file=sys.stderr)

    estructura = parse_structured_json(content)
    if not estructura:
        print("[warn] No JSON estructurado parseado (solo markdown)", file=sys.stderr)
    else:
        print(f"  JSON keys: {list(estructura.keys())}", file=sys.stderr)

    conn = psycopg.connect(DB_URL)
    plan_id = insert_plan(conn, args.dirigente_id, content, estructura, ctx)
    conn.close()
    print(f"[4/4] DONE · plan_id={plan_id}", file=sys.stderr)
    if estructura:
        print(f"\nInsight Bala: {estructura.get('insight_bala', '?')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
