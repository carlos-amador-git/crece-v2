"""Calendario de efemérides — endpoints.

GET /calendario/proximas?days=30 — efemerides próximas en la ventana
POST /calendario/sugerir-post     — genera draft de post via Claude API

D-CALENDARIO-1 (2026-05-12).
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.dirigente import Dirigente
from app.models.efemeride import Efemeride
from app.models.user import User

logger = logging.getLogger(__name__)


PLATFORM_SPECS = {
    "FACEBOOK": {"limite_chars": 2000, "emoji_ok": True, "tono": "conversacional, hashtags moderados"},
    "INSTAGRAM": {"limite_chars": 2200, "emoji_ok": True, "tono": "visual, hashtags abundantes (~10)"},
    "TWITTER": {"limite_chars": 280, "emoji_ok": True, "tono": "punzante, 1-2 hashtags"},
    "TIKTOK": {"limite_chars": 2200, "emoji_ok": True, "tono": "guion para video, hook 3s"},
    "YOUTUBE": {"limite_chars": 5000, "emoji_ok": False, "tono": "descripción larga, links"},
}

router = APIRouter()


# ============================================================================
# Schemas
# ============================================================================


class EfemerideOut(BaseModel):
    id: int
    mes: int
    dia: int
    titulo: str
    tipo: str
    descripcion: str | None
    ideas_politicas: list[str]
    viralidad: str
    ambito: str
    # campos calculados
    dias_hasta: int = Field(..., description="Días desde hoy hasta la próxima ocurrencia")
    fecha_proxima: date = Field(..., description="Fecha exacta de la próxima ocurrencia")


# ============================================================================
# Helpers
# ============================================================================


def _next_occurrence(mes: int, dia: int, today: date | None = None) -> date:
    """Devuelve la próxima ocurrencia de mes/dia >= hoy.

    Para fechas con día 29-Feb que caen en años no bisiestos se mapea a 28-Feb.
    """
    if today is None:
        today = date.today()
    # Ajuste 29-feb en año no bisiesto → 28
    try:
        candidate = date(today.year, mes, dia)
    except ValueError:
        # 29-feb año no bisiesto: ir a 28
        candidate = date(today.year, mes, 28) if mes == 2 else date(today.year, mes, 1)
    if candidate < today:
        try:
            candidate = date(today.year + 1, mes, dia)
        except ValueError:
            candidate = date(today.year + 1, mes, 28) if mes == 2 else date(today.year + 1, mes, 1)
    return candidate


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/proximas", response_model=list[EfemerideOut])
async def proximas(
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    viralidad_minima: Annotated[str | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EfemerideOut]:
    """Devuelve efemerides próximas en la ventana [hoy, hoy+days].

    Filtros:
        days: ventana en días (default 30, max 365)
        viralidad_minima: 'baja'|'media'|'alta' (filtra >= ese nivel)

    Auth: JWT obligatoria (todos los roles).
    """
    today = date.today()
    horizon = today + timedelta(days=days)

    # Cargar todas las activas; evaluación de fecha es per-row (Python)
    stmt = select(Efemeride).where(Efemeride.is_active.is_(True))
    if viralidad_minima:
        # alta > media > baja → si pide >= media, excluir baja
        if viralidad_minima == "alta":
            stmt = stmt.where(Efemeride.viralidad == "alta")
        elif viralidad_minima == "media":
            stmt = stmt.where(Efemeride.viralidad.in_(["alta", "media"]))
        # baja: sin filtro adicional

    result = await db.execute(stmt)
    efemerides = list(result.scalars().all())

    out: list[EfemerideOut] = []
    for ef in efemerides:
        proxima = _next_occurrence(ef.mes, ef.dia, today)
        if proxima > horizon:
            continue
        out.append(
            EfemerideOut(
                id=ef.id,
                mes=ef.mes,
                dia=ef.dia,
                titulo=ef.titulo,
                tipo=ef.tipo.value if hasattr(ef.tipo, "value") else str(ef.tipo),
                descripcion=ef.descripcion,
                ideas_politicas=list(ef.ideas_politicas or []),
                viralidad=ef.viralidad.value if hasattr(ef.viralidad, "value") else str(ef.viralidad),
                ambito=ef.ambito.value if hasattr(ef.ambito, "value") else str(ef.ambito),
                dias_hasta=(proxima - today).days,
                fecha_proxima=proxima,
            )
        )

    out.sort(key=lambda x: x.dias_hasta)
    return out


# ============================================================================
# Sugerir post (LLM)
# ============================================================================


class SugerirPostRequest(BaseModel):
    efemeride_id: int
    dirigente_id: int
    plataforma: str = Field(..., description="FACEBOOK · INSTAGRAM · TWITTER · TIKTOK · YOUTUBE")


class SugerirPostResponse(BaseModel):
    efemeride_titulo: str
    dirigente_full_name: str
    plataforma: str
    contenido: str
    hashtags: list[str]
    fuente: str = Field(..., description="claude_api | plantilla_fallback")
    aviso: str | None = None


def _build_prompt_efemeride(
    *,
    efemeride: Efemeride,
    dirigente: Dirigente,
    plataforma: str,
) -> str:
    spec = PLATFORM_SPECS.get(plataforma.upper(), PLATFORM_SPECS["FACEBOOK"])
    ideas = ", ".join(efemeride.ideas_politicas or [])
    return f"""Eres un estratega de comunicación política digital mexicano.
