from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.contenido import ContenidoGenerado, EstadoContenido, FormatoContenido
from app.models.dirigente import Dirigente
from app.models.user import User

logger = logging.getLogger(__name__)

# ── Platform constraints ────────────────────────────────────────────────

_PLATFORM_CONSTRAINTS: dict[FormatoContenido, dict[str, object]] = {
    FormatoContenido.POST_TWITTER: {
        "max_chars": 280,
        "instruction": (
            "Escribe un tweet de maximo 280 caracteres. "
            "Tono conversacional y directo. Maximo 2 hashtags relevantes. "
            "Evita lenguaje generico de politico. Debe sonar autentico y humano."
        ),
        "example_structure": "Mensaje directo + dato/opinion + CTA o hashtag",
    },
    FormatoContenido.POST_INSTAGRAM: {
        "max_chars": 2200,
        "instruction": (
            "Escribe un caption de Instagram (maximo 2200 caracteres). "
            "Primera linea debe ser un hook que capture atencion. "
            "Incluye 5-10 hashtags relevantes AL FINAL, separados del texto principal. "
            "Sugiere brevemente que tipo de imagen o carrusel acompanaria el post."
        ),
        "example_structure": "Hook → Desarrollo → CTA → [linea en blanco] → #hashtags",
    },
    FormatoContenido.POST_FACEBOOK: {
        "max_chars": 5000,
        "instruction": (
            "Escribe un post de Facebook extenso y compartible. "
            "Usa parrafos cortos para facilitar la lectura. "
            "Incluye una pregunta al final para generar engagement en comentarios. "
            "Puede ser mas largo y detallado que otros formatos."
        ),
        "example_structure": "Gancho → Contexto → Desarrollo → Pregunta/CTA",
    },
    FormatoContenido.REEL_SCRIPT: {
        "max_chars": 3000,
        "instruction": (
            "Escribe un guion para un Reel/TikTok de 30-60 segundos. "
            "Estructura: HOOK (primeros 3 segundos, crucial) → CONTENIDO (20-40 seg) → CTA (5-10 seg). "
            "Incluye indicaciones visuales entre corchetes [accion/escena]. "
            "El hook debe ser una pregunta provocadora o dato impactante. "
            "Lenguaje coloquial, ritmo rapido, frases cortas."
        ),
        "example_structure": "[HOOK 0-3s] → [CONTENIDO 3-45s] → [CTA 45-60s]",
    },
    FormatoContenido.THREAD_TWITTER: {
        "max_chars": 280,  # per tweet
        "instruction": (
            "Escribe un hilo de Twitter de 3 a 7 tweets. "
            "Cada tweet debe tener maximo 280 caracteres. "
            "Numera cada tweet (1/N, 2/N, etc.). "
            "Tweet 1: hook que genere curiosidad. "
            "Tweets intermedios: desarrollo con datos y argumentos. "
            "Ultimo tweet: conclusion + CTA. "
            "El hilo debe contar una narrativa coherente que funcione de principio a fin."
        ),
        "example_structure": "1/N Hook → 2/N-6/N Desarrollo → N/N Conclusion+CTA",
    },
    FormatoContenido.INFOGRAFIA_COPY: {
        "max_chars": 2000,
        "instruction": (
            "Escribe el texto para una infografia. "
            "Estructura: TITULO (maximo 10 palabras, impactante) → SUBTITULO → "
            "3-5 PUNTOS CLAVE (frase corta + dato) → FUENTE → CTA. "
            "Cada punto debe ser auto-explicativo en 1-2 lineas. "
            "Sugiere colores o iconografia que refuerce el mensaje."
        ),
        "example_structure": "Titulo → Subtitulo → Puntos clave → Fuente → CTA",
    },
    FormatoContenido.COMUNICADO: {
        "max_chars": 8000,
        "instruction": (
            "Escribe un comunicado de prensa formal. "
            "Estructura: ENCABEZADO (titulo noticioso) → LUGAR Y FECHA → "
            "PARRAFO DE APERTURA (5W: quien, que, cuando, donde, por que) → "
            "CUERPO (2-3 parrafos con contexto y detalles) → "
            "CITA TEXTUAL del dirigente (entrecomillada) → "
            "CIERRE (proximos pasos) → CONTACTO DE PRENSA. "
            "Tono institucional y profesional. Tercera persona."
        ),
        "example_structure": (
            "Encabezado → Lugar/Fecha → Apertura 5W → Cuerpo → Cita → Cierre → Contacto"
        ),
    },
}

# INE compliance disclaimer
_INE_DISCLAIMER = "\n\n---\n*Contenido generado con asistencia de Inteligencia Artificial.*"


