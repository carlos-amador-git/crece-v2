"""Bulk seeder de recomendaciones IA para los 7 dirigentes (sin Pepe).

Genera 5 recomendaciones por dirigente ancladas a las efemerides próximas
60 días, con drafts templated que respetan:
- Plataformas activas de cada dirigente (no recomienda TT si no la tiene)
- Rol político (oficialismo vs oposición — tono y framing distinto)
- Partido (MC vs MORENA — narrativa de base)
- Cargo (legislativo vs ejecutivo)

NO es contenido de calidad-Pepe (esos fueron hand-crafted + Gemini cross-audit).
Esto es "skeleton uniforme" para que cada dirigente vea 5 recomendaciones
aprobadas en su /dashboard/recomendaciones. La curaduría fina viene después.

Estado inicial = 'aprobada' para que viewers las vean inmediatamente.

Idempotente: borra previas con modelo='claude-code-bulk-2026-05-12' antes
de re-insertar. NO toca las hand-crafted de Pepe ni otras versiones.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from sqlalchemy import text

from app.core.database import async_session_factory


# Efemerides próximas 60 días seleccionadas
EFEMERIDES = [
    {
        "fecha": datetime(2026, 5, 15, 8, 0, tzinfo=timezone.utc),
        "fecha_fin": datetime(2026, 5, 15, 23, 59, tzinfo=timezone.utc),
        "titulo": "Día del Maestro",
        "viralidad": "alta",
        "principio": "Haidt Care + Autoridad afectiva",
        "tono": "reconocimiento agradecido a quienes formaron",
    },
    {
        "fecha": datetime(2026, 5, 23, 8, 0, tzinfo=timezone.utc),
        "fecha_fin": datetime(2026, 5, 23, 23, 59, tzinfo=timezone.utc),
        "titulo": "Día del Estudiante",
        "viralidad": "media",
        "principio": "Cialdini Affinity — generación joven",
        "tono": "respaldo a juventud + educación como prioridad",
    },
    {
        "fecha": datetime(2026, 6, 5, 8, 0, tzinfo=timezone.utc),
        "fecha_fin": datetime(2026, 6, 5, 23, 59, tzinfo=timezone.utc),
        "titulo": "Día Mundial del Medio Ambiente",
        "viralidad": "alta",
        "principio": "Causa transversal no-polarizante",
        "tono": "compromiso ambiental concreto + acción local",
    },
    {
        "fecha": datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc),
        "fecha_fin": datetime(2026, 6, 21, 23, 59, tzinfo=timezone.utc),
        "titulo": "Día del Padre",
        "viralidad": "alta",
        "principio": "Cialdini Affinity — familia universal",
        "tono": "reconocimiento personal o a padres en general",
    },
    {
        "fecha": datetime(2026, 6, 6, 18, 0, tzinfo=timezone.utc),
        "fecha_fin": datetime(2026, 6, 7, 23, 59, tzinfo=timezone.utc),
        "titulo": "Día de la Elección (1er domingo de junio)",
        "viralidad": "alta",
        "principio": "Posicionamiento institucional + civilidad",
        "tono": "paz en urnas, democracia como acuerdo",
    },
]


def build_accion(dirigente: dict, efemeride: dict) -> str:
    """Templated draft adaptado a partido + rol + plataformas del dirigente."""
    plats = dirigente["plataformas"][:3]  # top 3 redes por followers
    plats_str = " + ".join(plats)

    if dirigente["rol_politico"] == "oficialismo":
        marco = "Comunicación institucional — respaldar la efeméride desde la responsabilidad de tu cargo."
    else:
        marco = "Voz de oposición constructiva — ubicar el tema en agenda sin polarizar."

    return (
        f"📅 {efemeride['titulo']} — POST {plats_str}.\n\n"
        f"Tono: {efemeride['tono']}.\n"
        f"Marco: {marco}\n\n"
        f"Draft sugerido (ajustar a voz propia):\n"
        f"\"Hoy reconocemos [{efemeride['titulo']}]. Como {dirigente['cargo']}, "
        f"reafirmo el compromiso con [eje principal]. #{efemeride['titulo'].replace(' ', '')} #México\"\n\n"
        f"Sugerencia formato: post + 2-3 stories. Hora pico: {efemeride['fecha'].strftime('%H:%M')} CDMX."
    )


def build_criterio(efemeride: dict) -> dict:
    return {
        "tipo": "engagement",
        "objetivo_relativo": "≥ promedio últimos 7 posts del dirigente",
        "viralidad_referencia": efemeride["viralidad"],
        "stories_min": 2,
    }


def build_evidencia(dirigente: dict, efemeride: dict) -> dict:
    return {
        "efemeride_titulo": efemeride["titulo"],
        "fecha_proxima": efemeride["fecha"].date().isoformat(),
        "plataformas_target": dirigente["plataformas"][:3],
        "partido": dirigente["partido"],
        "rol_politico": dirigente["rol_politico"],
        "fuente": "bulk_recomendaciones_v1 · 2026-05-12",
    }


async def fetch_dirigentes(session) -> list[dict]:
    rows = (await session.execute(
        text("""
            SELECT d.id, d.full_name, d.partido, d.rol_politico, d.cargo, d.org_id,
              (SELECT array_agg(spr.platform::text ORDER BY spr.followers_count DESC NULLS LAST)
                 FROM social_profiles spr WHERE spr.dirigente_id=d.id) AS plats
            FROM dirigentes d
            WHERE d.id IN (1,2,3,4,5,6,8)
            ORDER BY d.id
        """)
    )).all()
    return [
        {
            "id": r.id,
            "full_name": r.full_name,
            "partido": r.partido,
            "rol_politico": r.rol_politico,
            "cargo": r.cargo,
            "org_id": r.org_id,
            "plataformas": list(r.plats or []),
        }
        for r in rows
    ]


async def main():
    async with async_session_factory() as session:
        dirigentes = await fetch_dirigentes(session)
        print(f"Dirigentes a procesar: {len(dirigentes)}")

        # CONSOLIDACION plan_ia_id por dirigente (más reciente)
        plan_ids = {}
        for d in dirigentes:
            row = (await session.execute(
                text("""
                    SELECT id FROM planes_ia
                    WHERE dirigente_id=:did AND tipo='CONSOLIDACION'
                    ORDER BY created_at DESC LIMIT 1
                """),
                {"did": d["id"]},
            )).first()
            plan_ids[d["id"]] = row.id if row else None

        # Cleanup previas con este modelo
        await session.execute(
            text("""
                DELETE FROM recomendaciones_plan_ia
                WHERE dirigente_id = ANY(:dids)
                  AND principio_conductual ILIKE '%-- bulk-2026-05-12'
            """),
            {"dids": [d["id"] for d in dirigentes]},
        )

        total_inserted = 0
        for d in dirigentes:
            if not d["plataformas"]:
                print(f"  ⚠️  {d['full_name']} sin perfiles — skip")
                continue
            for ef in EFEMERIDES:
                accion = build_accion(d, ef)
                await session.execute(
                    text("""
                        INSERT INTO recomendaciones_plan_ia
                            (plan_ia_id, dirigente_id, org_id, tipo, accion_texto,
                             ventana_inicio, ventana_fin, ventana_duracion_dias,
                             criterio_exito, principio_conductual, evidencia_respaldo,
                             estado, created_at, updated_at)
                        VALUES (:plan_id, :did, :org, 'start', :accion,
                                :ini, :fin, :dur,
                                CAST(:crit AS JSONB),
                                :princ,
                                CAST(:evid AS JSONB),
                                'aprobada', NOW(), NOW())
                    """),
                    {
                        "plan_id": plan_ids.get(d["id"]),
                        "did": d["id"],
                        "org": d["org_id"],
                        "accion": accion,
                        "ini": ef["fecha"],
                        "fin": ef["fecha_fin"],
                        "dur": max(1, (ef["fecha_fin"] - ef["fecha"]).days),
                        "crit": json.dumps(build_criterio(ef)),
                        "princ": f"{ef['principio']} -- bulk-2026-05-12",
                        "evid": json.dumps(build_evidencia(d, ef)),
                    },
                )
                total_inserted += 1
            print(f"  ✅ {d['full_name']} · {len(EFEMERIDES)} recomendaciones")

        await session.commit()
        print(f"\n🎯 {total_inserted} recomendaciones insertadas (estado=aprobada)")


if __name__ == "__main__":
    asyncio.run(main())
