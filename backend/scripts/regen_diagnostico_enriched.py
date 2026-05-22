"""Regenera DIAGNOSTICO con prompt enriquecido (FODA 8-10 items/cuadrante con evidencia).

Uso:
  docker exec -e DATABASE_URL=... -e CLAUDE_API_KEY=... crece-backend \\
    python /app/scripts/regen_diagnostico_enriched.py --dirigente 8 [--apply]

--apply persiste el resultado a planes_ia (nuevo registro DIAGNOSTICO).
Sin --apply solo imprime el output a stdout para review.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import os

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set", file=sys.stderr)
    sys.exit(1)

# Reuse plan_generator helpers
sys.path.insert(0, "/app")
from app.core.config import settings  # noqa: E402
from app.models.dirigente import Dirigente  # noqa: E402
from app.models.plan_ia import PlanIA, TipoPlan  # noqa: E402
from app.services.plan_generator import _gather_context  # noqa: E402


ENRICHED_PROMPT_HEADER = """Genera un DIAGNOSTICO COMPLETO de la presencia digital del dirigente.

## TONO Y ESTILO OBLIGATORIO:
Escribe como un consultor senior presentando ante el cliente. Usa lenguaje
evaluativo y directo, no descriptivo. Cada dato debe ir acompanado de su
JUICIO: ¿es bueno, malo, critico, excepcional? ¿Que significa para el
dirigente?
Usa metaforas y frases memorables. El diagnostico debe ser MEMORABLE.

## ESTRUCTURA OBLIGATORIA (10 secciones):

### 1. Resumen Ejecutivo
3-4 oraciones que cuenten la HISTORIA del hallazgo principal. Incluye el
IPD score (Indice de Penetracion Digital, escala 0-10). Menciona la brecha
principal vs competidor con ratio exacto. Cierra con la oportunidad mas
importante.

### 2. Analisis por Plataforma
Para CADA plataforma con datos:
- Tabla: seguidores, posts/30d, engagement, sentimiento
- Benchmark de referencia (politicos mexicanos de cargo similar)
- Calificacion: CRITICO / BAJO / ACEPTABLE / BUENO / EXCEPCIONAL
- 1 parrafo narrativo que INTERPRETE los numeros

### 3. Plataformas Ausentes
Cuales faltan y por que son criticas en el contexto del territorio.

### 4. Analisis de Sentimiento
Interpreta la distribucion. Si la muestra es pequena, advierte sobre sesgo.

### 5. Analisis FODA (CRITICAL — esta seccion debe ser EXTENSA)

**REGLAS DE EXTENSION OBLIGATORIAS:**
- MINIMO 8 items por cuadrante. NO ACEPTABLE menos de 6.
- CADA item debe tener: (a) hallazgo concreto + (b) evidencia numerica o
  cualitativa especifica + (c) implicacion politica o tactica para el
  dirigente.
- PROHIBIDO: items genericos como 'mejorar redes' o 'aumentar presencia'.

**Formato de salida en MARKDOWN (DOS tablas separadas):**

| **Fortalezas**                                         | **Debilidades**                                       |
| :----------------------------------------------------- | :---------------------------------------------------- |
| <Fortaleza 1 con dato numerico>. **Implicacion:** ...  | <Debilidad 1 con dato>. **Riesgo:** ...               |
| <Fortaleza 2>... (8-10 filas)                          | <Debilidad 2>... (8-10 filas)                         |

| **Oportunidades**                                      | **Amenazas**                                          |
| :----------------------------------------------------- | :---------------------------------------------------- |
| <Oportunidad 1 con benchmark concreto>. **Tactica:** ...| <Amenaza 1 con escenario>. **Mitigacion:** ...       |
| ... (8-10 filas)                                       | ... (8-10 filas)                                      |

EJEMPLOS de items aceptables (NO COPIES, SON EJEMPLOS DE GRANULARIDAD):

Fortaleza ejemplo: "Engagement promedio en TikTok de 4.47% (2.5x sobre
benchmark politico mexicano de 1.8%). **Implicacion:** TikTok es el unico
canal donde existe comunidad activa — debe ser el vehiculo principal de
narrativa de campana."

Debilidad ejemplo: "Cero publicaciones en Twitter en los ultimos 30 dias
con 55,640 seguidores acumulados. **Riesgo:** seguidores percibiran
abandono y migraran a competidores activos como Batres (52K+ seguidores
con 12 posts/dia)."

### 6. Tabla Comparativa vs Competidores
Tabla lado a lado con todos los numeros. Calcula ratios.

### 7. Tabla de KPIs
Formato: metrica | valor actual | meta 30d | meta 90d | herramienta.

### 8. Recomendaciones (3 fases)
- INMEDIATAS (semana 1-2)
- CORTO PLAZO (mes 1-2)
- MEDIANO PLAZO (mes 2-3)
Cada recomendacion: frecuencia, formato, responsable. Conecta con dato real.

### 9. Plataforma Prioritaria (ROI)
CUAL plataforma tiene mejor retorno y por que. Justifica con datos del
propio dirigente.

### 10. Datos Faltantes
Lista de datos que se necesitan para profundizar.

---

## BLOQUE EXTRA · JSON ESTRUCTURADO (OBLIGATORIO AL FINAL)

Después de las 10 secciones markdown, agrega este bloque exacto:

