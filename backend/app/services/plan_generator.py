from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.benchmark import Competidor, CompetidorSocialProfile
from app.models.dirigente import Dirigente
from app.models.plan_ia import PlanIA, TipoPlan
from app.models.social import SentimentLabel, SocialPost, SocialProfile
from app.models.user import User
from app.services.diagnostico import calculate_ipd

logger = logging.getLogger(__name__)


async def _gather_context(db: AsyncSession, dirigente: Dirigente) -> dict:
    """Collect real metrics to feed the AI prompt. Never invent data."""
    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)

    # Social profiles summary
    profiles_result = await db.execute(
        select(SocialProfile).where(SocialProfile.dirigente_id == dirigente.id)
    )
    profiles = list(profiles_result.scalars().all())

    profiles_data = []
    for p in profiles:
        # Recent post stats
        stats_result = await db.execute(
            select(
                func.count(SocialPost.id),
                func.avg(SocialPost.engagement_rate),
                func.avg(SocialPost.sentiment_score),
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
            "avg_sentiment_30d": round(float(row[2]), 4) if row[2] else None,
        })

    # Sentiment distribution
    sent_result = await db.execute(
        select(SocialPost.sentiment_label, func.count(SocialPost.id))
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(
            SocialProfile.dirigente_id == dirigente.id,
            SocialPost.published_at >= thirty_days_ago,
            SocialPost.sentiment_label.is_not(None),
        )
        .group_by(SocialPost.sentiment_label)
    )
    sentiment_dist = {row[0].value: int(row[1]) for row in sent_result.all()}

    # Top competitors
    comp_result = await db.execute(
        select(Competidor, func.sum(CompetidorSocialProfile.followers_count))
        .join(CompetidorSocialProfile)
        .where(Competidor.es_rival.is_(True))
        .group_by(Competidor.id)
        .order_by(func.sum(CompetidorSocialProfile.followers_count).desc())
        .limit(5)
    )
    competitors = [
        {
            "nombre": row[0].nombre,
            "partido": row[0].partido,
            "total_followers": int(row[1]) if row[1] else 0,
        }
        for row in comp_result.all()
    ]

    # Calculate IPD score from diagnostico engine
    ipd = await calculate_ipd(db, dirigente)

    return {
        "dirigente": {
            "nombre": dirigente.full_name,
            "cargo": dirigente.cargo,
            "partido": dirigente.partido,
            "estado": dirigente.estado,
            "municipio": dirigente.municipio,
        },
        "ipd": {
            "score": ipd.ipd_score,
            "scale": "0-10 (10 = presencia digital óptima)",
            "platform_scores": ipd.platform_scores,
            "platform_coverage": f"{ipd.platform_coverage:.0%}",
            "posting_frequency_per_day": ipd.posting_frequency,
            "interpretation": (
                "CRITICO" if ipd.ipd_score < 3
                else "BAJO" if ipd.ipd_score < 5
                else "MEDIO" if ipd.ipd_score < 7
                else "BUENO" if ipd.ipd_score < 9
                else "EXCELENTE"
            ),
        },
        "social_profiles": profiles_data,
        "sentiment_30d": sentiment_dist,
        "top_competitors": competitors,
        "analysis_date": datetime.now(UTC).isoformat(),
    }


