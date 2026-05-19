"""Seed batch de 5 planes deliberados (Solano, Pineda, Nolasco, Jiménez, Cravioto).

Lee batch-5-dirigentes-v1.json (ya con audit Gemini integrado).
Reutiliza los mismos mappings de plataforma/formato que el script de Piña.
Idempotente por plan_id.
"""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import text

from app.core.database import async_session_factory

DATA_FILE = Path(__file__).parent.parent / "data" / "planes-deliberados" / "batch-5-dirigentes-v1.json"


PLATAFORMA_VALIDAS = {
    "INSTAGRAM", "TWITTER", "FACEBOOK", "TIKTOK", "YOUTUBE",
    "WHATSAPP", "LINKEDIN", "BLUESKY", "THREADS", "TELEGRAM", "CROSS",
}

FORMATO_VALIDOS = {
    "post_texto", "post_imagen", "video_corto", "video_largo", "reel",
    "story", "live", "hilo", "carousel", "articulo", "comentario",
    "respuesta", "evento", "otro",
}


def map_plataforma(raw: str) -> str:
    r = raw.strip().upper()
    if r in PLATAFORMA_VALIDAS:
        return r
    if "," in raw or r in {"TODAS", "TODOS", "INTERNAL", "MEDIOS_EXTERNOS"}:
        return "CROSS"
    return "CROSS"


def map_formato(raw: str) -> str:
    if raw in FORMATO_VALIDOS:
        return raw
    return "otro"


async def seed_plan(session, plan_data: dict, meta: dict) -> tuple[int, int]:
    dirigente_id = plan_data["dirigente_id"]
    tareas = plan_data["tareas"]

    existing_plan = (
        await session.execute(
            text("SELECT id FROM planes_ia WHERE dirigente_id = :did AND tipo = 'CONSOLIDACION' ORDER BY id LIMIT 1"),
            {"did": dirigente_id},
        )
    ).first()

    if existing_plan:
        plan_id = existing_plan[0]
        print(f"  ↻ plan_id={plan_id} ya existe para dirigente {dirigente_id} ({plan_data['dirigente_nombre']})")
    else:
        admin_uid = (
            await session.execute(text("SELECT id FROM users WHERE role='ADMIN' LIMIT 1"))
        ).scalar_one()
        new_plan = (
            await session.execute(
                text("""
                    INSERT INTO planes_ia (
                        dirigente_id, tipo, contenido, modelo_ia, prompt_usado,
                        generado_por_id, aprobado, created_at
                    )
                    VALUES (
                        :did, 'CONSOLIDACION',
                        :contenido, 'claude-opus-4.6+gemini-2.5-pro',
                        'deliberación 3-IAs batch', :uid, false, NOW()
                    )
                    RETURNING id
                """),
                {
                    "did": dirigente_id,
                    "uid": admin_uid,
                    "contenido": f"Plan de Consolidación para {plan_data['dirigente_nombre']} — generado con deliberación Claude + Gemini.\n\nContexto: {plan_data.get('contexto', '')}\n\nVer tareas estructuradas en /dashboard/planes/{{id}}.",
                },
            )
        ).first()
        plan_id = new_plan[0]
        print(f"  + plan_id={plan_id} CREADO para dirigente {dirigente_id} ({plan_data['dirigente_nombre']})")

    existing = (
        await session.execute(
            text("SELECT COUNT(*) FROM plan_tareas WHERE plan_id = :pid"),
            {"pid": plan_id},
        )
    ).scalar_one()
    if existing > 0:
        print(f"    ⚠️  plan_id={plan_id} tiene {existing} tareas. Re-seed...")
        await session.execute(
            text("DELETE FROM plan_tareas WHERE plan_id = :pid"),
            {"pid": plan_id},
        )

    for t in tareas:
        deadline = datetime.now(UTC) + timedelta(days=t["deadline_dias"])
        historial = [{
            "timestamp": datetime.now(UTC).isoformat(),
            "actor": "seed_batch_deliberado_v2",
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

    structure = {
        "version": meta["version"],
        "deliberado_con": meta["deliberado_con"],
        "contexto": plan_data.get("contexto", ""),
        "cambios_vs_v1": meta.get("cambios_vs_v1_integrados_gemini", []),
        "blindaje_electoral_nota": meta.get("blindaje_electoral_nota", ""),
    }
    await session.execute(
        text("UPDATE planes_ia SET estructura_json = CAST(:j AS JSONB) WHERE id = :pid"),
        {"j": json.dumps(structure), "pid": plan_id},
    )
    return plan_id, len(tareas)


async def main() -> None:
    with DATA_FILE.open() as f:
        batch = json.load(f)

    meta = batch["meta"]
    planes = batch["planes"]

    total_tareas = 0
    async with async_session_factory() as session:
        for p in planes:
            plan_id, n = await seed_plan(session, p, meta)
            print(f"✅ plan_id={plan_id} ({p['dirigente_nombre']}): {n} tareas")
            total_tareas += n
        await session.commit()

    print(f"\n🎯 Total tareas sembradas: {total_tareas} en {len(planes)} planes")


if __name__ == "__main__":
    asyncio.run(main())
