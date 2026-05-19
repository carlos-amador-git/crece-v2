"""Seed synthetic citizens with INEGI Census 2020 CDMX distributions.

Creates 200+ ciudadanos with demographically realistic distributions
based on INEGI Censo de Población y Vivienda 2020 data for CDMX.

EVERY record has data_source='synthetic_census_2020' — clearly synthetic,
NEVER to be confused with real citizen data.

Usage:
    cd backend
    python -m scripts.seed_synthetic_citizens
"""

from __future__ import annotations

import asyncio
import logging
import random
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.ciudadano import (
    Escolaridad,
    Genero,
    IntencionVotoCiudadano,
    NivelInteres,
    RangoEdad,
)
from app.models.encuesta import NivelCerteza

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── INEGI Census 2020 CDMX distributions ─────────────────────────────────
# Source: INEGI Censo de Población y Vivienda 2020
# https://www.inegi.org.mx/programas/ccpv/2020/

# Age distribution (18+ only, voting age) — CDMX
# Total CDMX 18+: ~7.2M. Percentages from pyramid.
AGE_DISTRIBUTION: dict[RangoEdad, float] = {
    RangoEdad.E_18_25: 0.18,  # 18-25: ~18%
    RangoEdad.E_26_35: 0.22,  # 26-35: ~22% (largest group)
    RangoEdad.E_36_45: 0.20,  # 36-45: ~20%
    RangoEdad.E_46_55: 0.17,  # 46-55: ~17%
    RangoEdad.E_56_65: 0.13,  # 56-65: ~13%
    RangoEdad.E_65_PLUS: 0.10,  # 65+: ~10%
}

# Gender distribution — CDMX is ~52% F, 48% M (INEGI 2020)
GENDER_DISTRIBUTION: dict[Genero, float] = {
    Genero.F: 0.52,
    Genero.M: 0.48,
}

# Education (escolaridad) distribution — CDMX 15+ (INEGI 2020)
# CDMX has highest education levels in Mexico
EDUCATION_DISTRIBUTION: dict[Escolaridad, float] = {
    Escolaridad.SIN_ESTUDIOS: 0.02,  # ~2%
    Escolaridad.PRIMARIA: 0.08,  # ~8%
    Escolaridad.SECUNDARIA: 0.18,  # ~18%
    Escolaridad.PREPARATORIA: 0.27,  # ~27%
    Escolaridad.UNIVERSIDAD: 0.35,  # ~35% (CDMX is high)
    Escolaridad.POSGRADO: 0.10,  # ~10%
}

# Alcaldías and their approximate population share (INEGI 2020)
ALCALDIAS: dict[str, float] = {
    "Iztapalapa": 0.19,
    "Gustavo A. Madero": 0.12,
    "Álvaro Obregón": 0.08,
    "Tlalpan": 0.07,
    "Coyoacán": 0.07,
    "Cuauhtémoc": 0.05,
    "Azcapotzalco": 0.04,
    "Iztacalco": 0.04,
    "Benito Juárez": 0.04,
    "Venustiano Carranza": 0.04,
    "Miguel Hidalgo": 0.04,
    "Xochimilco": 0.04,
    "Tláhuac": 0.04,
    "La Magdalena Contreras": 0.03,
    "Milpa Alta": 0.01,
    "Cuajimalpa de Morelos": 0.02,
}

# Alcaldía → seccion mapping (existing + new secciones to create)
ALCALDIA_SECCIONES: dict[str, str] = {
    "Azcapotzalco": "0901-0001",
    "Coyoacán": "0901-0050",
    "Gustavo A. Madero": "0901-0100",
    "Iztapalapa": "0901-0200",
    "Tlalpan": "0901-0300",
    "Álvaro Obregón": "0901-0400",
    "Cuauhtémoc": "0901-0500",
    "Iztacalco": "0901-0600",
    "Benito Juárez": "0901-0700",
    "Venustiano Carranza": "0901-0800",
    "Miguel Hidalgo": "0901-0900",
    "Xochimilco": "0901-1000",
    "Tláhuac": "0901-1100",
    "La Magdalena Contreras": "0901-1200",
    "Milpa Alta": "0901-1300",
    "Cuajimalpa de Morelos": "0901-1400",
}

# Vote intention distribution — based on CDMX 2024 election results + polls
# MC historically gets ~8-12% in CDMX
INTENCION_VOTO_DISTRIBUTION: dict[IntencionVotoCiudadano, float] = {
    IntencionVotoCiudadano.MORENA: 0.35,
    IntencionVotoCiudadano.MC: 0.10,
    IntencionVotoCiudadano.PAN: 0.12,
    IntencionVotoCiudadano.PRI: 0.05,
    IntencionVotoCiudadano.PVEM: 0.04,
    IntencionVotoCiudadano.PT: 0.03,
    IntencionVotoCiudadano.OTRO: 0.03,
    IntencionVotoCiudadano.INDECISO: 0.18,
    IntencionVotoCiudadano.NO_RESPONDE: 0.10,
}

