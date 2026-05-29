"""Regenera DIAGNOSTICO con prompt enriquecido usando Gemini CLI.

Corre EN HOST (no en contenedor) porque /opt/homebrew/bin/gemini vive ahí.
Conecta a la BD via la URL expuesta del container Postgres.

Uso desde el host:
  cd backend
  DATABASE_URL='postgresql+asyncpg://crece:crece_dev@localhost:5438/crece' \\
    python scripts/regen_diagnostico_gemini.py --dirigente 8 [--apply]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import UTC, datetime

GEMINI_BIN = "/opt/homebrew/bin/gemini"

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.models.dirigente import Dirigente  # noqa: E402
from app.models.plan_ia import PlanIA, TipoPlan  # noqa: E402
from app.services.plan_generator import _gather_context  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402


ENRICHED_PROMPT_HEADER = """Genera un DIAGNOSTICO COMPLETO de la presencia digital del dirigente.

## TONO Y ESTILO OBLIGATORIO:
Escribe como un consultor senior presentando ante el cliente. Usa lenguaje
evaluativo y directo, no descriptivo. Cada dato debe ir acompanado de su
JUICIO. Usa metaforas y frases memorables.

## ESTRUCTURA OBLIGATORIA (10 secciones):

### 1. Resumen Ejecutivo
3-4 oraciones con la HISTORIA del hallazgo principal. Incluye IPD score,
brecha vs competidor con ratio exacto, oportunidad principal.

### 2. Analisis por Plataforma
Para CADA plataforma con datos: tabla, benchmark de referencia,
calificacion (CRITICO/BAJO/ACEPTABLE/BUENO/EXCEPCIONAL), parrafo
narrativo interpretativo.

### 3. Plataformas Ausentes
Cuales faltan y por que son criticas en el contexto del territorio.

### 4. Analisis de Sentimiento
Interpreta la distribucion. Si la muestra es pequena, advierte.

### 5. Analisis FODA — SECCION CRITICA, EXTENSA

**REGLAS DE EXTENSION OBLIGATORIAS:**
- MINIMO 8 items por cuadrante. NO ACEPTABLE menos de 6.
- CADA item tiene: (a) hallazgo concreto + (b) evidencia numerica
  especifica + (c) implicacion politica/tactica.
- PROHIBIDO: items genericos como 'mejorar redes' o 'aumentar presencia'.

**Formato OBLIGATORIO en MARKDOWN — DOS tablas separadas:**

| **Fortalezas**                                           | **Debilidades**                                          |
| :------------------------------------------------------- | :------------------------------------------------------- |
| <Fortaleza 1 con dato numerico>. **Implicacion:** ...    | <Debilidad 1 con dato>. **Riesgo:** ...                  |
| ... (8-10 filas cada lado)                               | ...                                                      |

| **Oportunidades**                                        | **Amenazas**                                             |
| :------------------------------------------------------- | :------------------------------------------------------- |
| <Oportunidad 1 con benchmark concreto>. **Tactica:** ... | <Amenaza 1 con escenario>. **Mitigacion:** ...           |
| ... (8-10 filas cada lado)                               | ...                                                      |

EJEMPLOS de granularidad esperada (NO COPIES, son ejemplos):

Fortaleza: "Engagement promedio en TikTok de 4.47% (2.5x sobre benchmark
politico mexicano de 1.8%). **Implicacion:** TikTok es el unico canal con
comunidad activa — vehiculo principal de narrativa de campana."

Debilidad: "Cero publicaciones en Twitter en 30 dias con 55,640 seguidores
acumulados. **Riesgo:** seguidores percibiran abandono y migraran a
competidores activos."

### 6. Tabla Comparativa vs Competidores
Tabla lado a lado. Calcula ratios.

### 7. Tabla de KPIs
metrica | valor actual | meta 30d | meta 90d | herramienta.

### 8. Recomendaciones (3 fases)
INMEDIATAS / CORTO PLAZO / MEDIANO PLAZO. Cada una: frecuencia, formato,
responsable. Conecta con dato real.

### 9. Plataforma Prioritaria (ROI)
Cual plataforma tiene mejor retorno y por que.

### 10. Datos Faltantes
Que se necesita para profundizar.

## CONTEXTO REAL DEL DIRIGENTE (USAR SOLO ESTOS DATOS, NO INVENTAR):

```json
{CONTEXT_JSON}
```

Genera el documento markdown completo. NO encierres en triple backticks
externos — el output va directo a una BD. Empieza con "## DIAGNOSTICO ..."
"""


def call_gemini(prompt: str, timeout: int = 600) -> str:
    """Invoca gemini -p con el prompt y devuelve stdout."""
    proc = subprocess.run(
        [GEMINI_BIN, "-p", prompt],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if proc.returncode != 0:
        sys.stderr.write(f"gemini stderr: {proc.stderr}\n")
        raise RuntimeError(f"gemini failed: returncode={proc.returncode}")
    return proc.stdout


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirigente", type=int, required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--timeout", type=int, default=600)
    args = ap.parse_args()

    eng = create_async_engine(DATABASE_URL, echo=False)
    Session = async_sessionmaker(eng, expire_on_commit=False)

    async with Session() as db:
        dirigente = await db.get(Dirigente, args.dirigente)
        if not dirigente:
            print(f"ERROR: dirigente {args.dirigente} no existe", file=sys.stderr)
            return 1

        print(f"[+] Dirigente: {dirigente.full_name}", file=sys.stderr)
        print(f"[+] Recolectando contexto...", file=sys.stderr)
        ctx = await _gather_context(db, dirigente)
        print(f"[+] IPD: {ctx['ipd']['score']:.2f} · profiles: {len(ctx['social_profiles'])}", file=sys.stderr)

        ctx_json = json.dumps(ctx, indent=2, ensure_ascii=False, default=str)
        prompt = ENRICHED_PROMPT_HEADER.replace("{CONTEXT_JSON}", ctx_json)

        print(f"[+] Prompt size: {len(prompt)} chars · invoking Gemini CLI...", file=sys.stderr)
        content = call_gemini(prompt, timeout=args.timeout)
        print(f"[+] Output: {len(content)} chars", file=sys.stderr)

        if not args.apply:
            print("\n=========== OUTPUT (no persistido — usa --apply) ===========\n", file=sys.stderr)
            print(content)
            return 0

        plan = PlanIA(
            dirigente_id=dirigente.id,
            tipo=TipoPlan.DIAGNOSTICO,
            contenido=content,
            modelo_ia="gemini-cli-enriched",
            prompt_usado=prompt[:2000],
            datos_entrada=ctx,
            generado_por_id=None,
            aprobado=False,
            created_at=datetime.now(UTC),
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        print(f"[OK] Persistido como planes_ia.id={plan.id}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
