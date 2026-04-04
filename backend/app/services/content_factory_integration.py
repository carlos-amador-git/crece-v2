from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.dirigente import Dirigente
from app.models.social import SocialPost, SocialProfile

logger = logging.getLogger(__name__)


PLATFORM_SPECS = {
    "twitter": {"max_chars": 280, "instrucciones": "Conciso, max 3 hashtags"},
    "instagram_reel": {
        "duracion": "30-60s",
        "instrucciones": "Hook en 3 seg, trending audio, subtitulos obligatorios",
    },
    "instagram_carrusel": {
        "slides": "5-7",
        "instrucciones": "Slide 1 hook visual, final CTA, texto legible",
    },
    "facebook": {
        "max_chars": 2000,
        "instrucciones": "Narrativo, emojis moderados, CTA al final",
    },
    "whatsapp": {
        "max_chars": 500,
        "instrucciones": "Personal, un solo CTA, tono cercano",
    },
}


async def _gather_context(db: AsyncSession, dirigente: Dirigente) -> dict:
    """Collect real metrics to feed the AI prompt. Never invent data.

    Reuses the pattern from plan_generator._gather_context.
    """
    from sqlalchemy import func

    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)

    profiles_result = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente.id)
    )
    profiles = list(profiles_result.scalars().all())

    profiles_data = []
    for p in profiles:
        stats_result = await db.execute(
            select(
                func.count(SocialPost.id),
                func.avg(SocialPost.engagement_rate),
            ).where(
                SocialPost.profile_id == p.id,
                SocialPost.published_at >= thirty_days_ago,
            )
        )
        row = stats_result.one()
        profiles_data.append({
            "platform": p.platform.value,
            "handle": p.handle,
            "followers": p.followers_count,
            "posts_30d": int(row[0]),
            "avg_engagement_30d": round(float(row[1]), 4) if row[1] else 0.0,
        })

    return {
        "dirigente": {
            "nombre": dirigente.full_name,
            "cargo": dirigente.cargo,
            "partido": dirigente.partido,
            "estado": dirigente.estado,
            "municipio": dirigente.municipio,
        },
        "social_profiles": profiles_data,
        "analysis_date": datetime.now(UTC).isoformat(),
    }


def _build_content_prompt(
    context: dict,
    tema: str,
    tono: str,
    plataformas: list[str],
    contexto_adicional: str | None = None,
) -> str:
    """Build a structured prompt for multi-platform content generation."""
    context_json = json.dumps(context, indent=2, ensure_ascii=False, default=str)

    specs_section = ""
    for plat in plataformas:
        spec = PLATFORM_SPECS.get(plat, {"instrucciones": "Formato estandar"})
        specs_section += f"\n### {plat}\n"
        for key, val in spec.items():
            specs_section += f"- {key}: {val}\n"

    prompt = f"""Eres un estratega de comunicacion politica digital experto en el contexto
mexicano. Tu cliente es un dirigente del partido Movimiento Ciudadano (MC).

Genera CONTENIDO LISTO PARA PUBLICAR sobre el siguiente tema, adaptado a cada plataforma.

## TEMA: {tema}
## TONO: {tono}

## DATOS REALES DEL DIRIGENTE (NO inventes datos adicionales):

{context_json}

## ESPECIFICACIONES POR PLATAFORMA:
{specs_section}

## REGLAS:
1. Genera contenido para CADA plataforma solicitada.
2. Respeta los limites de caracteres y formatos de cada plataforma.
3. Incluye hashtags relevantes donde aplique.
4. Usa el tono indicado: {tono}.
5. No inventes datos ni estadisticas.
6. Considera el contexto politico mexicano actual.

## FORMATO DE RESPUESTA:
Responde EXCLUSIVAMENTE con un JSON valido (sin markdown code blocks) con esta estructura:
{{
  "plataforma_nombre": {{
    "contenido": "texto del post",
    "hashtags": ["#tag1", "#tag2"],
    "notas_produccion": "indicaciones para el equipo de produccion"
  }}
}}
"""

    if contexto_adicional:
        prompt += f"\n## CONTEXTO ADICIONAL:\n{contexto_adicional}\n"

    return prompt


