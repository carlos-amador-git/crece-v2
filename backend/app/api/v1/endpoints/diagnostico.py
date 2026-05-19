"""Diagnóstico Tier 1 endpoints (Sprint S2 · MASTER §3.1 #01-#10).

Cada bloque expone un GET individual + un endpoint agregado que regresa los 10
en una sola llamada para consumo del dashboard de diagnóstico.

Auth: JWT obligatoria. ``org_id`` se extrae del user del JWT (admin puede
sobrescribir con header ``X-Org-Id``). No-admins solo ven dirigentes de su org.
"""
from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.diagnostico import (
    benchmark_service,
    breakout_service,
    crisis_spike_service,
    er_service,
    growth_attribution_service,
    humanizacion_service,
    matrix_2x2_service,
    sentiment_plutchik_service,
    share_like_ratio_service,
    sov_service,
)

router = APIRouter()


def _resolve_org_id(current_user: User, request: Request) -> int | None:
    """Return effective org_id. Admin can override via X-Org-Id header."""
    org_id = getattr(current_user, "org_id", None)
    if current_user.role == "admin":
        override = request.headers.get("x-org-id")
        if override and override.isdigit():
            return int(override)
    return org_id


@router.get("/{dirigente_id}/er_normalizado")
async def get_er_normalizado(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    dias_a_comicio: int | None = Query(None, ge=0, description="Días a próxima elección (activa modificador temporal D-19)"),
) -> dict:
    """B01 ER normalizado por estrato (matriz 5×5 + modificador temporal D-19)."""
    org_id = _resolve_org_id(current_user, request)
    return await er_service.compute(db, dirigente_id, org_id, dias_a_comicio=dias_a_comicio)