def _build_prompt(tipo: TipoPlan, context: dict, extra: str | None = None) -> str:
    """Build a structured prompt from real data."""
    context_json = json.dumps(context, indent=2, ensure_ascii=False, default=str)

    tipo_instructions = {
        TipoPlan.DIAGNOSTICO: (
            "Genera un DIAGNOSTICO COMPLETO de la presencia digital del dirigente.\n\n"
            "## TONO Y ESTILO OBLIGATORIO:\n"
            "Escribe como un consultor senior presentando ante el cliente. Usa lenguaje evaluativo "
            "y directo, no descriptivo. NO digas 'el engagement es 7.74%' — di 'el engagement de "
            "7.74% es EXCEPCIONAL, casi el doble del benchmark para politicos mexicanos (3-5%), "
            "lo que revela una comunidad pequena pero ferozmente leal'. Cada dato debe ir acompanado "
            "de su JUICIO: ¿es bueno, malo, critico, excepcional? ¿Que significa para el dirigente?\n"
            "Usa metaforas y frases memorables: 'presencia dormida', 'mina de oro sin explotar', "
            "'brecha de 40:1', 'invisible por inactividad'. El diagnostico debe ser MEMORABLE.\n\n"
            "## ESTRUCTURA OBLIGATORIA (10 secciones):\n\n"
            "### 1. Resumen Ejecutivo\n"
            "3-4 oraciones que cuenten la HISTORIA del hallazgo principal. Incluye el IPD score "
            "(Indice de Penetracion Digital, escala 0-10, dato incluido en los datos). "
            "Menciona la brecha principal vs competidor con ratio exacto (ej: '40:1'). "
            "Cierra con la oportunidad mas importante.\n\n"
            "### 2. Analisis por Plataforma\n"
            "Para CADA plataforma, incluye:\n"
            "- Tabla con: seguidores, posts/30d, engagement, sentimiento\n"
            "- Benchmark de referencia (politicos mexicanos de cargo similar en estado similar)\n"
            "- Calificacion: CRITICO / BAJO / ACEPTABLE / BUENO / EXCEPCIONAL\n"
            "- 1 parrafo narrativo que INTERPRETE los numeros (no solo los repita)\n\n"
            "### 3. Plataformas Ausentes\n"
            "Cuales faltan y por que son criticas EN EL CONTEXTO ESPECIFICO de este dirigente y territorio.\n\n"
            "### 4. Analisis de Sentimiento\n"
            "Interpreta la distribucion. Si la muestra es pequena, advierte sobre sesgo estadistico. "
            "¿El sentimiento positivo es por burbuja de simpatizantes o por alcance real?\n\n"
            "### 5. Analisis FODA\n"
            "Minimo 3 items por cuadrante en formato tabla. CADA item debe ser especifico al territorio, "
            "cargo y datos del dirigente. PROHIBIDO: items genericos como 'aprovechar redes sociales'.\n\n"
            "### 6. Tabla Comparativa vs Competidores\n"
            "Tabla lado a lado con todos los numeros disponibles. Calcula ratios (ej: 'Batres tiene 92x "
            "mas seguidores en Twitter'). Si faltan datos de competidores, indica que se necesitan.\n\n"
            "### 7. Tabla de KPIs\n"
            "Formato: metrica | valor actual | meta 30 dias | meta 90 dias | herramienta de medicion. "
            "Incluye el IPD score como primer KPI.\n\n"
            "### 8. Recomendaciones (divididas en 3 fases)\n"
            "- INMEDIATAS (semana 1-2): acciones ejecutables manana\n"
            "- CORTO PLAZO (mes 1-2): crecimiento y consistencia\n"
            "- MEDIANO PLAZO (mes 2-3): consolidacion y expansion\n"
            "Para CADA recomendacion: frecuencia exacta, formato de contenido, responsable sugerido. "
            "Conecta cada recomendacion con un dato real ('dado que el engagement en Instagram es 7.74%...').\n\n"
            "### 9. Plataforma Prioritaria (ROI)\n"
            "Identifica CUAL plataforma tiene el mejor retorno de esfuerzo y por que. "
            "Justifica con datos del propio dirigente, no con generalizaciones.\n\n"
            "### 10. Datos Faltantes\n"
            "Lista de datos que se necesitan para profundizar el analisis."
        ),
        TipoPlan.CONSOLIDACION: (
            "Genera un PLAN DE CONSOLIDACION a 90 dias.\n\n"
            "ESTRUCTURA OBLIGATORIA:\n"
            "1. Diagnostico rapido del estado actual (1 parrafo)\n"
            "2. FASE 1 (Dias 1-30) — Fundacion: tabla de acciones con plataforma, KPI meta, "
            "frecuencia de posting especifica, responsable\n"
            "3. FASE 2 (Dias 31-60) — Crecimiento: misma estructura\n"
            "4. FASE 3 (Dias 61-90) — Consolidacion: misma estructura\n"
            "5. Tabla de KPIs SMART: metrica | actual | meta 30d | meta 60d | meta 90d\n"
            "6. Calendario editorial semanal tipo (lunes a domingo, por plataforma)\n"
            "7. Riesgos y mitigaciones (tabla)\n"
            "8. Presupuesto estimado si aplica"
        ),
        TipoPlan.CRISIS: (
            "Genera un PLAN DE MANEJO DE CRISIS digital.\n\n"
            "ESTRUCTURA OBLIGATORIA:\n"
            "1. Evaluacion de vulnerabilidades actuales del dirigente\n"
            "2. Protocolo de respuesta rapida: tiempos de reaccion por plataforma\n"
            "3. Arbol de escalamiento: quien responde, quien aprueba, quien comunica\n"
            "4. Plantillas de respuesta por tipo de crisis (ataque personal, fake news, escandalo partido, tema sensible)\n"
            "5. Narrativas alternativas pre-preparadas\n"
            "6. Plan de recuperacion reputacional post-crisis (7, 15, 30 dias)\n"
            "7. Metricas de monitoreo continuo"
        ),
        TipoPlan.CONTENIDO: (
            "Genera un PLAN DE CONTENIDO detallado para 30 dias.\n\n"
            "ESTRUCTURA OBLIGATORIA:\n"
            "1. Pilares tematicos (maximo 5) con justificacion\n"
            "2. Calendario semanal por plataforma: dia, hora, formato, pilar tematico\n"
            "3. Para cada plataforma: numero exacto de posts/semana, formatos (texto, imagen, video, story, reel, live), "
            "longitud optima, hashtags sugeridos\n"
            "4. 10 ejemplos de posts concretos (redactados, listos para publicar) distribuidos por plataforma\n"
            "5. Horarios optimos de publicacion para audiencia en Mexico (por plataforma)\n"
            "6. Metricas de exito por tipo de contenido"
        ),
    }

    instruction = tipo_instructions[tipo]

    # Build territory context if available
    territory_context = ""
    dirigente_info = context.get("dirigente", {})
    estado = dirigente_info.get("estado", "")
    municipio = dirigente_info.get("municipio", "")
    if estado or municipio:
        territory = municipio or estado
        territory_context = (
            f"\n## CONTEXTO TERRITORIAL:\n"
            f"El dirigente opera en {territory}. Considera los temas que dominan la "
            f"conversacion publica en esta zona (movilidad, seguridad, agua, servicios, "
            f"empleo) al hacer recomendaciones de contenido. Las recomendaciones deben "
            f"ser especificas para este territorio, no genericas.\n"
        )

    prompt = f"""Eres un estratega de comunicacion politica digital con 15 anos de experiencia
en el contexto mexicano. Trabajas para Movimiento Ciudadano (MC). Tu analisis debe ser
tan especifico y accionable que el equipo del dirigente pueda ejecutarlo manana.

{instruction}

## DATOS REALES DEL DIRIGENTE:

{context_json}
{territory_context}
## REGLAS CRITICAS:
1. Basa tu analisis PRINCIPALMENTE en los datos proporcionados. Si conoces informacion publica verificable sobre este dirigente (columnas en medios, apariciones publicas, trayectoria), puedes mencionarla como contexto adicional marcandola como "Fuente: conocimiento publico" para distinguirla de los datos medidos.
2. Si faltan datos medidos (metricas, seguidores, engagement), indica que se necesitan. NO inventes metricas numericas.
3. Responde en espanol mexicano.
4. Usa formato Markdown con tablas, negritas, y estructura visual clara.
5. Se hiper-especifico: numeros exactos, frecuencias concretas, formatos por plataforma.
6. CADA dato debe ir acompanado de un JUICIO evaluativo (critico/bajo/aceptable/bueno/excepcional).
7. Considera el contexto politico mexicano actual y las particularidades del territorio.
8. PROHIBIDO: consejos genericos tipo manual. Cada recomendacion DEBE conectar con un dato real.
9. PROHIBIDO: repetir los datos sin interpretarlos. Siempre agrega el "¿y esto que significa?".
10. USA metaforas y frases memorables para los hallazgos clave. Este documento sera leido por el dirigente.
11. Incluye presupuestos estimados cuando sea relevante (en MXN).
"""

    if extra:
        prompt += f"\n## CONTEXTO ADICIONAL DEL USUARIO:\n{extra}\n"

    return prompt


