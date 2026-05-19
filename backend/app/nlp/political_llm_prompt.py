"""Prompt template for Gemma3:12b political classification (v2 — compact).

Layer 2 — Comprensión del texto:
- Gemma clasifica tono_discurso + target_politico + es_rt
- NO calcula score (eso lo hace Python con la matriz del tenant)

Layer 3 (Python) aplica la matriz a (rol, tono, target) → score_politico_ajustado

Rationale del cambio v1→v2: prompt con matriz completa embebida (~1500 tokens)
causaba 5+ min/post en Gemma3:12b Mac M-series. Prompt compacto ~300 tokens
permite 15-30s/post, viable para batch 3,709 posts.
"""
from __future__ import annotations

from typing import Any

PROMPT_V2 = """Analiza este post de {plataforma} y clasifícalo. Responde SOLO JSON válido.

Post: "{texto}"

Clasifica:
1. TONO (elige uno):
- critico: cuestiona, denuncia, señala fallas
- propositivo: propone soluciones
- celebratorio: celebra logros o efemérides
- informativo: hechos sin postura
- solidario: condolencias, apoyo
- ataque: ataque directo a persona/institución
- personal: contenido íntimo sin carga política

2. TARGET principal (elige uno):
- gobierno: gobierno/funcionarios en turno
- oposicion: partidos opositores
- ciudadania: la gente en general
- medios: prensa, periodistas
- autopromocion: el autor mismo
- tema_especifico: un tema (sin atacar actor)
- otro

3. ES_RT: true si empieza con "RT @"

Responde JSON únicamente:
{{"tono":"...","target":"...","es_rt":false,"razon":"una frase"}}"""


PROMPT_V3_COMMENT = """Analiza este comment de {plataforma} dirigido a un post del dirigente "{dirigente_nombre}" (rol político: {rol_politico}). Responde SOLO JSON válido.

Comment: "{texto}"

Clasifica:
1. TONO (elige uno):
- critico: cuestiona, denuncia, señala fallas
- propositivo: propone soluciones
- celebratorio: celebra logros, apoya
- informativo: hechos sin postura
- solidario: condolencias, apoyo emocional
- ataque: ataque directo a persona/institución
- personal: contenido íntimo sin carga política

2. TARGET principal (elige uno):
- dirigente: el autor del post original (respuesta directa a él)
- gobierno: gobierno/funcionarios en turno
- oposicion: partidos opositores
- ciudadania: la gente en general
- medios: prensa, periodistas
- autopromocion: el comentarista se promueve a sí mismo
- tema_especifico: un tema (sin atacar actor)
- otro

Responde JSON únicamente:
{{"tono":"...","target":"...","razon":"una frase"}}"""


def build_prompt(*, texto: str, plataforma: str) -> str:
    """Build compact prompt (v2). Only classifies tono+target, no score."""
    texto_clean = texto[:800].replace('"', "'")  # truncate + escape
    return PROMPT_V2.format(texto=texto_clean, plataforma=plataforma)


def build_comment_prompt(
    *,
    texto: str,
    plataforma: str,
    dirigente_nombre: str,
    rol_politico: str,
) -> str:
    """Build comment classification prompt (v3). target=dirigente available."""
    texto_clean = texto[:800].replace('"', "'")
    return PROMPT_V3_COMMENT.format(
        texto=texto_clean,
        plataforma=plataforma,
        dirigente_nombre=dirigente_nombre,
        rol_politico=rol_politico,
    )


def parse_response(raw: str) -> dict[str, Any] | None:
    """Parse Gemma's JSON response with tolerance."""
    import json
    import re

    # Strip markdown code blocks
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if match:
        raw = match.group(1)
    else:
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            raw = raw[start:end + 1]

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return None

    required = {"tono", "target", "es_rt"}
    if not required.issubset(result.keys()):
        return None

    try:
        result["es_rt"] = bool(result["es_rt"])
    except (ValueError, TypeError):
        return None

    valid_tonos = {"critico", "propositivo", "celebratorio", "informativo", "solidario", "ataque", "personal"}
    valid_targets = {"gobierno", "oposicion", "ciudadania", "medios", "autopromocion", "tema_especifico", "otro"}
    if result["tono"] not in valid_tonos or result["target"] not in valid_targets:
        return None

    if "razon" not in result:
        result["razon"] = ""

    return result


def apply_matrix(
    rol: str, tono: str, target: str, matriz_cells: list[dict],
) -> tuple[int, str | None]:
    """Python-side application of the political framework matrix.

    Returns (score, descripcion). If combination not found, returns (0, None).
    This is Layer 3 — applies after LLM classification.
    """
    for c in matriz_cells:
        if c["rol"] == rol and c["tono"] == tono and c["target"] == target:
            return c["score_effective"], c.get("descripcion")
    return 0, None
