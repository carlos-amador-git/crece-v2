"""Divergencia CRECE sentiment vs encuestas públicas.

Compara la tendencia mensual de sentiment_politico_ajustado por ámbito
contra la aprobación del gobierno en encuestas públicas. Alerta si
divergencia > 30% — D-NLP-05 opción B.

Granularidad: ámbito (federal/CDMX/Oaxaca), NO por dirigente individual.
Rationale: las encuestas públicas miden aprobación de gobiernos, no de
diputados específicos. Si mi score político general diverge del humor
político capturado por Parametría/Oraculus, algo está mal.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


THRESHOLD_PCT = 30.0


async def compute_divergencia(
    db: AsyncSession,
    ambito: str,
    entidad: str | None = None,
    mes_referencia: date | None = None,
) -> dict:
    """Compute divergencia CRECE sentiment vs encuestas públicas para un ámbito.

    Returns:
        {
            "ambito": str,
            "entidad": str | None,
            "mes": str (YYYY-MM),
            "crece_score_avg": float (-1 to 1 scale normalized),
            "encuestas_score_avg": float (same scale),
            "divergencia_pct": float (0-100),
            "alert": bool (True if >30%),
            "n_posts": int,
            "n_encuestas": int,
            "sources_encuestas": list[str],
        }
    """
    if mes_referencia is None:
        today = date.today()
        mes_referencia = date(today.year, today.month, 1)

    mes_siguiente = date(
        mes_referencia.year + (mes_referencia.month // 12),
        (mes_referencia.month % 12) + 1,
        1,
    )

    # CRECE: avg sentimiento_politico_ajustado for dirigentes in this ambito
    # Map ambito + entidad → dirigente filter
    dirigente_filter = ""
    if ambito == "federal":
        dirigente_filter = "d.cargo ILIKE '%diputad%federal%' OR d.cargo ILIKE '%senador%'"
    elif ambito == "estatal" and entidad:
        dirigente_filter = f"d.estado = '{entidad}'"
    else:
        dirigente_filter = "1=1"

    crece_result = await db.execute(
        text(f"""
            SELECT AVG(p.sentimiento_politico_ajustado)::float AS avg_score, COUNT(*) AS n
            FROM social_posts p
            JOIN social_profiles sp ON p.profile_id = sp.id
            JOIN dirigentes d ON sp.dirigente_id = d.id
            WHERE p.published_at >= :mes_start AND p.published_at < :mes_end
              AND p.sentimiento_politico_ajustado IS NOT NULL
              AND ({dirigente_filter})
        """).bindparams(mes_start=mes_referencia, mes_end=mes_siguiente)
    )
    crece_row = crece_result.fetchone()
    crece_avg = crece_row[0]  # -1 to 1
    n_posts = crece_row[1] or 0

    # Encuestas: avg aprobación government for this ambito
    encuestas_result = await db.execute(
        text("""
            SELECT AVG(valor_pct)::float AS avg_pct, COUNT(*) AS n,
                   array_agg(DISTINCT fuente) AS sources
            FROM encuestas_publicas
            WHERE fecha_publicacion >= :mes_start AND fecha_publicacion < :mes_end
              AND ambito = :ambito
              AND (entidad = :entidad OR (:entidad IS NULL AND entidad IS NULL))
              AND metrica IN ('aprobacion', 'aprobacion_gobierno')
              AND actor_tipo = 'gobierno'
        """).bindparams(
            mes_start=mes_referencia, mes_end=mes_siguiente,
            ambito=ambito, entidad=entidad,
        )
    )
    enc_row = encuestas_result.fetchone()
    enc_pct = enc_row[0]  # 0-100
    n_encuestas = enc_row[1] or 0
    sources = enc_row[2] or []

    # Normalize both to -1..1
    # Encuesta aprobación: 50% = 0, 100% = +1, 0% = -1
    enc_normalized = (enc_pct - 50) / 50 if enc_pct is not None else None
    crece_normalized = crece_avg  # already -1..1 (sentimiento_politico_ajustado scale is actually -2..2, map to -1..1)

    if crece_normalized is not None:
        # Our score is -2..2 range, map to -1..1
        crece_normalized = max(-1.0, min(1.0, crece_normalized / 2))

    # Divergencia: abs difference as % of full range (range = 2)
    divergencia_pct = None
    alert = False
    if crece_normalized is not None and enc_normalized is not None:
        divergencia_pct = abs(crece_normalized - enc_normalized) / 2 * 100
        alert = divergencia_pct > THRESHOLD_PCT

    return {
        "ambito": ambito,
        "entidad": entidad,
        "mes": mes_referencia.strftime("%Y-%m"),
        "crece_score_avg": round(crece_normalized, 3) if crece_normalized is not None else None,
        "encuestas_score_avg": round(enc_normalized, 3) if enc_normalized is not None else None,
        "encuestas_aprobacion_pct": round(enc_pct, 1) if enc_pct is not None else None,
        "divergencia_pct": round(divergencia_pct, 1) if divergencia_pct is not None else None,
        "alert": alert,
        "threshold_pct": THRESHOLD_PCT,
        "n_posts": n_posts,
        "n_encuestas": n_encuestas,
        "sources_encuestas": sources,
    }
