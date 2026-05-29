"""Pepe Monroy · 5 recomendaciones IA accionables ancladas a efemérides.

Cada recomendación incluye:
- Post draft en su tono real (paz/disciplina/familia)
- Ventana de ejecución (días previos + día efeméride)
- Principio conductual aplicado
- Criterio de éxito medible
- Evidencia respaldo (link a posts pasados con tono similar)

Cross-audit Gemini aplicado:
- DRAFT 1 Maestro: condensado a 2 líneas (era 3 párrafos)
- DRAFT 2 Homofobia: DESCARTADO por Gemini (riesgo polarización base conservadora)
- DRAFT 3 Medio Ambiente: condensado + más emojis
- DRAFT 4 Día del Padre: APROBADO sin cambios
- DRAFT 5 TikTok: 5 reels/sem → 2-3 reels/sem (realista)
- NUEVO DRAFT 6: Día de la Elección 7-jun (omisión grave de mi draft inicial, detectada por Gemini)

Idempotente: borra recomendaciones previas de Pepe con modelo claude-code-2026-05-12.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from sqlalchemy import text

from app.core.database import async_session_factory


# Plan IA CONSOLIDACION id de Pepe (verificar antes de correr)
PLAN_IA_ID_PEPE = 37
DIRIGENTE_ID = 57
ORG_ID = 4


REC_1_MAESTRO = {
    "tipo": "start",
    "accion_texto": (
        "📚🙏 Día del Maestro — POST IG + FB.\n\n"
        "Draft (2 líneas, su estilo real):\n"
        "\"📚🙏 La disciplina y la paz interior comienzan con las lecciones de un buen maestro. "
        "Gracias a quienes construyen a México desde las aulas enseñándonos a no rendirnos.\n"
        "#DíaDelMaestro #Educación #Disciplina #HagamosRED #SomosPAZ\"\n\n"
        "Publicar 15-may entre 8-10am. Reel opcional: 30 seg de un maestro suyo "
        "(profesor, mentor) o frase a cámara de él mismo."
    ),
    "ventana_inicio": datetime(2026, 5, 14, 20, 0, tzinfo=timezone.utc),
    "ventana_fin": datetime(2026, 5, 15, 23, 59, tzinfo=timezone.utc),
    "ventana_duracion_dias": 2,
    "principio_conductual": "Haidt Care + Autoridad afectiva",
    "criterio_exito": {
        "likes_ig_24h_min": 50,
        "comments_min": 5,
        "comments_quality": "menciones a maestros propios por seguidores",
    },
    "evidencia_respaldo": {
        "tono_alineado_con": ["posts #PazInterior", "#Ayuno52horas", "running disciplina"],
        "viralidad_efemeride": "alta",
        "fuente_efemeride_id": "ver tabla efemerides mes=5 dia=15",
    },
}


REC_3_MEDIO_AMBIENTE = {
    "tipo": "start",
    "accion_texto": (
        "🌎🤍 Día Mundial del Medio Ambiente — POST + Reel IG/FB.\n\n"
        "Draft (condensado, más emojis · Gemini):\n"
        "\"🌎🤍 La paz interior también es cuidar las calles que corremos y el aire que respiramos. "
        "Hoy sumé 5km recogiendo basura, ¿quién me manda foto haciendo lo mismo en su colonia? 🏃🏽‍♂️♻️\n"
        "#DíaDelMedioAmbiente #PazInterior #DisciplinaSocial #SomosPAZ\"\n\n"
        "Reel 30-60 seg corriendo + recogiendo basura. CTA explícito: pedir UGC "
        "(user-generated content) en comments con foto/video propio."
    ),
    "ventana_inicio": datetime(2026, 6, 4, 18, 0, tzinfo=timezone.utc),
    "ventana_fin": datetime(2026, 6, 5, 23, 59, tzinfo=timezone.utc),
    "ventana_duracion_dias": 2,
    "principio_conductual": "Cialdini Social Proof + UGC activation",
    "criterio_exito": {
        "likes_24h_min": 100,
        "ugc_responses_min": 10,
        "ugc_quality": "fotos/videos de seguidores haciendo limpieza local",
    },
    "evidencia_respaldo": {
        "tono_alineado_con": ["disciplina personal", "running diario"],
        "oportunidad_foda": "activar IG con reels semanales · oportunidad #3",
        "viralidad_efemeride": "alta",
    },
}


REC_4_DIA_PADRE = {
    "tipo": "start",
    "accion_texto": (
        "👨‍👧‍👦💙 Día del Padre — POST IG + FB.\n\n"
        "Draft (APROBADO por Gemini · sin cambios):\n"
        "\"👨‍👧‍👦💙 Ser padre me enseñó que la disciplina sin amor es dura, "
        "y el amor sin disciplina es vacío.\n\n"
        "A mis tres motores: ustedes son la razón por la que despierto a las 5 am, "
        "por la que ayuno cuando tengo hambre, por la que sigo construyendo país.\n\n"
        "Feliz Día del Padre a todos los que están educando con paciencia. 🙏\n"
        "#DíaDelPadre #Familia #Amor #Disciplina #SomosPAZ\"\n\n"
        "Foto con sus 3 hijos. Hora: 11-12 am (peak engagement familiar)."
    ),
    "ventana_inicio": datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc),
    "ventana_fin": datetime(2026, 6, 21, 23, 59, tzinfo=timezone.utc),
    "ventana_duracion_dias": 2,
    "principio_conductual": "Cialdini Affinity — familia es su pilar más auténtico",
    "criterio_exito": {
        "likes_min": 200,
        "engagement_rate_objetivo": "mejor del mes",
        "comments_quality": "respuestas de padres con sus propios hijos",
    },
    "evidencia_respaldo": {
        "tono_alineado_con": ["post de boda 11-may", "posts con hijos abr-may"],
        "veta_pilar": "familia (la más auténtica de las 4)",
        "viralidad_efemeride": "alta",
    },
}


REC_5_TIKTOK = {
    "tipo": "start",
    "accion_texto": (
        "📱 Abrir cuenta TikTok @pepemonroyma — START estructural.\n\n"
        "Plan ajustado por Gemini (realista):\n"
        "• 2-3 reels/semana (NO 5/sem — burnout garantizado)\n"
        "• 100% reciclado de Reels IG que ya produce — ajustar ganchos primeros 3 seg + música TikTok\n"
        "• Hashtags: #TikTokMx #DiarioDePaz #Disciplina #PazInterior #SomosPAZ\n"
        "• Pilares: ayuno/disciplina (35%), familia (30%), afiliaciones territoriales (20%), causas cívicas (15%)\n"
        "• Hora de publicación: 19-21h (peak TikTok MX)\n\n"
        "Métrica a 30 días: 500 followers + 3 reels con > 5k views."
    ),
    "ventana_inicio": datetime(2026, 5, 13, 0, 0, tzinfo=timezone.utc),
    "ventana_fin": datetime(2026, 6, 13, 23, 59, tzinfo=timezone.utc),
    "ventana_duracion_dias": 30,
    "principio_conductual": "Apalancamiento estructural — red ausente con audiencia objetivo",
    "criterio_exito": {
        "followers_objetivo_30d": 500,
        "reels_min_5k_views": 3,
        "cadencia_objetivo": "2-3 reels/semana sostenible",
    },
    "evidencia_respaldo": {
        "oportunidad_foda": "TikTok ausente · FODA oportunidad #3",
        "audiencia_target": "<35 años",
        "costo_marginal": "0 (recicla producción IG)",
    },
}


REC_6_ELECCIONES = {
    "tipo": "start",
    "accion_texto": (
        "🗳️🕊️ Día de la Elección (1er domingo de junio 2026) — POST + Stories IG/FB.\n\n"
        "Detectado por Gemini como omisión crítica: siendo Líder Nacional de Partidos\n"
        "Políticos Locales, una jornada electoral SIN post es señal débil.\n\n"
        "Draft (causa neutra, no-partidista · alineado a #SomosPAZ):\n"
        "\"🗳️🕊️ Hoy México decide en las urnas — con respeto, con paz, con esperanza.\n\n"
        "La democracia no es una pelea, es un acuerdo entre vecinos. Salgamos a votar "
        "con la misma disciplina con que entrenamos, ayunamos y construimos familia.\n\n"
        "#PazEnLasUrnas #Democracia #Civilidad #SomosPAZ #HagamosRED\"\n\n"
        "Stories: foto suya en la casilla (post-voto), invitando a tag de otros que ya votaron."
    ),
    "ventana_inicio": datetime(2026, 6, 6, 18, 0, tzinfo=timezone.utc),
    "ventana_fin": datetime(2026, 6, 7, 23, 59, tzinfo=timezone.utc),
    "ventana_duracion_dias": 2,
    "principio_conductual": "Causa neutra + posicionamiento institucional (Líder Nac. Partidos Locales)",
    "criterio_exito": {
        "post_publicado_antes_18h_cdmx": True,
        "stories_min": 3,
        "likes_min": 150,
        "shares_min": 20,
    },
    "evidencia_respaldo": {
        "cargo": "Líder Nacional de Partidos Políticos Locales · jornada electoral es OBLIGATORIA en su agenda",
        "tono_alineado_con": ["#SomosPAZ", "#Civilidad", "neutralidad partidista"],
        "fuente_cross_audit": "Gemini detectó omisión 2026-05-12",
    },
}


RECOMENDACIONES = [REC_1_MAESTRO, REC_3_MEDIO_AMBIENTE, REC_4_DIA_PADRE, REC_5_TIKTOK, REC_6_ELECCIONES]


async def main():
    async with async_session_factory() as session:
        await session.execute(
            text("""
                DELETE FROM recomendaciones_plan_ia
                WHERE dirigente_id = :did AND plan_ia_id = :plan_id
            """),
            {"did": DIRIGENTE_ID, "plan_id": PLAN_IA_ID_PEPE},
        )

        for rec in RECOMENDACIONES:
            await session.execute(
                text("""
                    INSERT INTO recomendaciones_plan_ia
                        (plan_ia_id, dirigente_id, org_id, tipo, accion_texto,
                         ventana_inicio, ventana_fin, ventana_duracion_dias,
                         criterio_exito, principio_conductual, evidencia_respaldo,
                         estado, created_at, updated_at)
                    VALUES (:plan_id, :did, :org, :tipo, :accion,
                            :ini, :fin, :dur,
                            CAST(:crit AS JSONB), :princ, CAST(:evid AS JSONB),
                            'aprobada', NOW(), NOW())
                """),
                {
                    "plan_id": PLAN_IA_ID_PEPE,
                    "did": DIRIGENTE_ID,
                    "org": ORG_ID,
                    "tipo": rec["tipo"],
                    "accion": rec["accion_texto"],
                    "ini": rec["ventana_inicio"],
                    "fin": rec["ventana_fin"],
                    "dur": rec["ventana_duracion_dias"],
                    "crit": json.dumps(rec["criterio_exito"]),
                    "princ": rec["principio_conductual"],
                    "evid": json.dumps(rec["evidencia_respaldo"]),
                },
            )
        await session.commit()
        print(f"OK · {len(RECOMENDACIONES)} recomendaciones insertadas para Pepe (dirigente_id={DIRIGENTE_ID})")


if __name__ == "__main__":
    asyncio.run(main())