# ── Provider: Claude API ─────────────────────────────────────────────


async def _generate_claude(prompt: str) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
    message = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


async def _stream_claude(prompt: str) -> AsyncGenerator[str, None]:
    import anthropic

    client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
    with client.messages.stream(
        model=settings.CLAUDE_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text


# ── Provider: Ollama (Gemma 4 local) ────────────────────────────────


async def _generate_ollama(prompt: str) -> str:
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
            },
        )
        resp.raise_for_status()
        return resp.json()["response"]


async def _stream_ollama(prompt: str) -> AsyncGenerator[str, None]:
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream(
            "POST",
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": settings.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": True,
            },
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line:
                    chunk = json.loads(line)
                    if chunk.get("response"):
                        yield chunk["response"]


# ── Provider router ──────────────────────────────────────────────────


def _get_provider() -> str:
    return settings.AI_PROVIDER


def _get_model_name() -> str:
    provider = _get_provider()
    if provider == "ollama":
        return f"ollama/{settings.OLLAMA_MODEL}"
    return settings.CLAUDE_MODEL


# ── Public API ───────────────────────────────────────────────────────


async def generate_plan(
    db: AsyncSession,
    dirigente: Dirigente,
    tipo: TipoPlan,
    user: User,
    contexto_adicional: str | None = None,
    provider_override: str | None = None,
) -> PlanIA:
    """Generate an AI plan and persist it. Uses configured provider or override."""
    context = await _gather_context(db, dirigente)
    prompt = _build_prompt(tipo, context, contexto_adicional)

    provider = provider_override or _get_provider()

    if provider == "ollama":
        contenido = await _generate_ollama(prompt)
    else:
        contenido = await _generate_claude(prompt)

    model_name = f"ollama/{settings.OLLAMA_MODEL}" if provider == "ollama" else settings.CLAUDE_MODEL

    plan = PlanIA(
        dirigente_id=dirigente.id,
        tipo=tipo,
        contenido=contenido,
        modelo_ia=model_name,
        prompt_usado=prompt,
        datos_entrada=context,
        generado_por_id=user.id,
    )
    db.add(plan)
    await db.flush()
    await db.refresh(plan)
    return plan


