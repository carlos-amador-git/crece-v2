"""Genera plan v3 CONSOLIDACION por dirigente, grounded en DIAGNOSTICO FODA.

Estrategia migración suave:
- Plan v2 (CONSOLIDACION existente) queda marcado como `supersedes=True` en estructura_json
- Plan v3 (nuevo) es la versión activa
- Tareas v2 NO se borran (historial preservado)
- Tareas v3 referencian líneas FODA con `fundamento_foda`
"""
from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.core.database import async_session_factory


def derive_tareas_from_foda(foda: dict, dirigente: dict, baseline: dict) -> list[dict]:
    """Reglas deterministas: cada Debilidad + Amenaza → 1 tarea, cada Oportunidad → 1 tarea de explotación."""
    tareas = []
    orden = 0

    # Atacar Debilidades
    for d in foda.get("D", [])[:4]:
        orden += 1
        # Detectar si es sobre canal dead (engagement=0)
        if "engagement=0" in d.lower():
            tareas.append({
                "orden": orden,
                "titulo": "Auditar scraper + replantear estrategia en canales con engagement=0",
                "descripcion": f"FODA[D]: {d}  Acción: (1) validar scraper de las plataformas listadas, (2) si dato es real, redesign editorial.",
                "plataforma": "CROSS",
                "formato": "otro",
                "frecuencia": "una vez",
                "responsable": "MD TI + equipo comunicación",
                "deadline_dias": 14,
                "metrica_objetivo": "% plataformas con engagement > 0",
                "metrica_valor_objetivo": 80.0,
                "prioridad": "critica",
                "fundamento_foda": "D: " + d[:150],
            })
        elif "personal" in d.lower() and "%" in d:
            tareas.append({
                "orden": orden,
                "titulo": "Disciplina editorial: bajar posts 'personal' a ≤20% del mix",
                "descripcion": f"FODA[D]: {d}  Acción: sustituir personal puro por personal+territorial (visitas, eventos locales).",
                "plataforma": "CROSS",
                "formato": "otro",
                "frecuencia": "continua",
                "responsable": "editor contenido",
                "deadline_dias": 60,
                "metrica_objetivo": "% posts tono=personal",
                "metrica_valor_objetivo": 20.0,
                "prioridad": "alta",
                "fundamento_foda": "D: " + d[:150],
            })
        else:
            tareas.append({
                "orden": orden,
                "titulo": f"Atacar debilidad detectada ({orden})",
                "descripcion": f"FODA[D]: {d}  Equipo debe proponer plan específico en ≤7 días.",
                "plataforma": "CROSS",
                "formato": "otro",
                "frecuencia": "una vez",
                "responsable": "equipo comunicación",
                "deadline_dias": 30,
                "metrica_objetivo": "plan de acción definido",
                "metrica_valor_objetivo": 1.0,
                "prioridad": "media",
                "fundamento_foda": "D: " + d[:150],
            })

    # Explotar Oportunidades
    for o in foda.get("O", [])[:4]:
        orden += 1
        # Detectar plataforma específica
        plat_detected = "CROSS"
        for p in ["TIKTOK", "INSTAGRAM", "FACEBOOK", "TWITTER", "YOUTUBE"]:
            if p in o.upper():
                plat_detected = p
                break
        tareas.append({
            "orden": orden,
            "titulo": f"Escalar canal {plat_detected} — detectado como oportunidad",
            "descripcion": f"FODA[O]: {o}  Producir contenido dedicado 3-5/semana con formato nativo de la plataforma.",
            "plataforma": plat_detected,
            "formato": "video_corto" if plat_detected in {"TIKTOK", "INSTAGRAM"} else "post_texto",
            "frecuencia": "3-5/semana",
            "responsable": f"equipo contenido {dirigente['full_name'].split()[0]}",
            "deadline_dias": 60,
            "metrica_objetivo": f"publicaciones en {plat_detected}",
            "metrica_valor_objetivo": 24.0,
            "prioridad": "alta",
            "fundamento_foda": "O: " + o[:150],
        })

    # Mitigar Amenazas
    for a in foda.get("A", [])[:3]:
        orden += 1
        if "ine" in a.lower() or "propaganda" in a.lower():
            tareas.append({
                "orden": orden,
                "titulo": "Blindaje INE: revisión legal de piezas oficialistas antes de publicar",
                "descripcion": f"FODA[A]: {a}  Protocolo: toda pieza con target=gobierno pasa por copywriting legal ANTES de publicar.",
                "plataforma": "CROSS",
                "formato": "otro",
                "frecuencia": "continua",
                "responsable": f"{dirigente['full_name']} + asesor legal",
                "deadline_dias": 7,
                "metrica_objetivo": "% piezas oficialistas con revisión legal",
                "metrica_valor_objetivo": 100.0,
                "prioridad": "critica",
                "fundamento_foda": "A: " + a[:150],
            })
        elif "rechazo" in a.lower():
            tareas.append({
                "orden": orden,
                "titulo": "Monitoreo rechazo 7d: alerta + plan respuesta si supera 30%",
                "descripcion": f"FODA[A]: {a}  Cuando delta_rechazo_7d > 30%, disparar revisión narrativa y serie de respuesta en 72h.",
                "plataforma": "CROSS",
                "formato": "otro",
                "frecuencia": "monitoreo continuo",
                "responsable": "MD Consultoría + dirigente",
                "deadline_dias": 30,
                "metrica_objetivo": "tiempo respuesta a alerta rechazo (h)",
                "metrica_valor_objetivo": 72.0,
                "prioridad": "alta",
                "fundamento_foda": "A: " + a[:150],
            })
        else:
            tareas.append({
                "orden": orden,
                "titulo": f"Mitigar amenaza detectada ({orden})",
                "descripcion": f"FODA[A]: {a}  Equipo debe definir contramedidas.",
                "plataforma": "CROSS",
                "formato": "otro",
                "frecuencia": "una vez",
                "responsable": "equipo estrategia",
                "deadline_dias": 30,
                "metrica_objetivo": "contramedidas documentadas",
                "metrica_valor_objetivo": 1.0,
                "prioridad": "media",
                "fundamento_foda": "A: " + a[:150],
            })

    # Apalancar Fortalezas — 1 tarea
    if foda.get("F"):
        orden += 1
        f = foda["F"][0]
        tareas.append({
            "orden": orden,
            "titulo": "Apalancar fortaleza principal — escalar donde ya funciona",
            "descripcion": f"FODA[F]: {f}  Duplicar inversión de producción en este vehículo.",
            "plataforma": "CROSS",
            "formato": "otro",
            "frecuencia": "continua",
            "responsable": f"equipo contenido {dirigente['full_name'].split()[0]}",
            "deadline_dias": 90,
            "metrica_objetivo": "incremento output en canal ganador %",
            "metrica_valor_objetivo": 50.0,
            "prioridad": "alta",
            "fundamento_foda": "F: " + f[:150],
        })

    return tareas


