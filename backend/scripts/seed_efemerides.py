"""Seed catálogo de efemérides mexicanas + internacionales 2026.

Fuente: calendario CEO 2026-05-12 (sprint Pepe Monroy + Calendario).
Aplica a todos los dirigentes (catálogo global, no scoped por org).

Usage:
    docker exec crece-backend python /app/scripts/seed_efemerides.py

D-CALENDARIO-1.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.database import async_session_factory  # noqa: E402
from app.models.efemeride import (  # noqa: E402
    Efemeride,
    EfemerideAmbito,
    EfemerideTipo,
    EfemerideViralidad,
)


# Estructura: (mes, dia, titulo, tipo, ideas_politicas, viralidad, ambito)
EFEMERIDES_2026: list[tuple] = [
    # ENERO
    (1, 1, "Año Nuevo", "emocional", ["unidad", "nuevos comienzos", "balance"], "alta", "internacional"),
    (1, 4, "Día Mundial del Braille", "social", ["inclusión", "discapacidad visual"], "baja", "internacional"),
    (1, 6, "Día de Reyes", "familiar", ["entrega de juguetes", "rosca comunitaria", "tradición"], "alta", "nacional"),
    (1, 24, "Día Internacional de la Educación", "social", ["educación pública", "infancia", "futuro"], "media", "internacional"),
    (1, 26, "Día Mundial de la Educación Ambiental", "social", ["medio ambiente", "educación", "sustentabilidad"], "media", "internacional"),
    (1, 30, "Día Escolar de la No Violencia y la Paz", "social", ["paz", "no violencia", "escuelas"], "media", "internacional"),

    # FEBRERO
    (2, 2, "Día de la Candelaria", "familiar", ["tradición mexicana", "fe", "convivencia"], "alta", "nacional"),
    (2, 5, "Promulgación de la Constitución Mexicana", "civica", ["valores constitucionales", "orgullo nacional", "instituciones"], "alta", "nacional"),
    (2, 14, "Día del Amor y la Amistad", "emocional", ["valores familiares", "amistad", "comunidad"], "alta", "internacional"),
    (2, 19, "Día del Ejército Mexicano", "civica", ["respeto a instituciones", "seguridad", "patria"], "media", "nacional"),
    (2, 20, "Día Mundial de la Justicia Social", "social", ["justicia social", "equidad", "derechos"], "media", "internacional"),
    (2, 24, "Día de la Bandera", "civica", ["orgullo nacional", "símbolos patrios", "identidad"], "alta", "nacional"),

    # MARZO
    (3, 1, "Día de la Cero Discriminación", "social", ["inclusión", "diversidad", "derechos"], "media", "internacional"),
    (3, 8, "Día Internacional de la Mujer", "social", ["mujeres líderes", "derechos", "equidad de género"], "alta", "internacional"),
    (3, 18, "Expropiación Petrolera", "civica", ["soberanía", "historia nacional", "recursos"], "alta", "nacional"),
    (3, 21, "Natalicio de Benito Juárez", "civica", ["historia nacional", "juarista", "instituciones"], "alta", "nacional"),
    (3, 22, "Día Mundial del Agua", "social", ["medio ambiente", "agua", "sustentabilidad"], "media", "internacional"),
    (3, 24, "Día Mundial de la Tuberculosis", "social", ["salud pública", "prevención"], "baja", "internacional"),

    # ABRIL
    (4, 2, "Día Mundial del Autismo", "social", ["inclusión", "neurodiversidad", "familias"], "media", "internacional"),
    (4, 7, "Día Mundial de la Salud", "social", ["salud pública", "bienestar", "prevención"], "media", "internacional"),
    (4, 22, "Día Internacional de la Madre Tierra", "social", ["medio ambiente", "sustentabilidad", "naturaleza"], "alta", "internacional"),
    (4, 23, "Día Mundial del Libro", "social", ["cultura", "lectura", "educación"], "media", "internacional"),
    (4, 30, "Día del Niño", "emocional", ["actividades infantiles", "infancia", "futuro"], "alta", "nacional"),

    # MAYO
    (5, 1, "Día del Trabajo", "civica", ["reconocimiento a trabajadores", "derechos laborales", "dignidad"], "alta", "internacional"),
    (5, 5, "Batalla de Puebla (5 de mayo)", "civica", ["historia nacional", "orgullo", "resistencia"], "alta", "nacional"),
    (5, 8, "Día Mundial de la Cruz Roja", "social", ["humanitarismo", "voluntariado", "solidaridad"], "baja", "internacional"),
    (5, 10, "Día de las Madres", "emocional", ["homenaje a madres", "familia", "amor"], "alta", "nacional"),
    (5, 15, "Día del Maestro", "emocional", ["educación", "reconocimiento docente", "infancia"], "alta", "nacional"),
    (5, 17, "Día Internacional contra la Homofobia", "social", ["diversidad", "derechos LGBT+", "inclusión"], "media", "internacional"),
    (5, 23, "Día del Estudiante", "emocional", ["juventud", "educación", "futuro"], "media", "nacional"),
    (5, 28, "Día Internacional de Acción por la Salud de las Mujeres", "social", ["salud femenina", "derechos", "prevención"], "media", "internacional"),

    # JUNIO
    (6, 1, "Día de la Marina", "civica", ["instituciones", "soberanía", "mar"], "media", "nacional"),
    (6, 5, "Día Mundial del Medio Ambiente", "social", ["sustentabilidad", "ecología", "futuro"], "alta", "internacional"),
    (6, 14, "Día Mundial del Donante de Sangre", "social", ["solidaridad", "salud", "altruismo"], "baja", "internacional"),
    (6, 20, "Día Mundial de los Refugiados", "social", ["migración", "humanitarismo", "derechos"], "media", "internacional"),
    (6, 21, "Día del Padre", "emocional", ["homenaje a padres", "familia", "valores"], "alta", "nacional"),
    (6, 24, "Día Internacional contra la Contaminación", "social", ["medio ambiente", "salud", "responsabilidad"], "baja", "internacional"),

    # JULIO
    (7, 7, "Día Internacional de la Conservación del Suelo", "social", ["agricultura", "sustentabilidad", "campo"], "baja", "internacional"),
    (7, 11, "Día Mundial de la Población", "social", ["demografía", "desarrollo", "futuro"], "baja", "internacional"),
    (7, 18, "Fallecimiento de Benito Juárez", "civica", ["historia nacional", "instituciones", "legado"], "media", "nacional"),
    (7, 30, "Día Internacional de la Amistad", "emocional", ["comunidad", "valores", "cercanía"], "media", "internacional"),

    # AGOSTO
    (8, 9, "Día Internacional de los Pueblos Indígenas", "social", ["pueblos originarios", "inclusión", "cultura"], "media", "internacional"),
    (8, 12, "Día Internacional de la Juventud", "emocional", ["juventud", "futuro", "oportunidades"], "alta", "internacional"),
    (8, 19, "Día Mundial de la Asistencia Humanitaria", "social", ["humanitarismo", "solidaridad"], "baja", "internacional"),
    (8, 28, "Día del Adulto Mayor", "emocional", ["adultos mayores", "respeto", "programas sociales"], "alta", "nacional"),

    # SEPTIEMBRE
    (9, 13, "Niños Héroes", "civica", ["patriotismo", "historia", "valor"], "media", "nacional"),
    (9, 15, "Grito de Independencia", "civica", ["patriotismo", "fiesta nacional", "unidad"], "alta", "nacional"),
    (9, 16, "Independencia de México", "civica", ["patriotismo", "orgullo nacional", "historia"], "alta", "nacional"),
    (9, 19, "Día Nacional de Protección Civil", "civica", ["sismos 1985 y 2017", "memoria", "prevención"], "alta", "nacional"),
    (9, 21, "Día Internacional de la Paz", "social", ["paz", "diálogo", "valores"], "media", "internacional"),
    (9, 27, "Consumación de la Independencia", "civica", ["historia nacional", "soberanía"], "media", "nacional"),

    # OCTUBRE
    (10, 1, "Día Internacional de las Personas Adultas Mayores", "social", ["adultos mayores", "inclusión", "programas"], "media", "internacional"),
    (10, 2, "Movimiento Estudiantil de 1968", "civica", ["memoria histórica", "democracia", "estudiantes"], "alta", "nacional"),
    (10, 10, "Día Mundial de la Salud Mental", "social", ["salud mental", "bienestar", "prevención"], "alta", "internacional"),
    (10, 12, "Día de la Nación Pluricultural", "social", ["diversidad", "pueblos indígenas", "identidad"], "media", "nacional"),
    (10, 16, "Día Mundial de la Alimentación", "social", ["programas alimentarios", "nutrición", "campo"], "media", "internacional"),
    (10, 19, "Día Mundial de la Lucha contra el Cáncer de Mama", "social", ["salud femenina", "prevención", "solidaridad"], "alta", "internacional"),
    (10, 24, "Día de las Naciones Unidas", "social", ["cooperación", "paz", "internacional"], "baja", "internacional"),

    # NOVIEMBRE
    (11, 1, "Día de Muertos (Todos los Santos)", "familiar", ["tradiciones mexicanas", "memoria", "familia"], "alta", "nacional"),
    (11, 2, "Día de Muertos (Fieles Difuntos)", "familiar", ["tradiciones mexicanas", "memoria", "familia"], "alta", "nacional"),
    (11, 20, "Revolución Mexicana", "civica", ["historia nacional", "justicia social", "lucha"], "alta", "nacional"),
    (11, 25, "Día Internacional de la Eliminación de la Violencia contra la Mujer", "social", ["mujeres", "justicia", "prevención"], "alta", "internacional"),

    # DICIEMBRE
    (12, 1, "Día Mundial de la Lucha contra el VIH/SIDA", "social", ["salud", "prevención", "inclusión"], "media", "internacional"),
    (12, 3, "Día Internacional de las Personas con Discapacidad", "social", ["inclusión", "derechos", "accesibilidad"], "media", "internacional"),
    (12, 10, "Día de los Derechos Humanos", "social", ["derechos", "justicia", "dignidad"], "media", "internacional"),
    (12, 12, "Día de la Virgen de Guadalupe", "familiar", ["fe", "tradición", "identidad"], "alta", "nacional"),
    (12, 24, "Nochebuena", "familiar", ["familia", "tradición", "convivencia"], "alta", "nacional"),
    (12, 25, "Navidad", "familiar", ["familia", "fe", "valores"], "alta", "internacional"),
    (12, 28, "Día de los Inocentes", "familiar", ["tradición", "humor", "cercanía"], "media", "nacional"),
    (12, 31, "Fin de Año", "emocional", ["balance anual", "agradecimiento", "esperanza"], "alta", "internacional"),
]


async def seed() -> None:
    async with async_session_factory() as session:
        # Check existing
        existing = (await session.execute(select(Efemeride))).scalars().all()
        if existing:
            print(f"[seed_efemerides] {len(existing)} efemerides ya existen. Abortando para no duplicar.")
            print("[seed_efemerides] Para reseed: TRUNCATE efemerides RESTART IDENTITY; y reintentar.")
            return

        for mes, dia, titulo, tipo, ideas, vir, amb in EFEMERIDES_2026:
            ef = Efemeride(
                mes=mes,
                dia=dia,
                titulo=titulo,
                tipo=EfemerideTipo(tipo),
                ideas_politicas=ideas,
                viralidad=EfemerideViralidad(vir),
                ambito=EfemerideAmbito(amb),
                is_active=True,
            )
            session.add(ef)

        await session.commit()
        count = len((await session.execute(select(Efemeride))).scalars().all())
        print(f"[seed_efemerides] {count} efemerides insertadas ✓")


if __name__ == "__main__":
    asyncio.run(seed())
