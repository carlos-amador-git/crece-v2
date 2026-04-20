"""Seed 10 promesas plausibles para Alejandro Piña Medina (dirigente_id=1).

Sprint S4 T-1.1 (CEO §9.8 aprobado 2026-04-19): MD seed mínimo para que B16
Rastreador de Promesas pase de `insufficient_data` a `ok` en Piña. Los otros
7 dirigentes quedan con `promesas_dirigente=[]` hasta Onboarding Wizard S5,
donde el cliente las declara en primera persona (D-22 client-owned data).

Reglas de calidad:
- Promesas **plausibles** derivadas del rol público de Piña (Coordinador
  Comisión Operativa MC CDMX · miembro Secretaría del Ayuntamiento Cuajimalpa
  en administración previa). NO son promesas reales extraídas de declaración
  pública — son fixture mínimo para validar el pipeline B16 + Plan IA.
- MD review S5 reemplazará este fixture con declaraciones reales del cliente
  cuando firme contrato.
- Cada fila marca `evidencia_url=NULL` intencionalmente (fixture arranque).

Idempotente: si ya hay >= 10 promesas para dirigente_id=1, no re-inserta.

Run:
    docker exec -it crece-backend python -m scripts.seed_promesas_pina_s4
"""
from __future__ import annotations

import asyncio
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.promesa_dirigente import PromesaDirigente, PromesaEstado

DIRIGENTE_ID_PINA = 1

# 10 promesas plausibles del rol. Fechas de compromiso se generan a futuro
# (entre hoy y +180 días) con distribución escalonada para que el tracker
# B16 tenga señal útil en ventanas temporales distintas.
PROMESAS_PINA: list[dict] = [
    {
        "texto": "Publicar informe trimestral de actividades de la Comisión Operativa MC CDMX con métricas de cobertura territorial (distritos, eventos, brigadas).",
        "dias_compromiso": 30,
    },
    {
        "texto": "Convocar foro público abierto sobre movilidad urbana en alcaldía Iztapalapa con participación de expertos académicos y ciudadanía no militante.",
        "dias_compromiso": 45,
    },
    {
        "texto": "Impulsar auditoría externa independiente sobre gasto de precampaña de aspirantes MC CDMX 2027, con publicación abierta de resultados.",
        "dias_compromiso": 90,
    },
    {
        "texto": "Crear programa de mentorías digitales para 100 jóvenes militantes MC CDMX en comunicación política y gestión pública, ciclo semestral.",
        "dias_compromiso": 60,
    },
    {
        "texto": "Realizar 20 asambleas territoriales en alcaldías prioritarias (Iztapalapa, Gustavo A. Madero, Álvaro Obregón) en ventana de 6 meses.",
        "dias_compromiso": 150,
    },
    {
        "texto": "Publicar posicionamiento escrito sobre iniciativa de reforma al régimen de partidos y financiamiento electoral ante Congreso de la Unión.",
        "dias_compromiso": 21,
    },
    {
        "texto": "Establecer mesa de diálogo con organizaciones civiles ambientales sobre gestión de residuos sólidos en CDMX con reporte mensual público.",
        "dias_compromiso": 75,
    },
    {
        "texto": "Impulsar agenda legislativa local MC CDMX sobre paridad de género en candidaturas a alcaldías 2027 con compromiso 50/50 en todas las demarcaciones.",
        "dias_compromiso": 120,
    },
    {
        "texto": "Transparentar vía portal web el registro de asesores, equipo de comunicación y honorarios asociados a la Coordinación de la Comisión Operativa.",
        "dias_compromiso": 14,
    },
    {
        "texto": "Coordinar operativo de acompañamiento ciudadano para consulta MC CDMX sobre prioridades 2027, con participación de 5000+ simpatizantes registrados.",
        "dias_compromiso": 105,
    },
]


async def seed_promesas_pina() -> int:
    """Seed the 10 Piña promesas idempotently. Returns # of rows inserted."""
    engine = create_async_engine(str(settings.DATABASE_URL), echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    inserted = 0
    async with async_session() as session:
        # Idempotency check
        existing = await session.scalar(
            select(func.count(PromesaDirigente.id)).where(
                PromesaDirigente.dirigente_id == DIRIGENTE_ID_PINA
            )
        )
        if existing and existing >= len(PROMESAS_PINA):
            print(
                f"Idempotent skip: Piña ya tiene {existing} promesas "
                f"(>= {len(PROMESAS_PINA)} target)."
            )
            await engine.dispose()
            return 0

        if existing:
            print(
                f"Piña tiene {existing} promesas actuales, se insertan solo las "
                f"faltantes para alcanzar {len(PROMESAS_PINA)}."
            )

        # Insert only what is missing
        to_insert = len(PROMESAS_PINA) - (existing or 0)
        today = date.today()
        for idx, p in enumerate(PROMESAS_PINA[-to_insert:] if existing else PROMESAS_PINA):
            fecha_compromiso = today + timedelta(days=p["dias_compromiso"])
            row = PromesaDirigente(
                dirigente_id=DIRIGENTE_ID_PINA,
                texto_promesa=p["texto"],
                fecha_compromiso=fecha_compromiso,
                estado=PromesaEstado.PENDIENTE,
                evidencia_url=None,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(row)
            inserted += 1

        await session.commit()

    await engine.dispose()
    print(f"Insertadas {inserted} promesas para dirigente_id={DIRIGENTE_ID_PINA}.")
    return inserted


if __name__ == "__main__":
    n = asyncio.run(seed_promesas_pina())
    sys.exit(0 if n >= 0 else 1)
