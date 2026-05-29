"""
Seed demo data for participacion ciudadana and campanas.
Idempotent — checks for existing data before inserting.

Run with: python -m scripts.seed_demo_data
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.campana import Campana, EstadoCampana, TipoCampana
from app.models.solicitud import (
    CanalOrigen,
    EstadoSolicitud,
    SolicitudCiudadana,
    TipoSolicitud,
)

ORG_ID = int(os.environ.get("CRECE_DEMO_ORG_ID", "1"))

# ── Demo solicitudes ciudadanas ──────────────────────────────────────────

SOLICITUDES_DEMO: list[dict] = [
    {
        "tipo": TipoSolicitud.QUEJA,
        "titulo": "Baches en Av. Insurgentes Sur tramo Mixcoac",
        "descripcion": (
            "Desde hace 3 meses hay baches profundos en Av. Insurgentes Sur "
            "entre Barranca del Muerto y Mixcoac. Varios vecinos han reportado "
            "danos a sus vehiculos. La situacion empeora con las lluvias."
        ),
        "canal": CanalOrigen.WHATSAPP,
        "colonia": "Mixcoac",
        "categoria": "infraestructura_vial",
        "prioridad": 2,
        "estado": EstadoSolicitud.EN_PROCESO,
    },
    {
        "tipo": TipoSolicitud.PROPUESTA,
        "titulo": "Huerto comunitario en parque Hundido",
        "descripcion": (
            "Propongo crear un huerto comunitario en el area sur del Parque Hundido. "
            "Hay espacio disponible y ya tenemos un grupo de 15 vecinos interesados "
            "en participar. Seria un proyecto de cohesion social y alimentacion sustentable."
        ),
        "canal": CanalOrigen.WEB,
        "colonia": "Del Valle Centro",
        "categoria": "medio_ambiente",
        "prioridad": 3,
        "estado": EstadoSolicitud.RECIBIDA,
    },
    {
        "tipo": TipoSolicitud.REPORTE_PROBLEMA,
        "titulo": "Fuga de agua en calle Pitágoras esquina Uxmal",
        "descripcion": (
            "Hay una fuga de agua considerable en la esquina de Pitagoras y Uxmal, "
            "colonia Narvarte Poniente. Lleva al menos 2 semanas y esta generando "
            "encharcamientos que afectan a los peatones y comercios de la zona."
        ),
        "canal": CanalOrigen.TELEFONO,
        "colonia": "Narvarte Poniente",
        "categoria": "agua_drenaje",
        "prioridad": 1,
        "estado": EstadoSolicitud.ASIGNADA,
    },
    {
        "tipo": TipoSolicitud.SOLICITUD_INFO,
        "titulo": "Requisitos para tramite de uso de suelo comercial",
        "descripcion": (
            "Quisiera saber cuales son los requisitos actualizados para tramitar "
            "un cambio de uso de suelo de habitacional a comercial en la colonia "
            "Roma Norte. Mi predio esta en la calle Durango."
        ),
        "canal": CanalOrigen.WEB,
        "colonia": "Roma Norte",
        "categoria": "tramites",
        "prioridad": 4,
        "estado": EstadoSolicitud.RESUELTA,
    },
    {
        "tipo": TipoSolicitud.QUEJA,
        "titulo": "Ambulantaje descontrolado en metro Chabacano",
        "descripcion": (
            "El comercio ambulante en las salidas del metro Chabacano ha crecido "
            "de manera descontrolada. Los puestos bloquean las banquetas y las "
            "salidas de emergencia. Hay riesgo para los peatones, especialmente "
            "adultos mayores y personas con discapacidad."
        ),
        "canal": CanalOrigen.PRESENCIAL,
        "colonia": "Transito",
        "categoria": "comercio_via_publica",
        "prioridad": 2,
        "estado": EstadoSolicitud.RECIBIDA,
    },
    {
        "tipo": TipoSolicitud.REPORTE_PROBLEMA,
        "titulo": "Luminarias fundidas en calle Xola",
        "descripcion": (
            "En la calle Xola entre Division del Norte y Cuauhtemoc hay al menos "
            "8 luminarias fundidas. La zona queda completamente oscura por las noches "
            "y ha habido reportes de asaltos. Pedimos atencion urgente."
        ),
        "canal": CanalOrigen.WHATSAPP,
        "colonia": "Narvarte Oriente",
        "categoria": "alumbrado_publico",
        "prioridad": 1,
        "estado": EstadoSolicitud.EN_PROCESO,
    },
    {
        "tipo": TipoSolicitud.PROPUESTA,
        "titulo": "Programa de esterilizacion gratuita para mascotas",
        "descripcion": (
            "Solicito que se organice una jornada de esterilizacion gratuita "
            "en la alcaldia. Hay muchos animales callejeros en las colonias "
            "Portales y Nativitas. Podriamos coordinar con asociaciones locales "
            "como Adopta CDMX."
        ),
        "canal": CanalOrigen.WEB,
        "colonia": "Portales Norte",
        "categoria": "bienestar_animal",
        "prioridad": 3,
        "estado": EstadoSolicitud.RECIBIDA,
    },
    {
        "tipo": TipoSolicitud.SOLICITUD_INFO,
        "titulo": "Estado del proyecto de ciclopista en Eje Central",
        "descripcion": (
            "En la consulta publica de febrero se presento el proyecto de ciclopista "
            "sobre Eje Central. Han pasado 4 meses sin informacion. Quisiera saber "
            "el estatus actual, si ya hay presupuesto asignado y fecha estimada de inicio."
        ),
        "canal": CanalOrigen.WEB,
        "colonia": "Centro",
        "categoria": "movilidad",
        "prioridad": 3,
        "estado": EstadoSolicitud.RECIBIDA,
    },
    {
        "tipo": TipoSolicitud.REPORTE_PROBLEMA,
        "titulo": "Arbol caido bloquea calle en col. Alamos",
        "descripcion": (
            "Un arbol grande se cayo durante la tormenta del viernes pasado "
            "y esta bloqueando parcialmente la calle Bolivar en la colonia Alamos. "
            "Ademas de obstruir el paso, los cables de luz estan colgando. "
            "Es un riesgo electrico y vehicular."
        ),
        "canal": CanalOrigen.TELEFONO,
        "colonia": "Alamos",
        "categoria": "proteccion_civil",
        "prioridad": 1,
        "estado": EstadoSolicitud.ASIGNADA,
    },
    {
        "tipo": TipoSolicitud.QUEJA,
        "titulo": "Ruido excesivo de bar en zona residencial Roma Sur",
        "descripcion": (
            "El bar ubicado en calle Monterrey 215, colonia Roma Sur, opera "
            "hasta las 4am con musica a alto volumen. Viola el reglamento de "
            "establecimientos mercantiles. Los vecinos de los edificios contiguos "
            "no podemos descansar. Hemos llamado a la linea 311 sin resultado."
        ),
        "canal": CanalOrigen.PRESENCIAL,
        "colonia": "Roma Sur",
        "categoria": "establecimientos_mercantiles",
        "prioridad": 2,
        "estado": EstadoSolicitud.EN_PROCESO,
    },
]

# ── Demo campana ─────────────────────────────────────────────────────────

CAMPANA_DEMO = {
    "nombre": "Jornada de Salud Comunitaria - Abril 2026",
    "descripcion": (
        "Campana de difusion para la jornada de salud gratuita en las colonias "
        "Portales, Narvarte y Del Valle. Incluye deteccion de diabetes, "
        "hipertension, vacunacion y consulta dental."
    ),
    "tipo": TipoCampana.SEGMENTADA,
    "estado": EstadoCampana.PROGRAMADA,
    "plantilla_mensaje": (
        "Hola {{nombre}}, te invitamos a la Jornada de Salud Comunitaria "
        "este sabado 18 de abril en el Centro de Salud {{colonia}}. "
        "Servicios gratuitos: deteccion de diabetes, hipertension, "
        "vacunacion y consulta dental. Horario: 9:00 a 15:00 hrs. "
        "Lleva tu INE. Te esperamos."
    ),
    "variables_plantilla": {"nombre": "str", "colonia": "str"},
    "fecha_programada": datetime.now(UTC) + timedelta(days=7),
    "total_destinatarios": 450,
}


async def seed_demo_data() -> None:
    """Insert demo solicitudes and campana data. Idempotent."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # ── Check if org_id=3 exists ─────────────────────────
        org_check = await db.execute(
            text("SELECT id FROM organizaciones WHERE id = :org_id"),
            {"org_id": ORG_ID},
        )
        if org_check.scalar_one_or_none() is None:
            print(f"[SKIP] Organizacion id={ORG_ID} does not exist. Run seed.py first.")
            await engine.dispose()
            return

        # ── Get a valid user for creado_por_id ───────────────
        user_result = await db.execute(
            text("SELECT id FROM users WHERE org_id = :org_id LIMIT 1"),
            {"org_id": ORG_ID},
        )
        user_id = user_result.scalar_one_or_none()
        if user_id is None:
            # Fallback to any user
            user_result2 = await db.execute(text("SELECT id FROM users LIMIT 1"))
            user_id = user_result2.scalar_one_or_none()
        if user_id is None:
            print("[SKIP] No users found. Run seed.py first.")
            await engine.dispose()
            return

        # ── Solicitudes ciudadanas ───────────────────────────
        existing_count = await db.execute(
            select(SolicitudCiudadana.id).where(
                SolicitudCiudadana.org_id == ORG_ID
            )
        )
        existing = existing_count.scalars().all()
        if len(existing) >= 10:
            print(f"[SKIP] Already {len(existing)} solicitudes for org_id={ORG_ID}.")
        else:
            for s_data in SOLICITUDES_DEMO:
                # Check if this specific title already exists
                dup_check = await db.execute(
                    select(SolicitudCiudadana.id).where(
                        SolicitudCiudadana.titulo == s_data["titulo"],
                        SolicitudCiudadana.org_id == ORG_ID,
                    )
                )
                if dup_check.scalar_one_or_none() is not None:
                    continue

                solicitud = SolicitudCiudadana(
                    org_id=ORG_ID,
                    **s_data,
                )
                db.add(solicitud)

            await db.flush()
            print(f"[OK] Inserted solicitudes ciudadanas for org_id={ORG_ID}.")

        # ── Campana ──────────────────────────────────────────
        existing_camp = await db.execute(
            select(Campana.id).where(
                Campana.nombre == CAMPANA_DEMO["nombre"],
                Campana.org_id == ORG_ID,
            )
        )
        if existing_camp.scalar_one_or_none() is not None:
            print(f"[SKIP] Campana '{CAMPANA_DEMO['nombre']}' already exists.")
        else:
            campana = Campana(
                org_id=ORG_ID,
                creado_por_id=user_id,
                **CAMPANA_DEMO,
            )
            db.add(campana)
            await db.flush()
            print(f"[OK] Inserted campana '{CAMPANA_DEMO['nombre']}'.")

        await db.commit()
        print("[DONE] Demo data seed complete.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