# ── Context gathering ───────────────────────────────────────────────────


async def _gather_dirigente_context(db: AsyncSession, dirigente: Dirigente) -> dict:
    """Collect dirigente data for prompt context. Never invent data."""
    from app.models.social import SocialPost, SocialProfile

    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)

    # Social profiles summary
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

    # Recent top-performing post themes
    top_posts_result = await db.execute(
        select(SocialPost.content, SocialPost.engagement_rate, SocialPost.sentiment_score)
        .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
        .where(
            SocialProfile.dirigente_id == dirigente.id,
            SocialPost.published_at >= thirty_days_ago,
        )
        .order_by(SocialPost.engagement_rate.desc().nulls_last())
        .limit(5)
    )
    top_posts = [
        {
            "content_preview": row[0][:120] if row[0] else "",
            "engagement": round(float(row[1]), 4) if row[1] else 0.0,
            "sentiment": round(float(row[2]), 4) if row[2] else None,
        }
        for row in top_posts_result.all()
    ]

    return {
        "dirigente": {
            "nombre": dirigente.full_name,
            "cargo": dirigente.cargo,
            "partido": dirigente.partido,
            "estado": dirigente.estado,
            "municipio": dirigente.municipio,
        },
        "social_profiles": profiles_data,
        "top_performing_posts_30d": top_posts,
        "analysis_date": datetime.now(UTC).isoformat(),
    }


# ── Prompt building ─────────────────────────────────────────────────────


def _build_prompt(
    dirigente_context: dict,
    formato: FormatoContenido,
    tema: str,
    tono: str,
    plataforma_destino: str,
) -> tuple[str, str]:
    """Build system + user prompt pair for Claude.

    Returns (system_prompt, user_prompt).
    """
    constraints = _PLATFORM_CONSTRAINTS[formato]

    system_prompt = (
        "Eres un estratega de comunicacion politica mexicana con 15 anos de experiencia. "
        "Generas contenido digital para dirigentes del partido Movimiento Ciudadano (MC). "
        "Tu contenido es autentico, estrategico, y cumple con la normativa del INE. "
        "NUNCA generas contenido difamatorio, discriminatorio ni que incite violencia. "
        "NUNCA inventas datos, cifras o estadisticas que no esten en el contexto proporcionado. "
        "Si el periodo de veda electoral esta activo, lo indicas y ajustas el contenido."
    )

    context_json = json.dumps(dirigente_context, indent=2, ensure_ascii=False, default=str)

    user_prompt = f"""## TAREA
Genera contenido en formato: **{formato.value}**
Tema: **{tema}**
Tono: **{tono}**
Plataforma destino: **{plataforma_destino}**

## RESTRICCIONES DEL FORMATO
{constraints['instruction']}
Estructura sugerida: {constraints['example_structure']}
Maximo de caracteres: {constraints['max_chars']}

## CONTEXTO DEL DIRIGENTE (datos reales, NO inventes adicionales)
{context_json}

## TONO: {tono}
- "formal": lenguaje institucional, tercera persona donde aplique, sin coloquialismos
- "cercano": primera persona, empatico, accesible, como hablando con vecinos
- "urgente": directo, llamado a la accion, sentido de inmediatez
- "celebratorio": positivo, logros, agradecimiento, orgullo
- "informativo": datos, hechos, contexto, educativo

## REGLAS OBLIGATORIAS
1. El contenido DEBE reflejar el tono solicitado.
2. NUNCA inventes datos que no esten en el contexto.
3. El contenido debe ser apropiado para el contexto politico mexicano.
4. NO incluyas la etiqueta de IA al final — se anadira automaticamente.
5. Responde SOLO con el contenido final, sin explicaciones ni meta-comentarios.
"""

    if settings.VEDA_ELECTORAL_ACTIVE:
        user_prompt += (
            "\n## ALERTA: VEDA ELECTORAL ACTIVA\n"
            "El contenido NO debe incluir propaganda electoral, "
            "solicitud de voto, ni mencion de candidaturas. "
            "Solo informacion de gestion y servicio publico.\n"
        )

    return system_prompt, user_prompt


# ── Content generation (non-streaming) ──────────────────────────────────