Genera UN post listo para publicar para la siguiente fecha conmemorativa.

## EFEMÉRIDE
- Fecha: {efemeride.dia:02d}/{efemeride.mes:02d}
- Título: {efemeride.titulo}
- Tipo: {efemeride.tipo.value if hasattr(efemeride.tipo, 'value') else efemeride.tipo}
- Ámbito: {efemeride.ambito.value if hasattr(efemeride.ambito, 'value') else efemeride.ambito}
- Ideas políticas sugeridas: {ideas}

## DIRIGENTE
- Nombre: {dirigente.full_name}
- Cargo: {dirigente.cargo}
- Partido: {dirigente.partido}
- Estado: {dirigente.estado}

## PLATAFORMA: {plataforma.upper()}
- Límite caracteres: {spec['limite_chars']}
- Estilo: {spec['tono']}
- Emoji: {'sí' if spec['emoji_ok'] else 'no'}

## REGLAS
1. NO inventes datos del dirigente (no programas, no cifras, no eventos).
2. Tono cálido, primera persona si aplica, evitar jerga oficial.
3. Respeta el límite de caracteres de la plataforma.
4. Incluye 2-5 hashtags relevantes.
5. El post debe ser PUBLICABLE tal cual, sin placeholders tipo [TU CIUDAD].

