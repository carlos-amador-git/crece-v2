"""Genera plan tipo DIAGNOSTICO por dirigente — FODA estructurado.

Cada DIAGNOSTICO consume data real de:
 - social_posts (framework posts clasificados + NLP v1)
 - social_profiles (plataformas + followers)
 - social_comments (IA scores cuando existen)

Produce markdown con FODA + KPI baseline + recomendaciones.
Idempotente: si ya existe DIAGNOSTICO para el dirigente, lo reemplaza.
"""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from app.core.database import async_session_factory


async def collect_data(session, dirigente_id: int) -> dict[str, Any]:
    row = (await session.execute(
        text("""
            SELECT id, full_name, cargo, partido, estado, rol_politico
            FROM dirigentes WHERE id = :id
        """),
        {"id": dirigente_id},
    )).first()
    if not row:
        return {}

    profiles = (await session.execute(
        text("""
            SELECT platform::text, handle, followers_count, posts_count,
                   data_source::text, last_manual_update
            FROM social_profiles
            WHERE dirigente_id = :id
            ORDER BY followers_count DESC
        """),
        {"id": dirigente_id},
    )).fetchall()

    posts_stats = (await session.execute(
        text("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE p.nlp_model_version = 'multi-model-v1') AS with_nlp,
                COUNT(*) FILTER (WHERE p.tono_discurso IS NOT NULL) AS with_framework,
                AVG(p.engagement_rate) FILTER (WHERE p.engagement_rate > 0) AS avg_eng_nonzero,
                AVG(p.sentimiento_politico_ajustado::float) FILTER (WHERE p.sentimiento_politico_ajustado IS NOT NULL) AS avg_sent_pol
            FROM social_posts p
            JOIN social_profiles sp ON sp.id = p.profile_id
            WHERE sp.dirigente_id = :id
        """),
        {"id": dirigente_id},
    )).first()

    tono_mix = (await session.execute(
        text("""
            SELECT p.tono_discurso, COUNT(*)
            FROM social_posts p
            JOIN social_profiles sp ON sp.id = p.profile_id
            WHERE sp.dirigente_id = :id AND p.tono_discurso IS NOT NULL
            GROUP BY p.tono_discurso
            ORDER BY 2 DESC
        """),
        {"id": dirigente_id},
    )).fetchall()

    target_mix = (await session.execute(
        text("""
            SELECT p.target_politico, COUNT(*)
            FROM social_posts p
            JOIN social_profiles sp ON sp.id = p.profile_id
            WHERE sp.dirigente_id = :id AND p.target_politico IS NOT NULL
            GROUP BY p.target_politico
            ORDER BY 2 DESC
        """),
        {"id": dirigente_id},
    )).fetchall()

    engagement_per_plat = (await session.execute(
        text("""
            SELECT sp.platform::text,
                   COUNT(p.id) AS posts,
                   AVG(p.engagement_rate) AS avg_eng,
                   AVG(p.comments::float) AS avg_comments
            FROM social_profiles sp
            LEFT JOIN social_posts p ON p.profile_id = sp.id
            WHERE sp.dirigente_id = :id
            GROUP BY sp.platform
        """),
        {"id": dirigente_id},
    )).fetchall()

    ia_data = (await session.execute(
        text("""
            SELECT COUNT(*) AS total,
                   COUNT(DISTINCT c.parent_post_id) AS posts_with_comments,
                   COUNT(*) FILTER (WHERE c.nlp_polaridad = 1) AS positive,
                   COUNT(*) FILTER (WHERE c.nlp_polaridad = -1) AS negative
            FROM social_comments c
            JOIN social_posts p ON p.id = c.parent_post_id
            JOIN social_profiles sp ON sp.id = p.profile_id
            WHERE sp.dirigente_id = :id
              AND c.nlp_model_version IS NOT NULL
        """),
        {"id": dirigente_id},
    )).first()

    return {
        "id": row[0],
        "full_name": row[1],
        "cargo": row[2],
        "partido": row[3],
        "estado": row[4],
        "rol_politico": row[5],
        "profiles": [
            {"platform": p[0], "handle": p[1], "followers": p[2], "posts": p[3],
             "data_source": p[4], "last_manual": p[5].isoformat() if p[5] else None}
            for p in profiles
        ],
        "total_posts": posts_stats[0] or 0,
        "with_nlp": posts_stats[1] or 0,
        "with_framework": posts_stats[2] or 0,
        "avg_eng_nonzero": float(posts_stats[3]) if posts_stats[3] else 0.0,
        "avg_sent_pol": float(posts_stats[4]) if posts_stats[4] else 0.0,
        "tono_mix": {t[0]: t[1] for t in tono_mix},
        "target_mix": {t[0]: t[1] for t in target_mix},
        "engagement_per_plat": {e[0]: {
            "posts": e[1], "avg_eng": float(e[2]) if e[2] else 0.0,
            "avg_comments": float(e[3]) if e[3] else 0.0,
        } for e in engagement_per_plat},
        "ia": {
            "total_comments": ia_data[0] or 0,
            "posts_con_ia": ia_data[1] or 0,
            "positive": ia_data[2] or 0,
            "negative": ia_data[3] or 0,
        },
    }


def build_foda(d: dict) -> dict:
    """Construye FODA grounded en data."""
    fortalezas = []
    debilidades = []
    oportunidades = []
    amenazas = []

    # Fortalezas — canales con engagement real
    canal_ganador = None
    max_eng = 0
    for plat, stats in d["engagement_per_plat"].items():
        if stats["avg_eng"] > max_eng and stats["posts"] > 5:
            max_eng = stats["avg_eng"]
            canal_ganador = plat
    if canal_ganador and max_eng > 1.0:
        fortalezas.append(
            f"Canal **{canal_ganador}** genera engagement real ({max_eng:.2f}%) — es el vehículo principal para escalar narrativa."
        )

    # Fortalezas — cobertura NLP + framework
    if d["with_nlp"] > 500:
        fortalezas.append(
            f"Cobertura NLP técnica sobre {d['with_nlp']} publicaciones — base sólida para detectar patrones y tendencias."
        )

    # Debilidades — canales con engagement=0 (bug scraper o audiencia dormida)
    dead_channels = [p for p, s in d["engagement_per_plat"].items() if s["avg_eng"] == 0 and s["posts"] > 10]
    if dead_channels:
        debilidades.append(
            f"Plataformas con engagement=0: {', '.join(dead_channels)}. Indica audiencia dormida o datos incompletos — validar scraper y replantear estrategia."
        )

    # Debilidades — post mix sesgado
    total_clasif = sum(d["tono_mix"].values())
    if total_clasif > 10:
        personal_pct = (d["tono_mix"].get("personal", 0) / total_clasif) * 100
        if personal_pct > 30:
            debilidades.append(
                f"**{personal_pct:.0f}% de posts clasificados son 'personal'** — mix editorial demasiado casual para el cargo de {d['cargo']}."
            )

    # Oportunidades — plataformas subexplotadas
    for plat, stats in d["engagement_per_plat"].items():
        fol = next((p["followers"] for p in d["profiles"] if p["platform"] == plat), 0)
        if fol > 5000 and stats["posts"] < 100:
            oportunidades.append(
                f"**{plat}** tiene {fol:,} seguidores pero solo {stats['posts']} publicaciones — canal subexplotado."
            )

    # Oportunidades — YouTube con baja base
    yt_profile = next((p for p in d["profiles"] if p["platform"] == "YOUTUBE"), None)
    if yt_profile and yt_profile["followers"] < 100:
        oportunidades.append(
            f"YouTube con solo {yt_profile['followers']} subs — espacio para crecer con contenido educativo tipo columna-vídeo."
        )

    # Oportunidades — redes mainstream AUSENTES (no tiene perfil registrado)
    plataformas_propias = {p["platform"] for p in d["profiles"]}
    redes_estandar = {
        "TIKTOK": "TikTok ausente — canal con mayor potencial de viralización en audiencia <35 años. Bajo costo de producción (reels de 15-60s).",
        "YOUTUBE": "YouTube ausente — formato largo para contenido reflexivo / educativo (entrevistas, foros, columna-vídeo).",
        "TWITTER": "X/Twitter ausente — espacio político natural para construir posicionamiento en debate público.",
    }
    for red, mensaje in redes_estandar.items():
        if red not in plataformas_propias:
            oportunidades.append(mensaje)

    # Amenazas — riesgo INE oficialismo
    if d["rol_politico"] == "oficialismo":
        target_gob = d["target_mix"].get("gobierno", 0)
        if target_gob > total_clasif * 0.2:
            amenazas.append(
                f"**Riesgo INE**: {target_gob} publicaciones target=gobierno en posición oficialista. Redactar como 'comunicación institucional', no como promoción personal."
            )

    # Amenazas — rechazo alto en IA
    if d["ia"]["total_comments"] > 50:
        neg_pct = (d["ia"]["negative"] / d["ia"]["total_comments"]) * 100
        if neg_pct > 25:
            amenazas.append(
                f"**Rechazo {neg_pct:.0f}% en comments analizados** ({d['ia']['negative']}/{d['ia']['total_comments']}) — detectar narrativas problemáticas."
            )

    # Default fallbacks
    if not fortalezas:
        fortalezas.append("Presencia básica en múltiples plataformas. Pendiente: validar engagement real.")
    if not debilidades:
        debilidades.append("Pendiente: ingestar más data de comments para diagnóstico profundo.")
    if not oportunidades:
        oportunidades.append("Pendiente: identificar plataformas subexplotadas tras refresh de métricas.")
    if not amenazas:
        amenazas.append("Sin amenazas detectadas con data actual. Ampliar con scrape de encuestas públicas.")

    return {"F": fortalezas, "O": oportunidades, "D": debilidades, "A": amenazas}


def build_markdown(d: dict, foda: dict) -> str:
    total_fol = sum(p["followers"] for p in d["profiles"])
    lines = [
        f"# DIAGNÓSTICO — {d['full_name']}",
        "",
        f"**Cargo:** {d['cargo']}",
        f"**Partido:** {d['partido']} · **Rol político:** {d['rol_politico']}",
        f"**Entidad:** {d['estado']}",
        f"**Fecha diagnóstico:** {datetime.now(UTC).strftime('%Y-%m-%d')}",
        "**Versión:** v1-automated-data-driven",
        "",
        "---",
        "",
        "## Baseline de métricas",
        "",
        f"- **Audiencia total cross-plataforma:** {total_fol:,} seguidores",
        f"- **Publicaciones analizadas:** {d['total_posts']:,}",
        f"- **Cobertura NLP:** {d['with_nlp']:,} posts ({d['with_nlp']*100//max(d['total_posts'],1)}%)",
        f"- **Cobertura framework político:** {d['with_framework']} posts clasificados",
        f"- **Engagement promedio (posts con data):** {d['avg_eng_nonzero']:.2f}%",
        f"- **Sentimiento político ajustado promedio:** {d['avg_sent_pol']:+.2f}",
        f"- **Comments con IA analizado:** {d['ia']['total_comments']:,} en {d['ia']['posts_con_ia']} posts",
        "",
        "### Perfiles activos",
        "",
        "| Plataforma | Handle | Seguidores | Posts | Source |",
        "|---|---|---|---|---|",
    ]
    for p in d["profiles"]:
        src_note = " ⚠️ manual" if p["data_source"] == "manual_host_ingest" else ""
        lines.append(f"| {p['platform']} | {p['handle']} | {p['followers']:,} | {p['posts']} | {p['data_source']}{src_note} |")

    lines.extend([
        "",
        "### Mix editorial (posts clasificados con framework)",
        "",
        "**Tonos:** " + ", ".join(f"{t}={n}" for t, n in sorted(d["tono_mix"].items(), key=lambda x: -x[1])) if d["tono_mix"] else "**Tonos:** sin clasificar aún",
        "",
        "**Targets:** " + ", ".join(f"{t}={n}" for t, n in sorted(d["target_mix"].items(), key=lambda x: -x[1])) if d["target_mix"] else "**Targets:** sin clasificar aún",
        "",
        "---",
        "",
        "## FODA",
        "",
        "### Fortalezas (F)",
    ])
    for f in foda["F"]:
        lines.append(f"- {f}")
    lines.append("")
    lines.append("### Oportunidades (O)")
    for o in foda["O"]:
        lines.append(f"- {o}")
    lines.append("")
    lines.append("### Debilidades (D)")
    for x in foda["D"]:
        lines.append(f"- {x}")
    lines.append("")
    lines.append("### Amenazas (A)")
    for a in foda["A"]:
        lines.append(f"- {a}")

    lines.extend([
        "",
        "---",
        "",
        "## Recomendaciones alto-nivel para plan v3",
        "",
        "1. Priorizar el canal con engagement real confirmado.",
        "2. Atacar las debilidades detectadas con tareas medibles.",
        "3. Explotar plataformas subutilizadas con contenido adaptado.",
        "4. Blindaje legal en cada pieza que toque agenda gubernamental (si oficialismo) o crítica personal (si oposición).",
        "5. Monitoreo continuo de IA — alertar si rechazo supera 30% en ventana de 7 días.",
        "",
        "---",
        "",
        "*Diagnóstico generado automáticamente desde data en BD. Revisar y enriquecer con contexto cualitativo antes de construir plan v3.*",
    ])
    return "\n".join(lines)


async def main():
    async with async_session_factory() as session:
        admin_uid = (await session.execute(
            text("SELECT id FROM users WHERE role='ADMIN' LIMIT 1")
        )).scalar_one()

        import sys
        # CLI: --dirigente N (REQUERIDO).
        # NOTA: este script hace DELETE+INSERT sobre planes_ia. Correrlo sin
        # --dirigente borraba los DIAGNOSTICOs ricos del 2026-05-10 (claude-2way
        # / gemini-cli-2way). Ahora exige flag explícito para evitar pérdida.
        if "--dirigente" not in sys.argv:
            print("ERROR: --dirigente N es requerido (sobrescribe DIAGNOSTICO existente)")
            sys.exit(1)
        idx = sys.argv.index("--dirigente")
        target_ids = [int(sys.argv[idx + 1])]

        for did in target_ids:
            data = await collect_data(session, did)
            if not data:
                continue
            foda = build_foda(data)
            md = build_markdown(data, foda)

            structure = {
                "version": "v1-automated-data-driven",
                "foda": foda,
                "baseline": {
                    "total_posts": data["total_posts"],
                    "with_nlp": data["with_nlp"],
                    "with_framework": data["with_framework"],
                    "avg_engagement": data["avg_eng_nonzero"],
                    "avg_sent_politico": data["avg_sent_pol"],
                    "ia_summary": data["ia"],
                    "tono_mix": data["tono_mix"],
                    "target_mix": data["target_mix"],
                    "profiles": data["profiles"],
                },
            }

            # Delete previous DIAGNOSTICO for this dirigente
            await session.execute(
                text("DELETE FROM planes_ia WHERE dirigente_id = :did AND tipo = 'DIAGNOSTICO'"),
                {"did": did},
            )
            await session.execute(
                text("""
                    INSERT INTO planes_ia
                        (dirigente_id, tipo, contenido, modelo_ia, prompt_usado,
                         generado_por_id, aprobado, estructura_json, created_at)
                    VALUES (:did, 'DIAGNOSTICO', :contenido, 'data-driven-v1',
                            'generate_diagnostico_dirigentes.py', :uid, false,
                            CAST(:struct AS JSONB), NOW())
                """),
                {"did": did, "contenido": md, "uid": admin_uid, "struct": json.dumps(structure)},
            )
            print(f"✅ DIAGNOSTICO generado para {data['full_name']} (dirigente_id={did})")

        await session.commit()
        print("\n🎯 6 DIAGNOSTICOS creados en planes_ia")


if __name__ == "__main__":
    asyncio.run(main())