# Common Mexican first names by gender (top 20 each)
NOMBRES_M = [
    "José", "Juan", "Luis", "Carlos", "Miguel", "Ángel", "Francisco", "David",
    "Daniel", "Jorge", "Fernando", "Ricardo", "Alejandro", "Antonio", "Rafael",
    "Pedro", "Sergio", "Roberto", "Eduardo", "Arturo",
]
NOMBRES_F = [
    "María", "Guadalupe", "Juana", "Patricia", "Rosa", "Margarita", "Elizabeth",
    "Ana", "Leticia", "Verónica", "Martha", "Adriana", "Claudia", "Gabriela",
    "Silvia", "Laura", "Carmen", "Sandra", "Teresa", "Alejandra",
]
APELLIDOS = [
    "García", "Hernández", "López", "Martínez", "González", "Rodríguez",
    "Pérez", "Sánchez", "Ramírez", "Torres", "Flores", "Rivera", "Gómez",
    "Díaz", "Cruz", "Morales", "Reyes", "Gutiérrez", "Ortiz", "Jiménez",
    "Ruiz", "Mendoza", "Aguilar", "Castillo", "Romero", "Vargas", "Medina",
    "Chávez", "Vázquez", "Castro",
]


def _weighted_choice(distribution: dict, rng: random.Random) -> str:
    """Pick a random item from a weighted distribution dict."""
    items = list(distribution.keys())
    weights = list(distribution.values())
    return rng.choices(items, weights=weights, k=1)[0]


def _generate_phone(rng: random.Random) -> str | None:
    """Generate a realistic CDMX phone number or None (30% chance)."""
    if rng.random() < 0.30:
        return None
    return f"55{rng.randint(1000, 9999)}{rng.randint(1000, 9999)}"


def _generate_email(nombre: str, apellido: str, rng: random.Random) -> str | None:
    """Generate a plausible email or None (50% chance)."""
    if rng.random() < 0.50:
        return None
    providers = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com.mx"]
    clean_nombre = nombre.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    clean_apellido = apellido.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    return f"{clean_nombre}.{clean_apellido}{rng.randint(1, 999)}@{rng.choice(providers)}"


async def _ensure_secciones(db: AsyncSession) -> dict[str, int]:
    """Ensure all CDMX alcaldía secciones exist. Return seccion_code → id mapping."""
    seccion_map: dict[str, int] = {}

    for alcaldia, seccion_code in ALCALDIA_SECCIONES.items():
        result = await db.execute(
            text("SELECT id FROM secciones_electorales WHERE seccion = :s"),
            {"s": seccion_code},
        )
        row = result.scalar_one_or_none()
        if row:
            seccion_map[seccion_code] = row
        else:
            r = await db.execute(
                text("""
                    INSERT INTO secciones_electorales (seccion, estado, distrito_federal, distrito_local, municipio)
                    VALUES (:seccion, 'Ciudad de México', :df, :dl, :municipio)
                    RETURNING id
                """),
                {
                    "seccion": seccion_code,
                    "df": seccion_code.split("-")[1][:2].lstrip("0") or "1",
                    "dl": seccion_code.split("-")[1][:2].lstrip("0") or "1",
                    "municipio": alcaldia,
                },
            )
            seccion_map[seccion_code] = r.scalar_one()
            logger.info("Created seccion %s (%s)", seccion_code, alcaldia)

    await db.flush()
    return seccion_map


