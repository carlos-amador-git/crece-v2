"""D-23-G' · Prompt template for target_politico classification.

4-cat clasificación binaria expandida (5 etiquetas excluyentes con fallback):
- oficialismo: critica/menciona al gobierno actual al nivel del cargo
- oposicion: critica/menciona oposición política
- propio: habla de su propia gestión/iniciativas/logros
- personal: deportes, familia, cultural, sin contenido político
- no_determinado: post sin texto suficiente para clasificar (fallback)

Reglas de desempate (Gemini cross-audit 2026-04-24):
- Ante duda entre 'propio' y 'oficialismo', priorizar 'propio' si hay
  llamado a la acción (verbos imperativos · CTA · invitaciones).
- El nivel de evaluación del target depende del cargo del dirigente:
  diputado federal evalúa al gobierno federal, alcalde evalúa local.
"""
from __future__ import annotations

import json
import re
from typing import Any

VALID_TARGETS = {"oficialismo", "oposicion", "propio", "personal", "no_determinado"}


PROMPT_TEMPLATE = """Eres clasificador político mexicano. Analiza el post y responde SOLO JSON.

Dirigente: "{dirigente_nombre}" · partido: {partido} · cargo: {cargo}
Plataforma: {plataforma}

Post: "{texto}"

Clasifica el TARGET del post entre 5 etiquetas excluyentes:

1. **oficialismo** — critica, cuestiona o menciona al gobierno actual al nivel del cargo del dirigente (federal si es diputado/senador/legislador federal · estatal si es local · municipal si alcalde). Incluye críticas directas al presidente, gobernador, alcalde según corresponda.

2. **oposicion** — critica, cuestiona o menciona partidos/figuras de oposición política a la propia (al nivel del cargo). Incluye respuesta a ataques de oposición.

3. **propio** — habla de su propia gestión, iniciativas, logros, votaciones, propuestas, eventos personales con dimensión política. Incluye contenido autopromocional con llamado a la acción (asistir a evento, firmar petición, votar). REGLA: ante duda entre 'propio' y 'oficialismo', priorizar 'propio' si hay verbo imperativo o CTA explícito.

4. **personal** — deportes, familia, cultural, gastronomía, fiestas, condolencias personales sin carga política. Sin contenido político en absoluto.

5. **no_determinado** — post sin texto suficiente para clasificar (pura imagen/video sin descripción · texto puramente promocional sin contexto · idioma extranjero · solo emojis).

Responde JSON únicamente:
{{"target":"...", "razon":"una frase corta"}}"""


def build_prompt(
    *,
    texto: str,
    plataforma: str,
    dirigente_nombre: str,
    partido: str,
    cargo: str,
) -> str:
    """Build classification prompt for a single post."""
    texto_clean = (texto or "")[:800].replace('"', "'")
    return PROMPT_TEMPLATE.format(
        texto=texto_clean,
        plataforma=plataforma or "desconocida",
        dirigente_nombre=dirigente_nombre or "(sin nombre)",
        partido=partido or "INDEPENDIENTE",
        cargo=cargo or "(sin cargo)",
    )


def parse_response(raw: str) -> dict[str, Any] | None:
    """Parse JSON response with tolerance for markdown fences and minor errors."""
    if not raw:
        return None

    # Strip markdown code blocks
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]+?\})\s*```", raw)
    cand = fenced.group(1) if fenced else None

    if not cand:
        m = re.search(r"\{[\s\S]+\}", raw)
        cand = m.group(0) if m else None

    if not cand:
        return None

    try:
        result = json.loads(cand)
    except json.JSONDecodeError:
        # Tolerate trailing comma
        cand2 = re.sub(r",\s*([\]\}])", r"\1", cand)
        try:
            result = json.loads(cand2)
        except json.JSONDecodeError:
            return None

    target = (result.get("target") or "").strip().lower()
    if target not in VALID_TARGETS:
        return None

    return {
        "target": target,
        "razon": (result.get("razon") or "").strip()[:200],
    }