class ContentFactory:
    """AI-powered political content generator — supports Claude and Ollama."""

    @staticmethod
    async def _generate_with_ollama(system_prompt: str, user_prompt: str) -> str:
        """Generate content using local Ollama instance."""
        combined = f"{system_prompt}\n\n{user_prompt}"
        async with httpx.AsyncClient(timeout=300.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": combined,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            return resp.json()["response"]

    @staticmethod
    async def _stream_with_ollama(
        system_prompt: str, user_prompt: str
    ) -> AsyncGenerator[str, None]:
        """Stream content generation using local Ollama instance."""
        combined = f"{system_prompt}\n\n{user_prompt}"
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": combined,
                    "stream": True,
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        chunk = json.loads(line)
                        if chunk.get("response"):
                            yield chunk["response"]

    @staticmethod
    async def generate(
        db: AsyncSession,
        dirigente_id: int,
        formato: FormatoContenido,
        tema: str,
        tono: str,
        plataforma_destino: str,
        user_id: int,
    ) -> ContenidoGenerado:
        """Generate content for a dirigente and persist it."""
        provider = settings.AI_PROVIDER

        # Load dirigente
        dirigente = await _load_dirigente(db, dirigente_id)

        # Gather context
        context = await _gather_dirigente_context(db, dirigente)

        # Build prompts
        system_prompt, user_prompt = _build_prompt(context, formato, tema, tono, plataforma_destino)
        full_prompt_for_audit = f"[SYSTEM]\n{system_prompt}\n\n[USER]\n{user_prompt}"

        if provider == "ollama":
            generated_text = await ContentFactory._generate_with_ollama(system_prompt, user_prompt)
            model_name = f"ollama/{settings.OLLAMA_MODEL}"
            tokens_in, tokens_out = 0, 0
        else:
            if not settings.CLAUDE_API_KEY:
                raise ValueError("CLAUDE_API_KEY no configurada y AI_PROVIDER=claude.")
            import anthropic
            client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
            message = client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            generated_text = message.content[0].text
            model_name = settings.CLAUDE_MODEL
            tokens_in = message.usage.input_tokens
            tokens_out = message.usage.output_tokens

        # Append INE disclaimer
        final_content = generated_text + _INE_DISCLAIMER

        # Persist
        contenido = ContenidoGenerado(
            dirigente_id=dirigente_id,
            generado_por_id=user_id,
            org_id=dirigente.org_id,
            formato=formato,
            tema=tema,
            tono=tono,
            contenido=final_content,
            prompt_usado=full_prompt_for_audit,
            plataforma_destino=plataforma_destino,
            estado=EstadoContenido.BORRADOR,
            modelo_ia=model_name,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            etiqueta_ia=True,
        )
        db.add(contenido)
        await db.flush()
        await db.refresh(contenido)

        logger.info(
            "Content generated: id=%d dirigente=%s formato=%s provider=%s",
            contenido.id, dirigente.full_name, formato.value, provider,
        )
        return contenido

    @staticmethod
    async def generate_stream(
        db: AsyncSession,
        dirigente_id: int,
        formato: FormatoContenido,
        tema: str,
        tono: str,
        plataforma_destino: str,
        user_id: int,
    ) -> AsyncGenerator[str, None]:
        """Stream content generation via SSE-compatible chunks."""
        provider = settings.AI_PROVIDER

        # Load dirigente
        dirigente = await _load_dirigente(db, dirigente_id)

        # Gather context
        context = await _gather_dirigente_context(db, dirigente)

        # Build prompts
        system_prompt, user_prompt = _build_prompt(context, formato, tema, tono, plataforma_destino)
        full_prompt_for_audit = f"[SYSTEM]\n{system_prompt}\n\n[USER]\n{user_prompt}"

        collected_text = ""
        tokens_in, tokens_out = 0, 0

        if provider == "ollama":
            model_name = f"ollama/{settings.OLLAMA_MODEL}"
            async for chunk in ContentFactory._stream_with_ollama(system_prompt, user_prompt):
                collected_text += chunk
                yield json.dumps({"type": "chunk", "content": chunk})
        else:
            if not settings.CLAUDE_API_KEY:
                yield json.dumps({"type": "error", "message": "CLAUDE_API_KEY no configurada."})
                return
            import anthropic
            client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
            model_name = settings.CLAUDE_MODEL
            with client.messages.stream(
                model=settings.CLAUDE_MODEL,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            ) as stream:
                for text in stream.text_stream:
                    collected_text += text
                    yield json.dumps({"type": "chunk", "content": text})
                final_message = stream.get_final_message()
                tokens_in = final_message.usage.input_tokens
                tokens_out = final_message.usage.output_tokens

        # Append INE disclaimer
        final_content = collected_text + _INE_DISCLAIMER

        # Persist
        contenido = ContenidoGenerado(
            dirigente_id=dirigente_id,
            generado_por_id=user_id,
            org_id=dirigente.org_id,
            formato=formato,
            tema=tema,
            tono=tono,
            contenido=final_content,
            prompt_usado=full_prompt_for_audit,
            plataforma_destino=plataforma_destino,
            estado=EstadoContenido.BORRADOR,
            modelo_ia=model_name,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            etiqueta_ia=True,
        )
        db.add(contenido)
        await db.flush()
        await db.refresh(contenido)

        logger.info(
            "Content streamed: id=%d dirigente=%s formato=%s provider=%s",
            contenido.id, dirigente.full_name, formato.value, provider,
        )
        yield json.dumps({"type": "complete", "contenido_id": contenido.id})

    @staticmethod
    async def list_temas_sugeridos(
        db: AsyncSession,
        dirigente_id: int,
    ) -> list[dict[str, object]]:
        """Suggest content topics based on recent posts, sentiment, and ciudadano reports.

        Returns a list of dicts with keys: tema, relevancia_score, fuente.
        """
        from app.models.social import SocialPost, SocialProfile

        # Ensure the dirigente exists
        await _load_dirigente(db, dirigente_id)

        temas: list[dict[str, object]] = []
        thirty_days_ago = datetime.now(UTC) - timedelta(days=30)

        # 1. Topics from high-engagement posts (what resonates with audience)
        top_posts_result = await db.execute(
            select(SocialPost.content, SocialPost.engagement_rate)
            .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
            .where(
                SocialProfile.dirigente_id == dirigente_id,
                SocialPost.published_at >= thirty_days_ago,
                SocialPost.content.is_not(None),
            )
            .order_by(SocialPost.engagement_rate.desc().nulls_last())
            .limit(3)
        )
        for row in top_posts_result.all():
            content_preview = row[0][:80] if row[0] else ""
            engagement = float(row[1]) if row[1] else 0.0
            if content_preview:
                temas.append({
                    "tema": f"Seguimiento: {content_preview}...",
                    "relevancia_score": min(1.0, engagement * 10),
                    "fuente": "engagement_alto",
                })

        # 2. Topics from negative sentiment (issues to address)
        from app.models.social import SentimentAnalysis

        negative_result = await db.execute(
            select(SocialPost.content, SocialPost.sentiment_score)
            .join(SocialProfile, SocialPost.profile_id == SocialProfile.id)
            .where(
                SocialProfile.dirigente_id == dirigente_id,
                SocialPost.published_at >= thirty_days_ago,
                SocialPost.sentiment_score < -0.3,
                SocialPost.content.is_not(None),
            )
            .order_by(SocialPost.sentiment_score.asc())
            .limit(2)
        )
        for row in negative_result.all():
            content_preview = row[0][:80] if row[0] else ""
            if content_preview:
                temas.append({
                    "tema": f"Respuesta a critica: {content_preview}...",
                    "relevancia_score": 0.8,
                    "fuente": "sentimiento_negativo",
                })

        # 3. Topics from ciudadano reports (constituent concerns)
        try:
            from app.models.ciudadano import Ciudadano

            ciudadano_result = await db.execute(
                select(Ciudadano.problematica, func.count(Ciudadano.id))
                .where(
                    Ciudadano.dirigente_id == dirigente_id,
                    Ciudadano.problematica.is_not(None),
                    Ciudadano.created_at >= thirty_days_ago,
                )
                .group_by(Ciudadano.problematica)
                .order_by(func.count(Ciudadano.id).desc())
                .limit(3)
            )
            for row in ciudadano_result.all():
                if row[0]:
                    count = int(row[1])
                    temas.append({
                        "tema": f"Atencion ciudadana: {row[0]}",
                        "relevancia_score": min(1.0, count / 10),
                        "fuente": "ciudadanos",
                    })
        except Exception:
            # Ciudadano model may have different schema; gracefully skip
            logger.debug("Could not query ciudadano problematicas for topic suggestions")

        # 4. Default evergreen topics if nothing else available
        if not temas:
            temas = [
                {
                    "tema": "Rendicion de cuentas: logros del mes",
                    "relevancia_score": 0.6,
                    "fuente": "evergreen",
                },
                {
                    "tema": "Agenda legislativa y propuestas activas",
                    "relevancia_score": 0.5,
                    "fuente": "evergreen",
                },
                {
                    "tema": "Compromiso con la comunidad y participacion ciudadana",
                    "relevancia_score": 0.5,
                    "fuente": "evergreen",
                },
            ]

        # Sort by relevancia_score descending
        temas.sort(key=lambda t: t["relevancia_score"], reverse=True)
        return temas


# ── Helpers ─────────────────────────────────────────────────────────────


async def _load_dirigente(db: AsyncSession, dirigente_id: int) -> Dirigente:
    """Load a dirigente by ID or raise LookupError."""
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise LookupError(f"Dirigente with id={dirigente_id} not found")
    return dirigente
