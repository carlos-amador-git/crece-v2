"""Seed tareas estructuradas del plan Piña v2 deliberado (Claude + Gemini).

Lee pina-consolidacion-v2.json y pobla plan_tareas con 12 tareas.
Idempotente: si ya existen tareas del plan_id=1, no las duplica.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, UTC
from pathlib import Path

from sqlalchemy import text

from app.core.database import async_session_factory


DATA_FILE = Path(__file__).parent.parent / "data" / "planes-deliberados" / "pina-consolidacion-v2.json"


PLATAFORMA_VALIDAS = {
    "INSTAGRAM", "TWITTER", "FACEBOOK", "TIKTOK", "YOUTUBE",
    "WHATSAPP", "LINKEDIN", "BLUESKY", "THREADS", "TELEGRAM", "CROSS",
}

FORMATO_VALIDOS = {
    "post_texto", "post_imagen", "video_corto", "video_largo", "reel",
    "story", "live", "hilo", "carousel", "articulo", "comentario",
    "respuesta", "evento", "otro",
}

FORMATO_MAP = {
    "video vertical con dato": "video_corto",
    "diagnóstico técnico": "otro",
    "hilo 3-5 tweets": "hilo",
    "pieza larga + adaptaciones": "articulo",
    "hashtag disciplina": "otro",
    "reply directo": "respuesta",
    "pipeline técnico": "otro",
    "reel": "reel",
    "disciplina editorial": "otro",
    "columna 600-800 palabras": "articulo",
    "trigger + playbook": "otro",
    "reporte + serie derivada": "articulo",
}


def map_plataforma(raw: str) -> str:
    r = raw.strip().upper()
    if r in PLATAFORMA_VALIDAS:
        return r
    if "," in raw or r in {"TODAS", "TODOS", "INTERNAL", "MEDIOS_EXTERNOS"}:
        return "CROSS"
    return "CROSS"


def map_formato(raw: str) -> str:
    if raw in FORMATO_MAP:
        return FORMATO_MAP[raw]
    if raw in FORMATO_VALIDOS:
        return raw
    return "otro"


async def main() -> None:
    with DATA_FILE.open() as f:
        plan = json.load(f)

    plan_id = plan["plan_id"]
    tareas = plan["tareas"]

    async with async_session_factory() as session:
        existing = (
            await session.execute(
                text("SELECT COUNT(*) FROM plan_tareas WHERE plan_id = :pid"),
                {"pid": plan_id},
            )
        ).scalar_one()

        if existing > 0:
            print(f"⚠️  plan_id={plan_id} ya tiene {existing} tareas. Borrando para re-seed...")
            await session.execute(
                text("DELETE FROM plan_tareas WHERE plan_id = :pid"),
                {"pid": plan_id},
            )

        for t in tareas:
            deadline = datetime.now(UTC) + timedelta(days=t["deadline_dias"])
            historial = [{
                "timestamp": datetime.now(UTC).isoformat(),
                "actor": "seed_deliberado_v2",
                "accion": "creacion",
                "fundamento": t["fundamento"],
                "prioridad": t["prioridad"],
            }]
            await session.execute(
                text("""
                    INSERT INTO plan_tareas (
                        plan_id, orden, titulo, descripcion, plataforma, formato,
                        frecuencia, responsable, deadline, metrica_objetivo,
                        metrica_valor_objetivo, estado, cambios_historial,
                        created_at, updated_at
                    )
                    VALUES (
                        :plan_id, :orden, :titulo, :descripcion, :plataforma, :formato,
                        :frecuencia, :responsable, :deadline, :metrica_objetivo,
                        :metrica_valor_objetivo, 'TODO', CAST(:historial AS JSONB),
                        NOW(), NOW()
                    )
                """),
                {
                    "plan_id": plan_id,
                    "orden": t["orden"],
                    "titulo": t["titulo"],
                    "descripcion": t["descripcion"],
                    "plataforma": map_plataforma(t["plataforma"]),
                    "formato": map_formato(t["formato"]),
                    "frecuencia": t["frecuencia"],
                    "responsable": t["responsable"],
                    "deadline": deadline,
                    "metrica_objetivo": t["metrica_objetivo"],
                    "metrica_valor_objetivo": t["metrica_valor_objetivo"],
                    "historial": json.dumps(historial),
                },
            )

        await session.execute(
            text("UPDATE planes_ia SET estructura_json = CAST(:j AS JSONB) WHERE id = :pid"),
            {
                "j": json.dumps({
                    "version": plan["version"],
                    "deliberado_con": plan["deliberado_con"],
                    "cambios_vs_v1": plan.get("cambios_vs_v1", []),
                    "metricas_meta_global": plan.get("metricas_meta_global", {}),
                    "notas_para_dirigente": plan.get("notas_para_dirigente", ""),
                }),
                "pid": plan_id,
            },
        )

        await session.commit()
        print(f"✅ {len(tareas)} tareas sembradas para plan_id={plan_id} (Piña)")


if __name__ == "__main__":
    asyncio.run(main())