async def generate_plan_stream(
    db: AsyncSession,
    dirigente: Dirigente,
    tipo: TipoPlan,
    user: User,
    contexto_adicional: str | None = None,
    provider_override: str | None = None,
) -> AsyncGenerator[str, None]:
    """Stream plan generation via SSE-compatible chunks."""
    context = await _gather_context(db, dirigente)
    prompt = _build_prompt(tipo, context, contexto_adicional)

    provider = provider_override or _get_provider()
    collected_text = ""

    if provider == "ollama":
        stream_fn = _stream_ollama(prompt)
    else:
        stream_fn = _stream_claude(prompt)

    async for text in stream_fn:
        collected_text += text
        yield f"data: {json.dumps({'text': text})}\n\n"

    model_name = f"ollama/{settings.OLLAMA_MODEL}" if provider == "ollama" else settings.CLAUDE_MODEL

    plan = PlanIA(
        dirigente_id=dirigente.id,
        tipo=tipo,
        contenido=collected_text,
        modelo_ia=model_name,
        prompt_usado=prompt,
        datos_entrada=context,
        generado_por_id=user.id,
    )
    db.add(plan)
    await db.flush()
    await db.refresh(plan)

    yield f"data: {json.dumps({'done': True, 'plan_id': plan.id})}\n\n"
