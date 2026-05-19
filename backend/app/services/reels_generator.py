"""Generador de guiones para reels usando Groq Llama 3.3 70B (tier gratuito).

Decisión arquitectural D-REELS-GROQ-1 (2026-05-15):
- Groq tier gratuito: 30 req/min · Llama 3.3 70B Versatile · ultra-low latency
- httpx async (sin SDK pesado)
- Persistencia en tabla `contenido_piezas` existente (reusar · anti-over-engineering)
- ZERO API paga · cumple decisión "no hay API de ningún tipo" (CEO)

NO mockear en este service. Si Groq no responde correctamente, lanzar
excepción para que el endpoint retorne 503 honesto. Cero data ficticia.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"

# Tono → guidance específico para el prompt
TONO_GUIDANCE: dict[str, str] = {
    "informativo": (
        "Tono claro, didáctico, sin sensacionalismo. "
        "Explica los datos con precisión. Estilo: artículo de divulgación."
    ),
    "emocional": (
        "Tono cálido, conecta emocionalmente con la audiencia. "
        "Usa narrativa personal, anécdotas, sentimientos. Estilo: testimonio."
    ),
    "urgente": (
        "Tono directo, llamada inmediata a la atención. Lenguaje activo. "
        "Sentido de oportunidad. Estilo: alerta o convocatoria."
    ),
    "inspiracional": (
        "Tono motivador, eleva la audiencia. Mensaje aspiracional. "
        "Visión de futuro. Estilo: discurso de cierre."
    ),
}

# Duración → palabras objetivo (en español hablado: ~150 palabras/min)
DURACION_PALABRAS: dict[int, int] = {
    15: 38,   # ~15 seg
    30: 75,   # ~30 seg
    60: 150,  # ~60 seg
}


def _build_prompt(
    dirigente_nombre: str,
    dirigente_cargo: str | None,
    tema: str | None,
    duracion_segundos: int,
    tono: str,
    incluir_cta: bool,
    contexto_adicional: str | None,
    contexto_dirigente: str | None = None,
) -> str:
    """Construye prompt estructurado para generar guión de reel.

    El prompt instruye a Llama a retornar JSON parseable con secciones
    explícitas. Resistente a fence ```json``` (lo limpiamos post-receive).

    Args:
        contexto_dirigente: bloque de texto pre-formateado por
            `dirigente_context_builder.format_context_for_prompt`. Cuando se
            pasa, el LLM recibe datos reales del dirigente (tono dominante en
            posts, target predominante, posts recientes, promesas, efemérides)
            para particularizar el guión por actor. Sin este parámetro el
            prompt opera en modo genérico (backward compat).
    """
    palabras_target = DURACION_PALABRAS.get(duracion_segundos, 75)
    tono_guidance = TONO_GUIDANCE.get(tono, TONO_GUIDANCE["informativo"])

    cargo_str = f" ({dirigente_cargo})" if dirigente_cargo else ""
    tema_str = tema or "tema libre relevante para la audiencia política del dirigente"
    contexto_dirigente_str = (
        f"\n\n{contexto_dirigente}" if contexto_dirigente else ""
    )
    contexto_str = (
        f"\n\nCONTEXTO ADICIONAL DEL USUARIO:\n{contexto_adicional}" if contexto_adicional else ""
    )
    cta_instruction = (
        "- CTA: 1 línea de cierre con llamada a acción clara (etiquetar, "
        "compartir, visitar perfil, etc.)."
        if incluir_cta
        else "- CTA: omitir · script termina en el desarrollo."
    )

    return f"""Eres un guionista experto en contenido político para redes sociales mexicanas.
Genera UN guión de reel (Instagram / TikTok / Facebook) para:

DIRIGENTE: {dirigente_nombre}{cargo_str}
TEMA: {tema_str}
DURACIÓN: {duracion_segundos} segundos (~{palabras_target} palabras totales)
TONO: {tono} — {tono_guidance}{contexto_dirigente_str}{contexto_str}

ESTRUCTURA REQUERIDA:
- Hook (primeros 3-5 segundos): pregunta, dato sorprendente, o afirmación que detenga el scroll.
- Desarrollo (cuerpo del reel): mensaje principal con narrativa fluida. Lenguaje natural mexicano.
{cta_instruction}