async def _register_compliance(
    db: AsyncSession,
    pieza_id: str,
    modelo_ia: str,
    prompt_usado: str,
    user_id: int,
    org_id: int | None,
) -> None:
    """Register IA-generated content for compliance tracking."""
    try:
        from app.models.ia_content_registry import IaContentRegistry
    except ImportError:
        logger.warning("IaContentRegistry model not available; skipping compliance registration")
        return

    registry = IaContentRegistry(
        contenido_pieza_id=pieza_id,
        modelo_ia=modelo_ia,
        prompt_usado=prompt_usado,
        generado_por_id=user_id,
        org_id=org_id,
    )
    db.add(registry)
    await db.flush()


async def generate_content(
    db: AsyncSession,
    dirigente_id: int,
    tema: str,
    contexto: str | None,
    tono: str,
    plataformas: list[str],
    user_id: int,
    org_id: int | None,
):
    """Generate multi-platform content using Claude and persist it."""
    import anthropic

    if not settings.CLAUDE_API_KEY:
        raise ValueError(
            "CLAUDE_API_KEY is not configured. Set the environment variable to enable AI content generation."
        )

    # Load dirigente
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise ValueError(f"Dirigente {dirigente_id} not found")

    context = await _gather_context(db, dirigente)
    prompt = _build_content_prompt(context, tema, tono, plataformas, contexto)

    client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)

    message = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = message.content[0].text

    # Parse JSON response — handle potential markdown code blocks
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        # Remove markdown code block wrapper
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned

    try:
        variantes = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse Claude response as JSON; storing raw text")
        variantes = {"raw_response": raw_text}

    # Persist
    try:
        from app.models.contenido_pieza import ContenidoPieza
    except ImportError:
        raise ImportError("ContenidoPieza model is not available yet")

    pieza = ContenidoPieza(
        dirigente_id=dirigente_id,
        tema=tema,
        tono=tono,
        variantes=variantes,
        modelo_ia=settings.CLAUDE_MODEL,
        prompt_usado=prompt,
        estado="borrador",
        generado_por_id=user_id,
        org_id=org_id,
    )
    db.add(pieza)
    await db.flush()
    await db.refresh(pieza)

    # Compliance registration
    await _register_compliance(
        db,
        pieza_id=str(pieza.id),
        modelo_ia=settings.CLAUDE_MODEL,
        prompt_usado=prompt,
        user_id=user_id,
        org_id=org_id,
    )

    return pieza


async def generate_content_stream(
    db: AsyncSession,
    dirigente_id: int,
    tema: str,
    contexto: str | None,
    tono: str,
    plataformas: list[str],
    user_id: int,
    org_id: int | None,
) -> AsyncGenerator[str, None]:
    """Stream content generation via SSE-compatible chunks.

    Follows the exact pattern from plan_generator.generate_plan_stream.
    """
    import anthropic

    if not settings.CLAUDE_API_KEY:
        yield f"data: {json.dumps({'error': 'CLAUDE_API_KEY is not configured'})}\n\n"
        return

    # Load dirigente
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        yield f"data: {json.dumps({'error': f'Dirigente {dirigente_id} not found'})}\n\n"
        return

    context = await _gather_context(db, dirigente)
    prompt = _build_content_prompt(context, tema, tono, plataformas, contexto)

    client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)

    collected_text = ""

    with client.messages.stream(
        model=settings.CLAUDE_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            collected_text += text
            yield f"data: {json.dumps({'text': text})}\n\n"

    # Parse the collected response
    cleaned = collected_text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if len(lines) > 2 else cleaned

    try:
        variantes = json.loads(cleaned)
    except json.JSONDecodeError:
        variantes = {"raw_response": collected_text}

    # Persist the completed piece
    try:
        from app.models.contenido_pieza import ContenidoPieza
    except ImportError:
        yield f"data: {json.dumps({'error': 'ContenidoPieza model not available'})}\n\n"
        return

    pieza = ContenidoPieza(
        dirigente_id=dirigente_id,
        tema=tema,
        tono=tono,
        variantes=variantes,
        modelo_ia=settings.CLAUDE_MODEL,
        prompt_usado=prompt,
        estado="borrador",
        generado_por_id=user_id,
        org_id=org_id,
    )
    db.add(pieza)
    await db.flush()
    await db.refresh(pieza)

    # Compliance registration
    await _register_compliance(
        db,
        pieza_id=str(pieza.id),
        modelo_ia=settings.CLAUDE_MODEL,
        prompt_usado=prompt,
        user_id=user_id,
        org_id=org_id,
    )

    yield f"data: {json.dumps({'done': True, 'piece_id': str(pieza.id)})}\n\n"