@router.get("/{dirigente_id}/breakout_scale")
async def get_breakout_scale(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B02 Breakout Scale Brookings (Cat 1-6)."""
    org_id = _resolve_org_id(current_user, request)
    return await breakout_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/matriz_2x2")
async def get_matriz_2x2(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B03 Matriz 2×2 de contenido (Insignia/Crisis/Vanidad/Muerta)."""
    org_id = _resolve_org_id(current_user, request)
    return await matrix_2x2_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/benchmark")
async def get_benchmark(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B04 Benchmark vs competidores directos (proxies D-22 en S2)."""
    org_id = _resolve_org_id(current_user, request)
    return await benchmark_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/sentiment_plutchik")
async def get_sentiment_plutchik(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B05 Sentiment Plutchik 6 emociones."""
    org_id = _resolve_org_id(current_user, request)
    return await sentiment_plutchik_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/crisis_spike")
async def get_crisis_spike(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B06 Crisis Spike detector (ventana móvil 2h vs baseline 7d)."""
    org_id = _resolve_org_id(current_user, request)
    return await crisis_spike_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/growth_attribution")
async def get_growth_attribution(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B07 Growth attribution Time-Decay (half-life 7d · ventana 14d)."""
    org_id = _resolve_org_id(current_user, request)
    return await growth_attribution_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/sov")
async def get_sov(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    topics: Annotated[list[str] | None, Query()] = None,
) -> dict:
    """B08 Share of Voice por tema clave (topics opcionales como filtro)."""
    org_id = _resolve_org_id(current_user, request)
    return await sov_service.compute(db, dirigente_id, org_id, topics=topics)


@router.get("/{dirigente_id}/share_like_ratio")
async def get_share_like_ratio(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B09 Share-to-Like Ratio (movilización profunda)."""
    org_id = _resolve_org_id(current_user, request)
    return await share_like_ratio_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/humanizacion")
async def get_humanizacion(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """B10 Humanización Score (léxica 0-100)."""
    org_id = _resolve_org_id(current_user, request)
    return await humanizacion_service.compute(db, dirigente_id, org_id)


@router.get("/{dirigente_id}/humanizacion/examples")
async def get_humanizacion_examples(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(5, ge=1, le=20, description="Posts por categoría (institucional/humanizante)"),
) -> dict:
    """B10 drill-down — top N posts más institucionales y más humanizantes.

    Devuelve los extremos del ranking de humanización para que el Plan IA S4
    pueda traducir el score en recomendaciones específicas accionables.

    Response:
        {
          "status": "ok",
          "top_institucional": [{post_id, content_preview, score, factores}],
          "top_humanizante": [{post_id, content_preview, score, factores}],
          "keywords_usadas": {primera_persona, emojis_humanos, institucional},
          "n_posts_analizados": int,
          "ventana_dias": int
        }
    """
    org_id = _resolve_org_id(current_user, request)
    return await humanizacion_service.get_examples(db, dirigente_id, org_id, limit=limit)


@router.get("/{dirigente_id}")
async def get_diagnostico_completo(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    dias_a_comicio: int | None = Query(None, ge=0),
) -> dict:
    """Endpoint agregado — devuelve los 10 bloques Tier 1 en 1 request.

    Ejecuta los 10 services en paralelo usando ``asyncio.gather`` sobre sesiones
    independientes NO, por simplicidad S2 se ejecutan secuencialmente sobre la
    misma session (cada service es I/O bound con la misma DB).
    """
    org_id = _resolve_org_id(current_user, request)

    # Secuencial — los services comparten session y son cortos. Evita contention DB.
    bloques = {
        "B01_er_normalizado": await er_service.compute(db, dirigente_id, org_id, dias_a_comicio=dias_a_comicio),
        "B02_breakout_scale": await breakout_service.compute(db, dirigente_id, org_id),
        "B03_matriz_2x2": await matrix_2x2_service.compute(db, dirigente_id, org_id),
        "B04_benchmark": await benchmark_service.compute(db, dirigente_id, org_id),
        "B05_sentiment_plutchik": await sentiment_plutchik_service.compute(db, dirigente_id, org_id),
        "B06_crisis_spike": await crisis_spike_service.compute(db, dirigente_id, org_id),
        "B07_growth_attribution": await growth_attribution_service.compute(db, dirigente_id, org_id),
        "B08_sov": await sov_service.compute(db, dirigente_id, org_id),
        "B09_share_like_ratio": await share_like_ratio_service.compute(db, dirigente_id, org_id),
        "B10_humanizacion": await humanizacion_service.compute(db, dirigente_id, org_id),
    }

    ok_count = sum(1 for v in bloques.values() if v.get("status") == "ok")
    insufficient_count = sum(1 for v in bloques.values() if v.get("status") == "insufficient_data")

    return {
        "dirigente_id": dirigente_id,
        "bloques": bloques,
        "resumen": {
            "ok": ok_count,
            "insufficient_data": insufficient_count,
            "total": len(bloques),
        },
        "bloque_version": "tier1-v1",
    }


# ──────────────────────────────────────────────────────────────────────────
# FODA · vista dedicada para que el dirigente lea su Fortalezas/Debilidades
# /Oportunidades/Amenazas en cuadrante 2×2.
#
# Lee el último DIAGNOSTICO de planes_ia y parsea el bloque ## FODA.
# ──────────────────────────────────────────────────────────────────────────
_FODA_HEADER_RE = re.compile(r"^#{2,4}\s*(?:\d+(?:[.)]\d+)?[.)]?\s*)?(Fortalezas|Oportunidades|Debilidades|Amenazas)\b", re.IGNORECASE)
_FODA_COMBINED_HEADER_RE = re.compile(
    r"^#{2,4}\s*(?:\d+(?:[.)]\d+)?[.)]?\s*)?(Fortalezas|Oportunidades|Debilidades|Amenazas)"
    r"\s+y\s+(Fortalezas|Oportunidades|Debilidades|Amenazas)\b",
    re.IGNORECASE,
)
_BULLET_RE = re.compile(r"^[-*]\s+(.*)$")
_FODA_SECTION_START_RE = re.compile(r"^#{1,4}\s*(?:\d+[.)]\s*)?(?:Análisis\s+)?FODA\b", re.IGNORECASE)
_TABLE_SEPARATOR_RE = re.compile(r"^\|\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")
_QUADRANT_NAMES = {"fortalezas", "oportunidades", "debilidades", "amenazas"}
_SECTION_KEY = {q: q for q in _QUADRANT_NAMES}
# Prefijo F1, O1, D1, A1, F-1, O-1, etc. en primera celda de tabla
_QUADRANT_PREFIX_RE = re.compile(r"^\*{0,2}\s*([FODA])-?(\d+)\s*\*{0,2}\s*$", re.IGNORECASE)
_PREFIX_TO_QUAD = {
    "F": "fortalezas",
    "O": "oportunidades",
    "D": "debilidades",
    "A": "amenazas",
}
# Header columns que indican formato 4-col (#|Hallazgo|Evidencia|Implicación)
_HEADER_HALLAZGO_RE = re.compile(r"^\*{0,2}\s*(hallazgo|oportunidad|amenaza|debilidad|fortaleza)\s*\*{0,2}", re.IGNORECASE)


def _strip_md_inline(text: str) -> str:
    """Quita ** y * de inline emphasis y normaliza espacios."""
    return re.sub(r"\*+", "", text).strip()


def _split_table_row(line: str) -> list[str]:
    """Devuelve celdas de una row markdown sin las pipes de borde."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _classify_cell(cell: str) -> str | None:
    """Si una celda de header es exactamente uno de los 4 cuadrantes, devuelve la key normalizada."""
    norm = _strip_md_inline(cell).lower()
    return norm if norm in _QUADRANT_NAMES else None


def _parse_foda(contenido: str) -> dict:
    """Parser markdown tolerante del bloque FODA del DIAGNOSTICO.

    Soporta:
    - Estilo bullet (Piña): `## FODA` con `### Fortalezas` y `- item`
    - Estilo tabla (Ballesteros): `### N. Análisis FODA` con tablas markdown
      `| **Fortalezas** | **Debilidades** |` + filas de celdas
    """
    out: dict[str, list[str]] = {
        "fortalezas": [],
        "oportunidades": [],
        "debilidades": [],
        "amenazas": [],
    }
    if not contenido:
        return out

    lines = contenido.splitlines()
    # Encuentra inicio del bloque FODA
    start = None
    for i, raw in enumerate(lines):
        if _FODA_SECTION_START_RE.match(raw.strip()):
            start = i + 1
            break
    if start is None:
        return out

    # Determina el final: siguiente heading del mismo o mayor nivel (no subheading)
    # `### N. FODA` → corta en `### M.` (M != el número actual) o en `## `
    end = len(lines)
    for j in range(start, len(lines)):
        s = lines[j].strip()
        if s.startswith("## ") and not _FODA_SECTION_START_RE.match(s):
            end = j
            break
        if s.startswith("### ") and not _FODA_SECTION_START_RE.match(s) and _FODA_HEADER_RE.match(s) is None:
            # otra subsección numerada (### 6. ...)
            end = j
            break

    block = lines[start:end]

    # Estado para modo tabla
    table_columns: list[str | None] | None = None  # mapping col_idx → quadrant key
    expecting_separator = False
    # Quadrant inferido por sección o header (formato 4-col: #|Hallazgo|Ev|Impl)
    section_quadrant: str | None = None

    # Estado para modo bullet
    current_bullet: str | None = None

    for raw in block:
        line = raw.rstrip()
        stripped = line.lstrip()

        # Detección heading combinado (#### 5.1 Fortalezas y Oportunidades)
        # → no fija un quadrant; deja que prefijos F1/O1 los discriminen
        hcomb = _FODA_COMBINED_HEADER_RE.match(stripped)
        if hcomb:
            section_quadrant = None
            current_bullet = None
            table_columns = None
            expecting_separator = False
            continue

        # Detección heading bullet o single-quadrant (### Fortalezas, #### 5.1 Amenazas)
        h = _FODA_HEADER_RE.match(stripped)
        if h:
            quad = _SECTION_KEY[h.group(1).lower()]
            current_bullet = quad
            section_quadrant = quad
            table_columns = None
            expecting_separator = False
            continue

        # Detección de tabla
        if stripped.startswith("|"):
            cells = _split_table_row(stripped)

            if expecting_separator and _TABLE_SEPARATOR_RE.match(stripped):
                expecting_separator = False
                continue

            # Header row 2-col con celdas Fortalezas|Debilidades
            mapped = [_classify_cell(c) for c in cells]
            quadrants_in_row = [m for m in mapped if m]
            if len(quadrants_in_row) >= 2:
                table_columns = mapped
                expecting_separator = True
                current_bullet = None
                continue

            # Header row formato 4-col: #|Hallazgo|Evidencia|Implicación
            # → setear modo prefijo (cada fila usa F1/O1 en col 0 para identificar)
            if any(_HEADER_HALLAZGO_RE.match(c) for c in cells):
                table_columns = None  # señaliza modo prefijo
                expecting_separator = True
                continue

            # Data row dentro de una tabla 2-col activa
            if table_columns is not None:
                for col_idx, cell_raw in enumerate(cells):
                    if col_idx >= len(table_columns):
                        break
                    quadrant = table_columns[col_idx]
                    if not quadrant:
                        continue
                    item = _strip_md_inline(cell_raw)
                    if item:
                        out[quadrant].append(item)
                continue

            # Data row formato 4-col: chequear prefijo F1/O1/D1/A1 en primera celda
            if cells:
                prefix_match = _QUADRANT_PREFIX_RE.match(cells[0])
                if prefix_match:
                    quad = _PREFIX_TO_QUAD[prefix_match.group(1).upper()]
                    # Concatenar resto de columnas como item
                    item = " — ".join(_strip_md_inline(c) for c in cells[1:] if _strip_md_inline(c))
                    if item:
                        out[quad].append(item)
                    continue

                # Si no tiene prefijo pero hay section_quadrant activo
                # → usar todo el row (skip "#" header de columna numérica)
                if section_quadrant and len(cells) >= 2:
                    item = " — ".join(_strip_md_inline(c) for c in cells if _strip_md_inline(c))
                    if item and not _HEADER_HALLAZGO_RE.match(cells[0] if cells else ""):
                        out[section_quadrant].append(item)
                    continue

            # pipe row sin contexto → ignorar
            continue

        # Si la línea está vacía o no es tabla, sale del modo tabla
        if not stripped:
            # mantén tabla activa por si vienen más rows tras blank line
            continue

        # Modo bullet
        if current_bullet is None:
            continue
        b = _BULLET_RE.match(stripped)
        if b:
            item = b.group(1).strip()
            if item:
                out[current_bullet].append(item)

    return out


@router.get("/foda/{dirigente_id}")
async def get_diagnostico_foda(
    dirigente_id: int,
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Devuelve el FODA estructurado del último DIAGNOSTICO del dirigente.

    Scope (Option A):
      - admin → cualquier dirigente
      - viewer con dirigente_id propio → solo SU dirigente
      - resto → cualquier dirigente de su org
    """
    # Scope check
    if current_user.role == "admin":
        pass
    elif current_user.role == "viewer" and current_user.dirigente_id and current_user.dirigente_id != dirigente_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sin acceso a este dirigente")

    sql = text("""
        SELECT id, contenido, created_at
          FROM planes_ia
         WHERE dirigente_id = :did AND tipo = 'DIAGNOSTICO'
         ORDER BY created_at DESC
         LIMIT 1
    """)
    row = (await db.execute(sql, {"did": dirigente_id})).first()
    if not row:
        return {
            "dirigente_id": dirigente_id,
            "fortalezas": [],
            "oportunidades": [],
            "debilidades": [],
            "amenazas": [],
            "diagnostico_id": None,
            "generado_at": None,
            "plan_derivado_id": None,
        }

    diag_id, contenido, created_at = row
    foda = _parse_foda(contenido or "")

    plan_sql = text("""
        SELECT id FROM planes_ia
         WHERE dirigente_id = :did AND tipo = 'CONSOLIDACION'
         ORDER BY created_at DESC LIMIT 1
    """)
    plan_row = (await db.execute(plan_sql, {"did": dirigente_id})).first()

    return {
        "dirigente_id": dirigente_id,
        "fortalezas": foda["fortalezas"],
        "oportunidades": foda["oportunidades"],
        "debilidades": foda["debilidades"],
        "amenazas": foda["amenazas"],
        "diagnostico_id": diag_id,
        "generado_at": created_at.isoformat() if created_at else None,
        "plan_derivado_id": plan_row[0] if plan_row else None,
    }