REGLAS DURAS:
- NO uses hashtags en el guión (eso va en el caption, no en el voice over).
- NO uses palabras genéricas tipo "como sabemos", "es importante mencionar".
- NO menciones marca personal del dirigente más allá del nombre cuando aplique.
- NO inventes datos numéricos · si no tienes un dato concreto, hazlo cualitativo.
- ESCRIBE PARA SER LEÍDO EN VOZ ALTA · cuida ritmo, pausas naturales, sin trabalenguas.

FORMATO DE SALIDA (JSON puro · sin fence markdown):
{{
  "hook": "primera línea que detiene el scroll",
  "desarrollo": "cuerpo del guión completo",
  "cta": "{("línea de cierre con llamada a acción" if incluir_cta else "")}"
}}
"""


async def _call_groq(prompt: str) -> dict[str, Any]:
    """Llama a Groq API y retorna el response JSON completo.

    Raises:
        RuntimeError si GROQ_API_KEY no configurada
        httpx.HTTPStatusError si Groq retorna error
        ValueError si el response no es JSON parseable
    """
    api_key = getattr(settings, "GROQ_API_KEY", None) or ""
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY no configurada. Registrar en console.groq.com (gratuito) "
            "y agregar al .env como GROQ_API_KEY=gsk_..."
        )

    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.8,
        "max_tokens": 1024,
        # response_format JSON object para que Llama retorne JSON limpio sin fence
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{GROQ_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()


def _parse_script_from_response(groq_response: dict[str, Any]) -> dict[str, str]:
    """Extrae el guión estructurado del response Groq.

    Llama con response_format=json_object retorna texto JSON limpio en
    `choices[0].message.content`. Caveat: aun así, validar el shape.
    """
    try:
        content = groq_response["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"Response Groq sin choices[0].message.content: {e}") from e

    # Strip por si llama mete fence ```json``` (no debería con response_format)
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]

    parsed = json.loads(content)

    # Shape validation
    hook = parsed.get("hook", "").strip()
    desarrollo = parsed.get("desarrollo", "").strip()
    cta = parsed.get("cta", "").strip()

    if not hook or not desarrollo:
        raise ValueError(
            f"Script Groq incompleto: hook={bool(hook)} desarrollo={bool(desarrollo)}"
        )

    return {"hook": hook, "desarrollo": desarrollo, "cta": cta}


async def generate_reel_script(
    *,
    dirigente_nombre: str,
    dirigente_cargo: str | None,
    tema: str | None,
    duracion_segundos: int,
    tono: str,
    incluir_cta: bool,
    contexto_adicional: str | None,
    contexto_dirigente: str | None = None,
) -> dict[str, Any]:
    """Genera UN guión de reel via Groq.

    Args:
        contexto_dirigente: bloque de texto pre-formateado por
            `dirigente_context_builder.format_context_for_prompt`. Cuando se
            pasa, particulariza el guión usando datos BD del dirigente
            (tono dominante, target predominante, posts recientes, promesas,
            efemérides). El endpoint reels.py lo construye automáticamente.

    Returns:
        {
            "script": {"hook": ..., "desarrollo": ..., "cta": ...},
            "metadata": {
                "model": "groq/llama-3.3-70b-versatile",
                "prompt_tokens": int,
                "completion_tokens": int,
                "elapsed_ms": int,
                "context_enriched": bool,
            },
            "prompt_usado": str,
        }
    """
    prompt = _build_prompt(
        dirigente_nombre=dirigente_nombre,
        dirigente_cargo=dirigente_cargo,
        tema=tema,
        duracion_segundos=duracion_segundos,
        tono=tono,
        incluir_cta=incluir_cta,
        contexto_adicional=contexto_adicional,
        contexto_dirigente=contexto_dirigente,
    )

    t0 = time.time()
    response = await _call_groq(prompt)
    elapsed_ms = int((time.time() - t0) * 1000)

    script = _parse_script_from_response(response)

    usage = response.get("usage") or {}
    metadata = {
        "model": f"groq/{GROQ_MODEL}",
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "elapsed_ms": elapsed_ms,
        "context_enriched": contexto_dirigente is not None,
    }

    logger.info(
        f"reel_script generated · dirigente={dirigente_nombre} "
        f"tono={tono} dur={duracion_segundos}s elapsed={elapsed_ms}ms "
        f"tokens={metadata['completion_tokens']}"
    )

    return {
        "script": script,
        "metadata": metadata,
        "prompt_usado": prompt,
    }