async def _ensure_data_source_column(db: AsyncSession) -> None:
    """Add data_source column to ciudadanos if it doesn't exist."""
    result = await db.execute(
        text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'ciudadanos' AND column_name = 'data_source'
        """)
    )
    if result.scalar_one_or_none() is None:
        await db.execute(
            text("ALTER TABLE ciudadanos ADD COLUMN data_source VARCHAR(100)")
        )
        await db.flush()
        logger.info("Added data_source column to ciudadanos")


async def seed_synthetic_citizens(
    n_citizens: int = 200,
    seed: int = 42,
) -> dict:
    """Seed n_citizens synthetic citizens with INEGI-based distributions.

    Returns summary statistics.
    """
    rng = random.Random(seed)

    async with async_session_factory() as db:
        # Step 1: Ensure DB schema is ready
        await _ensure_data_source_column(db)
        seccion_map = await _ensure_secciones(db)

        # Build alcaldía → seccion_id lookup
        alcaldia_to_seccion_id: dict[str, int] = {}
        for alcaldia, seccion_code in ALCALDIA_SECCIONES.items():
            alcaldia_to_seccion_id[alcaldia] = seccion_map[seccion_code]

        # Step 2: Generate citizens
        ciudadanos_created = 0
        encuestas_created = 0
        stats = {
            "edad": {},
            "genero": {},
            "escolaridad": {},
            "alcaldia": {},
            "intencion_voto": {},
        }

        for i in range(n_citizens):
            # Demographics from INEGI distributions
            edad_rango = _weighted_choice(AGE_DISTRIBUTION, rng)
            genero = _weighted_choice(GENDER_DISTRIBUTION, rng)
            escolaridad = _weighted_choice(EDUCATION_DISTRIBUTION, rng)
            alcaldia = _weighted_choice(ALCALDIAS, rng)

            # Name based on gender
            if genero == Genero.F:
                nombre = rng.choice(NOMBRES_F)
            else:
                nombre = rng.choice(NOMBRES_M)

            apellido_p = rng.choice(APELLIDOS)
            apellido_m = rng.choice(APELLIDOS)

            seccion_id = alcaldia_to_seccion_id[alcaldia]

            # Political engagement (correlated with age and education)
            age_factor = {"18-25": 0.3, "26-35": 0.5, "36-45": 0.6, "46-55": 0.7, "56-65": 0.8, "65+": 0.6}
            edu_factor = {
                "sin_estudios": 0.2, "primaria": 0.3, "secundaria": 0.4,
                "preparatoria": 0.5, "universidad": 0.7, "posgrado": 0.8,
            }
            engagement_score = (
                age_factor.get(edad_rango, 0.5) * 0.4
                + edu_factor.get(escolaridad, 0.5) * 0.6
            )

            # Interest level based on engagement
            if engagement_score > 0.65:
                nivel_interes = NivelInteres.ALTO
            elif engagement_score > 0.45:
                nivel_interes = NivelInteres.MEDIO
            elif engagement_score > 0.25:
                nivel_interes = NivelInteres.BAJO
            else:
                nivel_interes = NivelInteres.DESCONOCIDO

            # MC sympathy (~15% of those with medium+ interest)
            es_simpatizante = (
                nivel_interes in (NivelInteres.ALTO, NivelInteres.MEDIO)
                and rng.random() < 0.15
            )
            es_promotor = es_simpatizante and rng.random() < 0.25

            telefono = _generate_phone(rng)
            email = _generate_email(nombre, apellido_p, rng)

            # Problematicas (CDMX top issues — INEGI ENVIPE 2023)
            problematicas_pool = [
                "inseguridad", "transporte_publico", "baches",
                "contaminacion", "agua", "desempleo", "corrupcion",
                "servicios_salud", "vivienda", "educacion",
            ]
            n_problemas = rng.choices([0, 1, 2, 3], weights=[0.2, 0.4, 0.3, 0.1])[0]
            problematicas = rng.sample(problematicas_pool, min(n_problemas, len(problematicas_pool)))

            # Insert ciudadano via raw SQL to include data_source
            result = await db.execute(
                text("""
                    INSERT INTO ciudadanos (
                        nombre, apellido_paterno, apellido_materno, seccion_id,
                        telefono, email, edad_rango, genero, nivel_interes,
                        es_simpatizante_mc, es_promotor, escolaridad,
                        registrado_por_id, problematicas, colonia,
                        data_source, created_at, updated_at
                    ) VALUES (
                        :nombre, :ap, :am, :seccion_id,
                        :telefono, :email, :edad_rango, :genero, :nivel_interes,
                        :es_simpatizante, :es_promotor, :escolaridad,
                        1, :problematicas, :colonia,
                        'synthetic_census_2020', :now, :now
                    ) RETURNING id
                """),
                {
                    "nombre": nombre,
                    "ap": apellido_p,
                    "am": apellido_m,
                    "seccion_id": seccion_id,
                    "telefono": telefono,
                    "email": email,
                    "edad_rango": edad_rango.name if hasattr(edad_rango, 'name') else str(edad_rango),
                    "genero": genero.name if hasattr(genero, 'name') else str(genero),
                    "nivel_interes": nivel_interes.name,
                    "es_simpatizante": es_simpatizante,
                    "es_promotor": es_promotor,
                    "escolaridad": escolaridad.name if hasattr(escolaridad, 'name') else str(escolaridad),
                    "problematicas": '{"issues": ' + str(problematicas).replace("'", '"') + '}' if problematicas else None,
                    "colonia": f"Col. Sintética {alcaldia[:8]}-{i + 1}",
                    "now": datetime.now(UTC),
                },
            )
            ciudadano_id = result.scalar_one()
            ciudadanos_created += 1

            # Track stats
            stats["edad"][edad_rango] = stats["edad"].get(edad_rango, 0) + 1
            stats["genero"][genero] = stats["genero"].get(genero, 0) + 1
            stats["escolaridad"][escolaridad] = stats["escolaridad"].get(escolaridad, 0) + 1
            stats["alcaldia"][alcaldia] = stats["alcaldia"].get(alcaldia, 0) + 1

            # Create encuesta for ~70% of citizens (needed for ML training)
            if rng.random() < 0.70:
                intencion = _weighted_choice(INTENCION_VOTO_DISTRIBUTION, rng)

                # Adjust intention based on sympathy
                if es_simpatizante and rng.random() < 0.80:
                    intencion = IntencionVotoCiudadano.MC

                certeza_options = [NivelCerteza.ALTA, NivelCerteza.MEDIA, NivelCerteza.BAJA]
                certeza_weights = [0.3, 0.5, 0.2]
                certeza = rng.choices(certeza_options, weights=certeza_weights)[0]

                fecha = date.today() - timedelta(days=rng.randint(1, 90))

                await db.execute(
                    text("""
                        INSERT INTO encuestas (
                            ciudadano_id, encuestador_id, seccion_id,
                            intencion_voto, nivel_certeza, fecha_encuesta,
                            motivacion, created_at
                        ) VALUES (
                            :cid, 1, :seccion_id,
                            :intencion, :certeza, :fecha,
                            :motivacion, :now
                        )
                    """),
                    {
                        "cid": ciudadano_id,
                        "seccion_id": seccion_id,
                        "intencion": intencion.name if hasattr(intencion, 'name') else str(intencion),
                        "certeza": certeza.name,
                        "fecha": fecha,
                        "motivacion": f"Encuesta sintética censo 2020 — {alcaldia}",
                        "now": datetime.now(UTC),
                    },
                )
                encuestas_created += 1
                stats["intencion_voto"][intencion] = stats["intencion_voto"].get(intencion, 0) + 1

        await db.commit()

        logger.info("=" * 60)
        logger.info("SYNTHETIC SEED COMPLETE")
        logger.info("=" * 60)
        logger.info("Ciudadanos created: %d", ciudadanos_created)
        logger.info("Encuestas created: %d", encuestas_created)
        logger.info("data_source: synthetic_census_2020")
        logger.info("-" * 40)
        logger.info("DISTRIBUTION VERIFICATION:")
        for category, counts in stats.items():
            logger.info("  %s:", category)
            total = sum(counts.values())
            for key, count in sorted(counts.items(), key=lambda x: -x[1]):
                pct = count / total * 100 if total > 0 else 0
                logger.info("    %-25s %4d (%5.1f%%)", key, count, pct)

        return {
            "ciudadanos_created": ciudadanos_created,
            "encuestas_created": encuestas_created,
            "data_source": "synthetic_census_2020",
            "distributions": {
                k: {str(kk): vv for kk, vv in v.items()}
                for k, v in stats.items()
            },
        }


async def train_and_score() -> dict:
    """Train the ML model and score all citizens."""
    from app.services.voter_scoring import voter_scoring_engine

    async with async_session_factory() as db:
        # Train
        logger.info("Training RandomForestClassifier...")
        train_result = voter_scoring_engine.train(db)
        if asyncio.iscoroutine(train_result):
            train_result = await train_result
        logger.info("Training result: %s", train_result)

        # Score all
        logger.info("Scoring all citizens...")
        score_result = await voter_scoring_engine.score_all(db)
        logger.info("Scoring result: %s", score_result)

        await db.commit()

        return {
            "training": train_result,
            "scoring": score_result,
        }


async def main() -> None:
    """Full pipeline: seed + train + score."""
    logger.info("Starting synthetic citizen seed (INEGI Census 2020 CDMX distributions)")

    # Seed
    seed_result = await seed_synthetic_citizens(n_citizens=200, seed=42)

    # Train and score
    ml_result = await train_and_score()

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("  Citizens: %d", seed_result["ciudadanos_created"])
    logger.info("  Encuestas: %d", seed_result["encuestas_created"])
    logger.info("  ML Accuracy: %s", ml_result["training"].get("accuracy", "N/A"))
    logger.info("  ML F1: %s", ml_result["training"].get("f1_score", "N/A"))
    logger.info("  Scored: %d", ml_result["scoring"]["total_scored"])
    logger.info("  Segments: %s", ml_result["scoring"]["segmento_breakdown"])
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
