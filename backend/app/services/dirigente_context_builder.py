"""dirigente_context_builder — recopila contexto BD del dirigente para enriquecer prompts IA.

Origen: Feature 2 sprint 2026-05-17 · CEO: "afinar menú IA a características particulares
de cada actor + coherencia de resultados".

Construye un dict compacto inyectable a prompts Groq/Gemini/CC que contiene:
  - metadata: cargo, partido, estado, municipio, rol_político, perfil
  - tono_dominante: tono más frecuente en últimos 30d posts (con %)
  - target_dominante: si habla más oficialismo / oposición / propio / personal
  - posts_recientes_muestra: 2-3 posts recientes (snippet) para que LLM vea cómo escribe
  - promesas_activas: pendientes con fecha compromiso (max 3)
  - efemerides_proximas: del mes actual + siguiente (max 5, ordenadas viralidad)

NO usa LLM para construir el contexto — solo SQL + heurísticas. Es input al prompt LLM,
no output del LLM. Determinista, barato, repetible.

Si una sección del contexto no tiene datos (ej. 0 promesas registradas), simplemente
no se incluye en el dict — el prompt resultante es más corto pero coherente.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.services.llm_sanitizer import sanitize_data_field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def build_context(
    db: AsyncSession,
    dirigente_id: int,
    *,
    ventana_dias: int = 30,
    max_promesas: int = 3,
    max_efemerides: int = 5,
    max_posts_muestra: int = 3,
    max_performance_posts: int = 3,
    min_classified_comments_for_perf: int = 10,
) -> dict[str, Any]:
    """Construye dict de contexto para inyectar al prompt LLM.

    Devuelve dict con claves opcionales (omitidas si la BD no tiene datos):
      metadata: {cargo, partido, estado, municipio, rol_politico, perfil_1_5}
      tono_dominante: {nombre, pct, total_clasificados}
      target_dominante: {nombre, pct}
      posts_recientes_muestra: list[{published_at, content_snippet, likes}]
      promesas_activas: list[{texto, fecha_compromiso}]
      efemerides_proximas: list[{titulo, fecha, viralidad, ideas_politicas}]
      performance_posts: {winners: [...], losers: [...]}  (Sprint E plan fans-dashboard)

    Args:
        ventana_dias: ventana para tono/target dominante + posts muestra (default 30)
        max_promesas: máximo promesas activas a incluir (default 3)
        max_efemerides: máximo efemérides próximas (default 5)
        max_posts_muestra: máximo posts crudos como muestra de estilo (default 3)
        max_performance_posts: máximo posts ganadores/negativos a incluir (default 3 c/u)
        min_classified_comments_for_perf: mínimo de comments con `nlp_tono` para incluir
            performance_posts (default 10 · R-6 plan: si BD tiene <10 muestras NLP,
            omitir sección entera para evitar señal ruidosa)
    """
    ctx: dict[str, Any] = {}

    # 1. Metadata del dirigente
    drow = (await db.execute(text("""
        SELECT cargo, partido, estado, municipio, rol_politico, perfil_1_5
        FROM dirigentes WHERE id = :did
    """), {"did": dirigente_id})).first()
    if drow:
        ctx["metadata"] = {
            "cargo": drow[0],
            "partido": drow[1],
            "estado": drow[2],
            "municipio": drow[3],
            "rol_politico": drow[4],
            "perfil": drow[5],
        }
    else:
        # Si el dirigente no existe, devolver dict vacío — el caller decide qué hacer
        return ctx

    # 2. Tono dominante (últimos N días)
    cutoff = datetime.now(UTC) - timedelta(days=ventana_dias)
    tono_rows = (await db.execute(text("""
        SELECT tono_discurso, COUNT(*) AS n
        FROM social_posts sp JOIN social_profiles sps ON sp.profile_id=sps.id
        WHERE sps.dirigente_id = :did
          AND sp.published_at >= :cutoff
          AND sp.tono_discurso IS NOT NULL
        GROUP BY tono_discurso
        ORDER BY n DESC
    """), {"did": dirigente_id, "cutoff": cutoff})).all()
    if tono_rows:
        total = sum(r[1] for r in tono_rows)
        ctx["tono_dominante"] = {
            "nombre": tono_rows[0][0],
            "pct": round(tono_rows[0][1] / total * 100, 1),
            "total_clasificados": total,
        }

    # 3. Target político dominante
    target_rows = (await db.execute(text("""
        SELECT target_politico, COUNT(*) AS n
        FROM social_posts sp JOIN social_profiles sps ON sp.profile_id=sps.id
        WHERE sps.dirigente_id = :did
          AND sp.published_at >= :cutoff
          AND sp.target_politico IS NOT NULL
        GROUP BY target_politico
        ORDER BY n DESC
    """), {"did": dirigente_id, "cutoff": cutoff})).all()
    if target_rows:
        total = sum(r[1] for r in target_rows)
        ctx["target_dominante"] = {
            "nombre": target_rows[0][0],
            "pct": round(target_rows[0][1] / total * 100, 1),
        }

    # 4. Posts recientes (muestra de estilo de escritura)
    posts = (await db.execute(text("""
        SELECT published_at, LEFT(content, 280) AS snippet, likes
        FROM social_posts sp JOIN social_profiles sps ON sp.profile_id=sps.id
        WHERE sps.dirigente_id = :did
          AND sp.content IS NOT NULL AND LENGTH(sp.content) > 30
        ORDER BY sp.published_at DESC
        LIMIT :n
    """), {"did": dirigente_id, "n": max_posts_muestra})).all()
    if posts:
        ctx["posts_recientes_muestra"] = [
            {
                "published_at": p[0].isoformat() if p[0] else None,
                "content_snippet": p[1],
                "likes": p[2],
            } for p in posts
        ]

    # 5. Promesas activas (pendientes)
    promesas = (await db.execute(text("""
        SELECT texto_promesa, fecha_compromiso
        FROM promesas_dirigente
        WHERE dirigente_id = :did AND estado = 'pendiente'
        ORDER BY fecha_compromiso ASC NULLS LAST
        LIMIT :n
    """), {"did": dirigente_id, "n": max_promesas})).all()
    if promesas:
        ctx["promesas_activas"] = [
            {
                "texto": p[0],
                "fecha_compromiso": p[1].isoformat() if p[1] else None,
            } for p in promesas
        ]

    # 6. Efemérides próximas (descarta las del mes actual ya pasadas)
    now = datetime.now(UTC)
    mes_actual = now.month
    dia_actual = now.day
    mes_siguiente = mes_actual + 1 if mes_actual < 12 else 1
    efems = (await db.execute(text("""
        SELECT titulo, mes, dia, viralidad::text, ideas_politicas, tipo::text
        FROM efemerides
        WHERE is_active = true
          AND (
            (mes = :m1 AND dia >= :dia_hoy)
            OR mes = :m2
          )
        ORDER BY
          mes, dia,
          CASE viralidad WHEN 'alta' THEN 1 WHEN 'media' THEN 2 ELSE 3 END
        LIMIT :n
    """), {"m1": mes_actual, "m2": mes_siguiente, "dia_hoy": dia_actual, "n": max_efemerides})).all()
    if efems:
        ctx["efemerides_proximas"] = [
            {
                "titulo": e[0],
                "fecha": f"{e[2]:02d}/{e[1]:02d}",
                "viralidad": e[3],
                "tipo": e[5],
                "ideas_politicas": e[4] or [],
            } for e in efems
        ]

    # 7. Performance posts — top winners + top losers (Sprint E PLAN-fans-dashboard)
    #
    # Score combina engagement (likes + n_comments × 2.5) × polaridad neta de comments.
    # Solo posts con >=2 comments clasificados (señal mínima por-post para no rankear
    # outliers de 1 solo comentario).
    #
    # R-6: si el dirigente tiene <min_classified_comments_for_perf comments con
    # nlp_tono en la ventana, omitir sección entera (muestra insuficiente).
    total_clasif = (await db.execute(text("""
        SELECT COUNT(*) FROM social_comments sc
        JOIN social_posts sp ON sc.parent_post_id = sp.id
        JOIN social_profiles sps ON sp.profile_id = sps.id
        WHERE sps.dirigente_id = :did
          AND sp.published_at >= :cutoff
          AND sc.nlp_tono IS NOT NULL
    """), {"did": dirigente_id, "cutoff": cutoff})).scalar() or 0

    if total_clasif >= min_classified_comments_for_perf:
        perf_sql = """
            SELECT
              sp.id,
              sp.published_at,
              LEFT(sp.content, 200) AS snippet,
              sp.likes,
              COUNT(sc.id) AS n_comments,
              AVG(sc.nlp_polaridad)::float AS avg_polaridad,
              (
                SELECT LEFT(sc2.content, 140)
                FROM social_comments sc2
                WHERE sc2.parent_post_id = sp.id
                  AND sc2.nlp_polaridad {op} 0
                  AND sc2.content IS NOT NULL
                ORDER BY sc2.nlp_polaridad {sample_order} NULLS LAST
                LIMIT 1
              ) AS sample_quote
            FROM social_posts sp
            JOIN social_profiles sps ON sp.profile_id = sps.id
            JOIN social_comments sc ON sc.parent_post_id = sp.id
            WHERE sps.dirigente_id = :did
              AND sp.published_at >= :cutoff
              AND sc.nlp_tono IS NOT NULL
              AND sp.content IS NOT NULL
            GROUP BY sp.id, sp.published_at, sp.content, sp.likes
            HAVING COUNT(sc.id) >= 2 AND AVG(sc.nlp_polaridad) {op} 0
            ORDER BY (COALESCE(sp.likes, 0) + COUNT(sc.id) * 2.5)
                     * ABS(AVG(sc.nlp_polaridad)) DESC
            LIMIT :n
        """
        winners = (await db.execute(
            text(perf_sql.format(op=">", sample_order="DESC")),
            {"did": dirigente_id, "cutoff": cutoff, "n": max_performance_posts},
        )).all()
        losers = (await db.execute(
            text(perf_sql.format(op="<", sample_order="ASC")),
            {"did": dirigente_id, "cutoff": cutoff, "n": max_performance_posts},
        )).all()

        if winners or losers:
            ctx["performance_posts"] = {
                "winners": [
                    {
                        "published_at": w[1].isoformat() if w[1] else None,
                        "snippet": w[2],
                        "likes": w[3] or 0,
                        "n_comments": w[4],
                        "avg_polaridad": round(w[5], 2) if w[5] is not None else 0.0,
                        "sample_quote_positive": w[6] or "",
                    } for w in winners
                ],
                "losers": [
                    {
                        "published_at": loser[1].isoformat() if loser[1] else None,
                        "snippet": loser[2],
                        "likes": loser[3] or 0,
                        "n_comments": loser[4],
                        "avg_polaridad": round(loser[5], 2) if loser[5] is not None else 0.0,
                        "sample_quote_negative": loser[6] or "",
                    } for loser in losers
                ],
            }

    return ctx


def format_context_for_prompt(ctx: dict[str, Any]) -> str:
    """Convierte el dict de contexto en bloque de texto compacto para inyectar al prompt.

    Output ejemplo (Saymi):
        CONTEXTO DEL DIRIGENTE (BD CRECE, últimos 30 días):
        - Cargo: Secretaria de Turismo Oaxaca · Partido: MORENA · Estado: Oaxaca
        - Rol: oficialismo · Perfil: funcionario_gobierno
        - Tono dominante: neutral (82%) sobre 98 posts clasificados
        - Target predominante: propio (91%) — habla mayormente de su gestión
        - Posts recientes (muestra):
          [2026-05-14] "Acompañé al gobernador en gira..."
          [2026-05-13] "Promovemos la riqueza cultural..."
        - Promesas activas: ninguna registrada
        - Próximas efemérides (mayo-jun): Día del Maestro (15/05, alta) · ...

    Devuelve string vacío si el dict no tiene metadata (dirigente inexistente).
    """
    if "metadata" not in ctx:
        return ""

    lines = ["CONTEXTO DEL DIRIGENTE (BD CRECE, últimos 30 días):"]
    m = ctx["metadata"]

    # Línea 1: cargo · partido · estado · municipio
    linea1_parts = [f"Cargo: {m['cargo']}"]
    if m.get("partido"):
        linea1_parts.append(f"Partido: {m['partido']}")
    if m.get("estado"):
        linea1_parts.append(f"Estado: {m['estado']}")
    if m.get("municipio"):
        linea1_parts.append(f"Municipio: {m['municipio']}")
    lines.append("- " + " · ".join(linea1_parts))

    # Línea 2: rol + perfil (opcional)
    if m.get("rol_politico") or m.get("perfil"):
        rol_parts = []
        if m.get("rol_politico"):
            rol_parts.append(f"Rol: {m['rol_politico']}")
        if m.get("perfil"):
            rol_parts.append(f"Perfil: {m['perfil']}")
        lines.append("- " + " · ".join(rol_parts))

    # Tono dominante
    if "tono_dominante" in ctx:
        td = ctx["tono_dominante"]
        lines.append(
            f"- Tono dominante: {td['nombre']} ({td['pct']}%) "
            f"sobre {td['total_clasificados']} posts clasificados últimos 30d"
        )

    # Target dominante
    if "target_dominante" in ctx:
        tg = ctx["target_dominante"]
        target_descripcion = {
            "propio": "habla mayormente de su gestión / iniciativas propias",
            "personal": "comparte contenido personal / familiar",
            "oficialismo": "alinea con narrativa del gobierno",
            "oposicion": "critica al gobierno / oposición",
        }.get(tg["nombre"], "")
        suffix = f" — {target_descripcion}" if target_descripcion else ""
        lines.append(f"- Target predominante: {tg['nombre']} ({tg['pct']}%){suffix}")

    # Posts recientes
    if "posts_recientes_muestra" in ctx:
        lines.append("- Posts recientes (muestra de estilo):")
        for p in ctx["posts_recientes_muestra"]:
            fecha = p["published_at"][:10] if p["published_at"] else "?"
            # D11 (2026-05-19) · PII stripping LFPDPPP antes de LLM
            snippet = sanitize_data_field(
                p["content_snippet"].replace("\n", " "), max_length=200
            )
            lines.append(f"  [{fecha}] \"{snippet}\"")

    # Promesas activas
    if "promesas_activas" in ctx:
        lines.append("- Promesas activas pendientes:")
        for pr in ctx["promesas_activas"]:
            fecha = f" (compromiso {pr['fecha_compromiso']})" if pr["fecha_compromiso"] else ""
            lines.append(f"  · {pr['texto']}{fecha}")
    else:
        lines.append("- Promesas activas: ninguna registrada en BD")

    # Efemérides próximas
    if "efemerides_proximas" in ctx:
        ef_strs = []
        for e in ctx["efemerides_proximas"]:
            viralidad_marker = "⭐" if e["viralidad"] == "alta" else ""
            ef_strs.append(f"{e['titulo']} ({e['fecha']}){viralidad_marker}")
        lines.append("- Próximas efemérides relevantes: " + " · ".join(ef_strs))

    # Performance posts (Sprint E plan fans-dashboard)
    if "performance_posts" in ctx:
        perf = ctx["performance_posts"]
        if perf.get("winners"):
            lines.append("- Posts de mejor desempeño (alto engagement + polaridad positiva):")
            for w in perf["winners"]:
                fecha = w["published_at"][:10] if w["published_at"] else "?"
                snippet = sanitize_data_field(
                    w["snippet"].replace("\n", " "), max_length=140
                )
                lines.append(
                    f"  [{fecha}] \"{snippet}\" → {w['likes']} likes, "
                    f"{w['n_comments']} comments, polaridad +{w['avg_polaridad']}"
                )
                if w.get("sample_quote_positive"):
                    q = sanitize_data_field(
                        w["sample_quote_positive"].replace("\n", " "), max_length=200
                    )
                    lines.append(f"    Comentario representativo: \"{q}\"")
        if perf.get("losers"):
            lines.append("- Posts que generaron crítica (alto engagement pero polaridad negativa):")
            for loser in perf["losers"]:
                fecha = loser["published_at"][:10] if loser["published_at"] else "?"
                snippet = sanitize_data_field(
                    loser["snippet"].replace("\n", " "), max_length=140
                )
                lines.append(
                    f"  [{fecha}] \"{snippet}\" → {loser['likes']} likes, "
                    f"{loser['n_comments']} comments, polaridad {loser['avg_polaridad']}"
                )
                if loser.get("sample_quote_negative"):
                    q = sanitize_data_field(
                        loser["sample_quote_negative"].replace("\n", " "), max_length=200
                    )
                    lines.append(f"    Crítica representativa: \"{q}\"")

    return "\n".join(lines)