## RESPUESTA
Devuelve EXCLUSIVAMENTE un JSON válido (sin markdown):
{{"contenido": "texto del post", "hashtags": ["#tag1", "#tag2"]}}
"""


def _plantilla_fallback(
    efemeride: Efemeride,
    dirigente: Dirigente,
    plataforma: str,
) -> tuple[str, list[str]]:
    """Draft cuando no hay Claude API key. Plantilla honesta, marcada."""
    titulo = efemeride.titulo
    nombre = dirigente.full_name.split()[0]
    ideas = efemeride.ideas_politicas or []
    primer_idea = ideas[0] if ideas else "este tema"

    if plataforma.upper() == "TWITTER":
        contenido = (
            f"Hoy es el {titulo}. Desde {dirigente.estado}, refrendo mi compromiso "
            f"con {primer_idea}."
        )
    else:
        contenido = (
            f"Hoy conmemoramos el {titulo}.\n\n"
            f"Como {dirigente.cargo}, mi compromiso con {primer_idea} es firme. "
            f"Las y los mexicanos merecemos un país donde {ideas[0] if ideas else 'la dignidad'} "
            f"sea una prioridad.\n\n"
            f"— {nombre}"
        )
    hashtags = [
        f"#{titulo.replace(' ', '').replace('Día', '').replace('de', '').replace('la', '')[:25]}",
        "#México",
    ]
    return contenido, hashtags[:5]


async def _llamar_claude(
    *,
    efemeride: Efemeride,
    dirigente: Dirigente,
    plataforma: str,
) -> tuple[str, list[str]]:
    """Llama Claude API. Lanza si falla."""
    import anthropic

    prompt = _build_prompt_efemeride(
        efemeride=efemeride, dirigente=dirigente, plataforma=plataforma
    )
    client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
    message = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if len(lines) > 2 else raw
    data = json.loads(raw)
    return data["contenido"], list(data.get("hashtags", []))


@router.post("/sugerir-post", response_model=SugerirPostResponse)
async def sugerir_post(
    body: SugerirPostRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SugerirPostResponse:
    """Genera draft de post para una efeméride + dirigente + plataforma.

    Si CLAUDE_API_KEY está vacía, devuelve plantilla fallback con aviso.
    """
    # Load efeméride
    ef_result = await db.execute(
        select(Efemeride).where(Efemeride.id == body.efemeride_id, Efemeride.is_active.is_(True))
    )
    efemeride = ef_result.scalar_one_or_none()
    if efemeride is None:
        raise HTTPException(status_code=404, detail=f"Efeméride {body.efemeride_id} no encontrada")

    # Load dirigente (scoped por org del user, salvo admin)
    d_stmt = select(Dirigente).where(Dirigente.id == body.dirigente_id)
    if current_user.role != "admin" and current_user.org_id is not None:
        d_stmt = d_stmt.where(
            or_(Dirigente.org_id == current_user.org_id, Dirigente.org_id.is_(None))
        )
    d_result = await db.execute(d_stmt)
    dirigente = d_result.scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=404, detail=f"Dirigente {body.dirigente_id} no encontrado")

    plat_upper = body.plataforma.upper()
    if plat_upper not in PLATFORM_SPECS:
        raise HTTPException(
            status_code=400,
            detail=f"Plataforma inválida. Use: {list(PLATFORM_SPECS.keys())}",
        )

    # Intentar Claude si hay key; si no, plantilla fallback
    has_key = bool(settings.CLAUDE_API_KEY and not settings.CLAUDE_API_KEY.startswith("#"))
    fuente = "plantilla_fallback"
    aviso: str | None = None
    contenido: str
    hashtags: list[str]

    if has_key:
        try:
            contenido, hashtags = await _llamar_claude(
                efemeride=efemeride, dirigente=dirigente, plataforma=plat_upper
            )
            fuente = "claude_api"
        except Exception as exc:  # pragma: no cover
            logger.warning("Claude API falló, fallback a plantilla: %s", exc)
            contenido, hashtags = _plantilla_fallback(efemeride, dirigente, plat_upper)
            aviso = f"Claude API falló ({type(exc).__name__}); generado con plantilla."
    else:
        contenido, hashtags = _plantilla_fallback(efemeride, dirigente, plat_upper)
        aviso = (
            "CLAUDE_API_KEY no configurada en backend. Generado con plantilla genérica. "
            "Configura la key para drafts con LLM real (D-CALENDARIO-1)."
        )

    # TODO: persistir en contenidos_generados + ia_content_registry cuando esté el flujo
    # de aprobación definido (HITL). Por ahora devolver draft directo.

    return SugerirPostResponse(
        efemeride_titulo=efemeride.titulo,
        dirigente_full_name=dirigente.full_name,
        plataforma=plat_upper,
        contenido=contenido,
        hashtags=hashtags,
        fuente=fuente,
        aviso=aviso,
    )


# ============================================================================
# Convertir efeméride → recomendación (Opción 4 · 2026-05-12)
# Cierra el gap "catálogo pasivo → acción accionable" dentro de
# /dashboard/recomendaciones sin duplicar la página /dashboard/calendario.
# ============================================================================


class ConvertirRequest(BaseModel):
    dirigente_id: int = Field(..., description="Target dirigente")
    plan_ia_id: int | None = Field(None, description="Vincular a Plan IA (opcional)")


class ConvertirResponse(BaseModel):
    recomendacion_id: int
    estado: str
    mensaje: str


@router.post(
    "/efemerides/{efemeride_id}/convertir-recomendacion",
    response_model=ConvertirResponse,
    status_code=status.HTTP_201_CREATED,
)
async def convertir_efemeride_a_recomendacion(
    efemeride_id: int,
    body: ConvertirRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ConvertirResponse:
    """Convierte una efeméride del catálogo en una recomendación accionable
    para el dirigente target. Estado inicial='propuesta' (admin debe aprobar
    antes de que el cliente la vea, salvo que el caller sea admin).

    - **viewer** ve sólo recomendaciones aprobadas; usar UI admin para aprobar.
    - **admin/analyst** puede convertir + dejar en 'propuesta' para curaduría
      manual del texto.
    """
    from sqlalchemy import text as sa_text

    if current_user.role not in ("admin", "analyst", "editor"):
        raise HTTPException(status_code=403, detail="Sin permiso para convertir efemérides")

    efemeride = (
        await db.execute(select(Efemeride).where(Efemeride.id == efemeride_id))
    ).scalar_one_or_none()
    if efemeride is None:
        raise HTTPException(status_code=404, detail="Efeméride no encontrada")

    dirigente = (
        await db.execute(select(Dirigente).where(Dirigente.id == body.dirigente_id))
    ).scalar_one_or_none()
    if dirigente is None:
        raise HTTPException(status_code=404, detail="Dirigente no encontrado")

    if current_user.role != "admin" and dirigente.org_id != current_user.org_id:
        raise HTTPException(status_code=403, detail="Dirigente fuera de tu organización")

    fecha = _next_occurrence(efemeride.mes, efemeride.dia)
    accion = (
        f"📅 {efemeride.titulo} ({fecha.isoformat()}) — viralidad {efemeride.viralidad}.\n\n"
        f"Generar post para redes activas del dirigente alineado a la efeméride.\n"
        f"Ideas eje: {', '.join(efemeride.ideas_politicas or []) or '—'}."
    )

    ventana_ini = fecha - timedelta(days=1)
    ventana_fin = fecha
    duracion = max(1, (ventana_fin - ventana_ini).days)

    criterio = {
        "tipo": "engagement",
        "objetivo_relativo": "≥ promedio últimos 7 posts",
        "viralidad_referencia": efemeride.viralidad,
    }
    evidencia = {
        "efemeride_id": efemeride.id,
        "efemeride_titulo": efemeride.titulo,
        "fecha_proxima": fecha.isoformat(),
        "ambito": efemeride.ambito,
        "fuente": "convertir-recomendacion · D-CALENDARIO-1",
    }

    result = await db.execute(
        sa_text(
            """
            INSERT INTO recomendaciones_plan_ia
                (plan_ia_id, dirigente_id, org_id, tipo, accion_texto,
                 ventana_inicio, ventana_fin, ventana_duracion_dias,
                 criterio_exito, principio_conductual, evidencia_respaldo,
                 estado, created_at, updated_at)
            VALUES (:plan_id, :did, :org, 'start', :accion,
                    :ini, :fin, :dur,
                    CAST(:crit AS JSONB),
                    'Calendar Anchor — efeméride contextual',
                    CAST(:evid AS JSONB),
                    'propuesta', NOW(), NOW())
            RETURNING id
            """
        ),
        {
            "plan_id": body.plan_ia_id,
            "did": body.dirigente_id,
            "org": dirigente.org_id,
            "accion": accion,
            "ini": ventana_ini,
            "fin": ventana_fin,
            "dur": duracion,
            "crit": json.dumps(criterio),
            "evid": json.dumps(evidencia),
        },
    )
    rec_id = result.scalar_one()
    await db.commit()

    return ConvertirResponse(
        recomendacion_id=rec_id,
        estado="propuesta",
        mensaje=f"Recomendación creada · revisa y aprueba en panel admin.",
    )