async def main():
    async with async_session_factory() as session:
        admin_uid = (await session.execute(
            text("SELECT id FROM users WHERE role='ADMIN' LIMIT 1")
        )).scalar_one()

        for did in range(1, 7):
            dirigente = (await session.execute(
                text("SELECT id, full_name, cargo, partido, rol_politico FROM dirigentes WHERE id = :id"),
                {"id": did},
            )).first()
            if not dirigente:
                continue
            d_dict = {"id": dirigente[0], "full_name": dirigente[1], "cargo": dirigente[2],
                      "partido": dirigente[3], "rol_politico": dirigente[4]}

            diag = (await session.execute(
                text("""
                    SELECT estructura_json FROM planes_ia
                    WHERE dirigente_id = :did AND tipo = 'DIAGNOSTICO'
                    ORDER BY created_at DESC LIMIT 1
                """),
                {"did": did},
            )).first()
            if not diag:
                print(f"⏭️  Sin diagnóstico para dirigente {did}")
                continue

            foda = diag[0].get("foda", {})
            baseline = diag[0].get("baseline", {})
            tareas = derive_tareas_from_foda(foda, d_dict, baseline)

            # Mark existing CONSOLIDACION v2 as superseded (via estructura_json)
            old_plans = (await session.execute(
                text("""
                    SELECT id, estructura_json FROM planes_ia
                    WHERE dirigente_id = :did AND tipo = 'CONSOLIDACION'
                """),
                {"did": did},
            )).fetchall()
            for op_row in old_plans:
                old_struct = op_row[1] or {}
                old_struct["superseded_by_v3"] = True
                old_struct["superseded_at"] = datetime.now(UTC).isoformat()
                await session.execute(
                    text("UPDATE planes_ia SET estructura_json = CAST(:s AS JSONB) WHERE id = :id"),
                    {"s": json.dumps(old_struct), "id": op_row[0]},
                )

            # Create new v3 plan
            structure_v3 = {
                "version": "v3-grounded-diagnostico",
                "supersedes_plan_ids": [p[0] for p in old_plans],
                "derived_from_diagnostico": True,
                "foda_applied": foda,
                "generated_at": datetime.now(UTC).isoformat(),
            }
            contenido = f"# Plan v3 — {d_dict['full_name']}\n\nGrounded en DIAGNÓSTICO FODA (ver tipo=DIAGNOSTICO).\n\nTareas derivadas:\n\n" + "\n".join(f"{i+1}. {t['titulo']}" for i, t in enumerate(tareas))

            result = await session.execute(
                text("""
                    INSERT INTO planes_ia (dirigente_id, tipo, contenido, modelo_ia, prompt_usado,
                                           generado_por_id, aprobado, estructura_json, created_at)
                    VALUES (:did, 'CONSOLIDACION', :contenido, 'foda-derived-v3',
                            'generate_planes_v3_from_diagnostico.py', :uid, false,
                            CAST(:struct AS JSONB), NOW())
                    RETURNING id
                """),
                {"did": did, "contenido": contenido, "uid": admin_uid,
                 "struct": json.dumps(structure_v3)},
            )
            new_plan_id = result.scalar_one()

            # Insert tareas
            for t in tareas:
                historial = [{
                    "timestamp": datetime.now(UTC).isoformat(),
                    "actor": "v3_from_diagnostico",
                    "accion": "creacion",
                    "fundamento_foda": t["fundamento_foda"],
                    "prioridad": t["prioridad"],
                }]
                deadline = datetime.now(UTC) + timedelta(days=t["deadline_dias"])
                await session.execute(
                    text("""
                        INSERT INTO plan_tareas
                            (plan_id, orden, titulo, descripcion, plataforma, formato,
                             frecuencia, responsable, deadline, metrica_objetivo,
                             metrica_valor_objetivo, estado, cambios_historial,
                             created_at, updated_at)
                        VALUES (:pid, :orden, :titulo, :desc, :plat, :fmt, :frec, :resp,
                                :dl, :met_obj, :met_val, 'TODO', CAST(:hist AS JSONB),
                                NOW(), NOW())
                    """),
                    {
                        "pid": new_plan_id,
                        "orden": t["orden"],
                        "titulo": t["titulo"][:200],
                        "desc": t["descripcion"],
                        "plat": t["plataforma"],
                        "fmt": t["formato"],
                        "frec": t["frecuencia"],
                        "resp": t["responsable"][:100],
                        "dl": deadline,
                        "met_obj": t["metrica_objetivo"][:200],
                        "met_val": t["metrica_valor_objetivo"],
                        "hist": json.dumps(historial),
                    },
                )

            print(f"✅ Plan v3 para {d_dict['full_name']}: plan_id={new_plan_id}, {len(tareas)} tareas (supersedes {len(old_plans)} v2)")

        await session.commit()
        print("\n🎯 Planes v3 generados para los 6 dirigentes")


if __name__ == "__main__":
    asyncio.run(main())