```json_diagnostico
{
  "ipd_score": <number>,
  "ipd_bucket": "BAJO|MEDIO|ALTO",
  "insight_bala": "<1-2 frases que sintetizan el hallazgo principal · MAX 240 chars>",
  "fortalezas": [
    {"titulo": "<corto>", "evidencia": "<dato concreto>", "implicacion": "<qué significa>"}
  ],
  "oportunidades": [
    {"titulo": "<corto>", "evidencia": "<dato/benchmark>", "tactica": "<acción específica>"}
  ],
  "debilidades": [
    {"titulo": "<corto>", "evidencia": "<dato concreto>", "riesgo": "<qué puede pasar>"}
  ],
  "amenazas": [
    {"titulo": "<corto>", "evidencia": "<dato/contexto>", "mitigacion": "<cómo blindar>"}
  ],
  "acciones_top3": [
    {"orden": 1, "texto": "<acción ejecutable 14-30d>", "cta_label": "<botón>", "cta_href": "/dashboard/..."}
  ],
  "plataforma_prioritaria": "<FACEBOOK|INSTAGRAM|TIKTOK|YOUTUBE|TWITTER>"
}
```

REGLAS DEL JSON:
- Mismo número de ítems FODA del markdown (8-10 por cuadrante mínimo).
- Acciones: EXACTAMENTE 3.
- CTAs reales de CRECE: /dashboard/hub, /dashboard/aceptacion/fans-y-perfiles, /dashboard/diagnostico, /dashboard/social/clima, /dashboard/sistema/onboarding.
- NO mezclar idiomas · todo en español.

## CONTEXTO REAL DEL DIRIGENTE (USAR SOLO ESTOS DATOS):
"""


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirigente", type=int, required=True, help="dirigente_id")
    ap.add_argument("--apply", action="store_true", help="Persistir a BD")
    ap.add_argument("--max-tokens", type=int, default=8192)
    args = ap.parse_args()

    eng = create_async_engine(DATABASE_URL, echo=False)
    Session = async_sessionmaker(eng, expire_on_commit=False)

    async with Session() as db:
        dirigente = await db.get(Dirigente, args.dirigente)
        if not dirigente:
            print(f"ERROR: dirigente {args.dirigente} no existe", file=sys.stderr)
            return 1

        print(f"[+] Dirigente: {dirigente.full_name} ({dirigente.cargo})", file=sys.stderr)
        print(f"[+] Recolectando contexto...", file=sys.stderr)
        ctx = await _gather_context(db, dirigente)
        print(f"[+] IPD: {ctx['ipd']['score']:.2f} | profiles: {len(ctx['social_profiles'])} | competitors: {len(ctx['top_competitors'])}", file=sys.stderr)

        prompt = ENRICHED_PROMPT_HEADER + "\n```json\n" + json.dumps(ctx, indent=2, ensure_ascii=False, default=str) + "\n```\n"

        print(f"[+] Prompt size: {len(prompt)} chars", file=sys.stderr)

        # 2026-05-21 · cambiado de Claude API a CC subprocess (no requiere API key)
        # · mismo approach que regen_diagnostico_v2.py · effort=high para FODA rico.
        # Si CC no disponible localmente, fallback a gemini-clean.
        import subprocess
        from pathlib import Path

        CLAUDE_BIN = "/Users/marxchavez/.local/bin/claude"
        GEMINI_BIN = "/Users/marxchavez/.claude/bin/gemini-clean"
        CC_EFFORT = os.environ.get("CC_EFFORT", "high")
        TIMEOUT_S = int(os.environ.get("CC_TIMEOUT", "1200"))

        content = None
        if Path(CLAUDE_BIN).exists():
            print(f"[+] Llamando CC subprocess (effort={CC_EFFORT}, timeout={TIMEOUT_S}s)...", file=sys.stderr)
            try:
                r = subprocess.run(
                    [CLAUDE_BIN, "--print", "--effort", CC_EFFORT, prompt],
                    capture_output=True, text=True, timeout=TIMEOUT_S,
                )
                if r.returncode == 0 and r.stdout:
                    content = r.stdout
            except subprocess.TimeoutExpired:
                print(f"[warn] CC subprocess timeout", file=sys.stderr)
        if not content and Path(GEMINI_BIN).exists():
            print(f"[+] Fallback a gemini-clean...", file=sys.stderr)
            try:
                r = subprocess.run([GEMINI_BIN, "--mode", "plan", "-p", prompt],
                                   capture_output=True, text=True, timeout=900)
                if r.returncode == 0 and r.stdout:
                    content = r.stdout
            except subprocess.TimeoutExpired:
                pass
        if not content:
            print("ERROR: Ambos LLMs fallaron · ABORT", file=sys.stderr)
            return 2
        print(f"[+] Generado: {len(content)} chars", file=sys.stderr)

        if not args.apply:
            print("\n=========== OUTPUT (no persistido — usa --apply) ===========\n", file=sys.stderr)
            print(content)
            return 0

        # Extraer JSON estructurado del bloque ```json_diagnostico ... ```
        import re
        estructura_json = None
        m = re.search(r"```json_diagnostico\s*\n(.*?)\n```", content, re.DOTALL)
        if m:
            try:
                estructura_json = json.loads(m.group(1))
                print(f"[+] JSON estructurado parseado: {list(estructura_json.keys())}", file=sys.stderr)
            except json.JSONDecodeError as e:
                print(f"[warn] JSON parse fail: {e}", file=sys.stderr)
        else:
            print("[warn] No se encontró bloque json_diagnostico en output", file=sys.stderr)

        plan = PlanIA(
            dirigente_id=dirigente.id,
            tipo=TipoPlan.DIAGNOSTICO,
            contenido=content,
            modelo_ia=settings.CLAUDE_MODEL,
            prompt_usado=prompt[:2000],
            datos_entrada=ctx,
            generado_por_id=1,  # NOT NULL constraint
            aprobado=False,
            created_at=datetime.now(UTC),
            estructura_json=estructura_json,
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        print(f"[OK] Persistido como planes_ia.id={plan.id} (estructura_json={'sí' if estructura_json else 'no'})", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
