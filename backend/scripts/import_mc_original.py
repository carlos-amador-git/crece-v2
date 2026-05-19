"""D-DATA-01 Ruta C — importar CRECE Oracle APEX legacy al dev DB.

Ruta C: filtrar ciudadanos a 3 alcaldías piloto (CUAUHTEMOC, BENITO
JUAREZ, MIGUEL HIDALGO). master_catalogo se importa COMPLETO porque no
tiene PII. Promotores se filtran a los asignados a las 3 alcaldías.

Uso (gated por env var):
    CRECE_MC_RAW_DIR=/app/data/raw/mc_original \\
    docker exec crece-backend python -m scripts.import_mc_original

Orden:
    1. master_catalogo.csv → unidades_territoriales (full, 5,548 rows)
    2. users (promotores).csv → promotores_legacy (filtrado)
    3. ciudadanos.csv → ciudadanos_legacy (filtrado)
    4. referencia_*.csv → linkear ciudadano ↔ promotor via promotor_legacy_id

El script es idempotente via UPSERT por `legacy_id` / `legacy_user_id`.
Puede re-correrse sin duplicar.
"""
from __future__ import annotations

import asyncio
import csv
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("import_mc_original")

# Ruta C — alcaldías piloto, en formato CAPS del master_catalogo y del CSV
PILOT_ALCALDIAS = {"CUAUHTEMOC", "BENITO JUAREZ", "MIGUEL HIDALGO"}

# Mapeo al nombre canónico INEGI en `alcaldias_cdmx`
LEGACY_TO_INEGI_ALCALDIA = {
    "CUAUHTEMOC": "Cuauhtémoc",
    "BENITO JUAREZ": "Benito Juárez",
    "MIGUEL HIDALGO": "Miguel Hidalgo",
    "ALVARO OBREGON": "Álvaro Obregón",
    "AZCAPOTZALCO": "Azcapotzalco",
    "COYOACAN": "Coyoacán",
    "CUAJIMALPA DE MORELOS": "Cuajimalpa de Morelos",
    "GUSTAVO A. MADERO": "Gustavo A. Madero",
    "IZTACALCO": "Iztacalco",
    "IZTAPALAPA": "Iztapalapa",
    "LA MAGDALENA CONTRERAS": "La Magdalena Contreras",
    "MILPA ALTA": "Milpa Alta",
    "TLAHUAC": "Tláhuac",
    "TLALPAN": "Tlalpan",
    "VENUSTIANO CARRANZA": "Venustiano Carranza",
    "XOCHIMILCO": "Xochimilco",
}

# Org target: MC CDMX root (id=3 per D-DX-01). El caller puede override
# vía env var si corre contra una DB diferente.
DEFAULT_ORG_ID = int(os.environ.get("CRECE_IMPORT_ORG_ID", "3"))


def _raw_dir() -> Path:
    """Resolve raw CSV directory from env, or fall back to the standard path."""
    env_path = os.environ.get("CRECE_MC_RAW_DIR")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parent.parent / "data" / "raw" / "mc_original"


def _parse_float(s: str | None) -> float | None:
    if not s:
        return None
    try:
        return float(s.strip())
    except (ValueError, AttributeError):
        return None


def _parse_int(s: str | None) -> int | None:
    if not s:
        return None
    try:
        v = int(s.strip())
        # Sanity: pgsql int4 range
        if v < -2147483648 or v > 2147483647:
            return None
        return v
    except (ValueError, AttributeError):
        return None


def _parse_age(s: str | None) -> int | None:
    """Parse age with sanity check — CSV has phone values in EDAD column."""
    v = _parse_int(s)
    if v is None or v < 0 or v > 120:
        return None
    return v


def _parse_oracle_date(s: str | None) -> datetime | None:
    """Oracle APEX format: '10-OCT-23 08.37.44.695572000 PM +00:00'.

    We only extract the date + hour; the nanosecond fraction and TZ are
    parsed leniently.
    """
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    try:
        from datetime import datetime as dt

        # Normalize Oracle's "AM/PM" + 9-digit fraction
        # Example: 10-OCT-23 08.37.44.695572000 PM +00:00
        parts = s.split()
        if len(parts) < 3:
            return None
        day_part = parts[0]  # 10-OCT-23
        time_part = parts[1]  # 08.37.44.695572000
        ampm = parts[2]  # PM
        # Truncate the fraction to 6 digits (Python max)
        time_parts = time_part.split(".")
        if len(time_parts) >= 4:
            time_parts[3] = time_parts[3][:6]
            time_part = ".".join(time_parts)
        return dt.strptime(
            f"{day_part} {time_part} {ampm}",
            "%d-%b-%y %H.%M.%S.%f %p",
        ).replace(tzinfo=UTC)
    except Exception:
        return None


def _parse_dob(s: str | None) -> datetime | None:
    """FECHA_DE_NACIMIENTO es texto libre — best effort."""
    if not s or not s.strip():
        return None
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


async def _load_alcaldia_map(session: AsyncSession) -> dict[str, int]:
    """Return mapping from legacy-style uppercase nombre → alcaldias_cdmx.id."""
    result = await session.execute(text("SELECT id, nombre FROM alcaldias_cdmx"))
    by_inegi = {nombre: aid for aid, nombre in result.all()}
    # Invertir el map para que pueda mapear desde el nombre legacy uppercase
    out: dict[str, int] = {}
    for legacy_name, inegi_name in LEGACY_TO_INEGI_ALCALDIA.items():
        if inegi_name in by_inegi:
            out[legacy_name] = by_inegi[inegi_name]
    return out


async def import_unidades_territoriales(
    session: AsyncSession, csv_path: Path, alcaldia_map: dict[str, int]
) -> int:
    log.info("importing unidades_territoriales from %s", csv_path)
    inserted = 0
    with open(csv_path, encoding="latin-1", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            legacy_id = row["ID"].strip()
            alcaldia_nombre_raw = row["ALCALDIA_2024"].strip()
            if not legacy_id or not alcaldia_nombre_raw:
                continue
            alc_id = alcaldia_map.get(alcaldia_nombre_raw)

            params = {
                "legacy_id": legacy_id,
                "alcaldia_id": alc_id,
                "alcaldia_nombre": alcaldia_nombre_raw,
                "clave_unidad_territorial": row.get(
                    "CLAVE_UNIDAD_TERRITORIAL", ""
                ).strip(),
                "cabecera_nombre": row.get(
                    "CABECERA_TERRITORIAL__UNIDAD_TERRITORIAL_", ""
                ).strip()
                or None,
                "parcial_completa": row.get("PARCIAL_COMPLETA", "").strip() or None,
                "seccion_2024": row.get("SECCION_2024", "").strip(),
                "dtto_federal_2024": row.get("DTTO_FED_2024", "").strip() or None,
                "dtto_local_2024": row.get("DTTO_LOCAL_2024", "").strip() or None,
                "circunscripcion_2024": row.get("CIRCUNSCRIPCION_2024", "").strip()
                or None,
                "circunscripcion_2022": row.get("CIRCUNSCRIPCION_2022", "").strip()
                or None,
                "estrato": (row.get("ESTRATO", "").strip() or None),
                "nivel_socioeconomico_resumen": (
                    row.get("RESUMEN_NIVEL_SOCIOECONOMICO", "").strip() or None
                ),
                "grado_promedio_estudios": _parse_float(
                    row.get("GRADO_PROMEDIO_ESTUDIOS")
                ),
                "p_viv_inter": _parse_float(row.get("P_VIV_INTER")),
                "lista_nominal_2023": _parse_int(row.get("LISTA_NOMINAL_2023")),
                "volatilidad": _parse_float(row.get("VOLATILIDAD")),
                "categoria": row.get("CATEGORIA", "").strip() or None,
            }

            await session.execute(
                text(
                    """
                    INSERT INTO unidades_territoriales (
                        legacy_id, alcaldia_id, alcaldia_nombre, clave_unidad_territorial,
                        cabecera_nombre, parcial_completa, seccion_2024,
                        dtto_federal_2024, dtto_local_2024, circunscripcion_2024,
                        circunscripcion_2022, estrato, nivel_socioeconomico_resumen,
                        grado_promedio_estudios, p_viv_inter, lista_nominal_2023,
                        volatilidad, categoria
                    )
                    VALUES (
                        :legacy_id, :alcaldia_id, :alcaldia_nombre,
                        :clave_unidad_territorial, :cabecera_nombre,
                        :parcial_completa, :seccion_2024, :dtto_federal_2024,
                        :dtto_local_2024, :circunscripcion_2024,
                        :circunscripcion_2022, :estrato,
                        :nivel_socioeconomico_resumen, :grado_promedio_estudios,
                        :p_viv_inter, :lista_nominal_2023, :volatilidad,
                        :categoria
                    )
                    ON CONFLICT (legacy_id) DO UPDATE SET
                        alcaldia_id = EXCLUDED.alcaldia_id,
                        cabecera_nombre = EXCLUDED.cabecera_nombre,
                        estrato = EXCLUDED.estrato,
                        lista_nominal_2023 = EXCLUDED.lista_nominal_2023,
                        volatilidad = EXCLUDED.volatilidad,
                        categoria = EXCLUDED.categoria
                    """
                ),
                params,
            )
            inserted += 1
    await session.commit()
    log.info("unidades_territoriales upserted: %d", inserted)
    return inserted


async def import_promotores(
    session: AsyncSession,
    csv_path: Path,
    alcaldia_map: dict[str, int],
    pilot_project_ids: set[str],
) -> int:
    log.info("importing promotores_legacy from %s", csv_path)
    imported = 0
    skipped = 0
    with open(csv_path, encoding="latin-1", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            project_id = row.get("PROJECT_ID", "").strip()
            if project_id not in pilot_project_ids:
                skipped += 1
                continue

            legacy_user_id = row.get("USER_ID", "").strip()
            user_name = row.get("USER_NAME", "").strip()
            if not legacy_user_id or not user_name:
                continue

            # Alcaldia inferred via the pilot project_id→nombre map
            alc_nombre = pilot_project_ids[project_id] if isinstance(pilot_project_ids, dict) else None  # type: ignore
            alc_id = alcaldia_map.get(alc_nombre) if alc_nombre else None

            params = {
                "legacy_user_id": legacy_user_id,
                "org_id": DEFAULT_ORG_ID,
                "alcaldia_id": alc_id,
                "user_name": user_name,
                "password_hash_legacy": row.get("PASSWORD", "").strip() or None,
                "project_id_legacy": project_id,
                "enabled": row.get("ENABLED", "").strip() or None,
                "super_promotor": row.get("SUPER_PROMOTOR", "").strip() or None,
                "mega_promotor": row.get("MEGA_PROMOTOR", "").strip() or None,
                "super_promotor_cdmx": row.get("SUPER_PROMOTOR_CDMX", "").strip()
                or None,
                "distrito_federal": row.get("DISTRITO_FEDERAL", "").strip() or None,
                "distritos": row.get("DISTRITOS", "").strip() or None,
                "distrito_local": row.get("DISTRITO_LOCAL", "").strip() or None,
                "imported_at": datetime.now(UTC),
            }

            await session.execute(
                text(
                    """
                    INSERT INTO promotores_legacy (
                        legacy_user_id, org_id, alcaldia_id, user_name,
                        password_hash_legacy, project_id_legacy, enabled,
                        super_promotor, mega_promotor, super_promotor_cdmx,
                        distrito_federal, distritos, distrito_local, imported_at
                    )
                    VALUES (
                        :legacy_user_id, :org_id, :alcaldia_id, :user_name,
                        :password_hash_legacy, :project_id_legacy, :enabled,
                        :super_promotor, :mega_promotor, :super_promotor_cdmx,
                        :distrito_federal, :distritos, :distrito_local, :imported_at
                    )
                    ON CONFLICT (legacy_user_id) DO UPDATE SET
                        alcaldia_id = EXCLUDED.alcaldia_id,
                        enabled = EXCLUDED.enabled,
                        super_promotor = EXCLUDED.super_promotor,
                        mega_promotor = EXCLUDED.mega_promotor
                    """
                ),
                params,
            )
            imported += 1
    await session.commit()
    log.info("promotores_legacy upserted: %d (skipped non-pilot: %d)", imported, skipped)
    return imported


async def import_ciudadanos(
    session: AsyncSession,
    csv_path: Path,
    alcaldia_map: dict[str, int],
    seccion_to_alcaldia: dict[str, str],
    seccion_to_ut_id: dict[str, int],
    promotor_name_to_id: dict[str, int],
) -> int:
    log.info("importing ciudadanos_legacy from %s", csv_path)
    imported = 0
    skipped_non_pilot = 0
    with open(csv_path, encoding="latin-1", newline="") as f:
        reader = csv.DictReader(f)
        batch_size = 500
        batch: list[dict] = []
        for row in reader:
            seccion = row.get("SECCION", "").strip()
            alcaldia_legacy = seccion_to_alcaldia.get(seccion)
            if alcaldia_legacy not in PILOT_ALCALDIAS:
                skipped_non_pilot += 1
                continue

            legacy_id = row.get("ID", "").strip()
            if not legacy_id:
                continue

            alc_id = alcaldia_map.get(alcaldia_legacy) if alcaldia_legacy else None
            ut_id = seccion_to_ut_id.get(seccion)
            promotor_name = row.get("PROMOTOR_ID", "").strip()
            promotor_id = (
                promotor_name_to_id.get(promotor_name) if promotor_name else None
            )

            params = {
                "legacy_id": legacy_id,
                "org_id": DEFAULT_ORG_ID,
                "alcaldia_id": alc_id,
                "unidad_territorial_id": ut_id,
                "promotor_legacy_id": promotor_id,
                "nombre": row.get("NOMBRE", "").strip() or None,
                "apellido_paterno": row.get("APELLIDO_PATERNO", "").strip() or None,
                "apellido_materno": row.get("APELLIDO_MATERNO", "").strip() or None,
                "fecha_nacimiento": _parse_dob(row.get("FECHA_DE_NACIMIENTO")),
                "edad": _parse_age(row.get("EDAD")),
                "sexo": row.get("SEXO", "").strip() or None,
                "identidad_de_genero": row.get("IDENTIDAD_DE_GENERO", "").strip()
                or None,
                "email": row.get("EMAIL", "").strip() or None,
                "phone_01": row.get("PHONE_01", "").strip() or None,
                "phone_02": row.get("PHONE_02", "").strip() or None,
                "whatsapp": row.get("WHATSAPP", "").strip() or None,
                "calle": row.get("CALLE", "").strip() or None,
                "numero": row.get("NUMERO", "").strip() or None,
                "numero_interior": row.get("NUMERO_INTERIOR", "").strip() or None,
                "colonia_texto": row.get("COLONIA", "").strip() or None,
                "codigo_postal": row.get("CP", "").strip() or None,
                "municipio_texto": row.get("MUNICIPIO", "").strip() or None,
                "direccion_libre": row.get("DIRECCION", "").strip() or None,
                "manzana": row.get("MANZANA", "").strip() or None,
                "latitud": _parse_float(row.get("LATITUD")),
                "longitud": _parse_float(row.get("LONGITUD")),
                "latitud_cd": _parse_float(row.get("LATITUD_CD")),
                "longitud_cd": _parse_float(row.get("LONGITUD_CD")),
                "seccion": seccion or None,
                "cabecera_territorial": row.get("CABECERA_TERRITORIAL", "").strip()
                or None,
                "clave_electoral": row.get("CLAVE_ELECTORAL", "").strip() or None,
                "origen_ciudadano": row.get("ORIGEN_CIUDADANO", "").strip() or None,
                "rol": row.get("ROL", "").strip() or None,
                "ocupacion": row.get("OCUPACION", "").strip() or None,
                "nivel_educativo": row.get("NIVEL_EDUCATIVO", "").strip() or None,
                "nivel_participacion": row.get("NIVEL_PARTICIPACION", "").strip()
                or None,
                "disposicion_tiempo": row.get("DISPOSICION_TIEMPO", "").strip() or None,
                "temas_de_interes": row.get("TEMAS_DE_INTERES", "").strip() or None,
                "red_social": row.get("RED_SOCIAL", "").strip() or None,
                "red_social_descripcion": row.get("RED_SOCIAL_DESCRIPCION", "").strip()
                or None,
                "residencia_si_no": row.get("RESIDENCIA_SI_NO", "").strip() or None,
                "contactado": row.get("CONTACTADO", "").strip() or None,
                "respuesta": row.get("RESPUESTA", "").strip() or None,
                "lista": row.get("LISTA", "").strip() or None,
                "aprobado": row.get("APROBADO", "").strip() or None,
                "procesado": row.get("PROCESADO", "").strip() or None,
                "observaciones": row.get("OBSERVACIONES", "").strip() or None,
                "id_mc": row.get("ID_MC", "").strip() or None,
                "username_legacy": row.get("USERNAME", "").strip() or None,
                "project_id_legacy": row.get("PROJECT_ID", "").strip() or None,
                "created_legacy": _parse_oracle_date(row.get("CREATED")),
                "created_by_legacy": row.get("CREATED_BY", "").strip() or None,
                "updated_legacy": _parse_oracle_date(row.get("UPDATED")),
                "updated_by_legacy": row.get("UPDATED_BY", "").strip() or None,
                "imported_at": datetime.now(UTC),
            }
            batch.append(params)
            if len(batch) >= batch_size:
                imported += await _flush_ciudadano_batch(session, batch)
                batch = []
        if batch:
            imported += await _flush_ciudadano_batch(session, batch)
    await session.commit()
    log.info(
        "ciudadanos_legacy upserted: %d (skipped non-pilot: %d)",
        imported,
        skipped_non_pilot,
    )
    return imported


async def _flush_ciudadano_batch(session: AsyncSession, batch: list[dict]) -> int:
    # PII columns were dropped (D-DATA-02c). Write to _enc columns via pgcrypto.
    pii_key = os.environ.get("PII_ENCRYPTION_KEY", "dev-crece-pii-key-2026-min32chars!")
    sql = text(
        """
        INSERT INTO ciudadanos_legacy (
            legacy_id, org_id, alcaldia_id, unidad_territorial_id,
            promotor_legacy_id, nombre, apellido_paterno, apellido_materno,
            fecha_nacimiento_enc, edad, sexo, identidad_de_genero, email_enc,
            phone_01_enc, phone_02_enc, whatsapp_enc, calle, numero, numero_interior,
            colonia_texto, codigo_postal, municipio_texto, direccion_libre,
            manzana, latitud, longitud, latitud_cd, longitud_cd,
            seccion, cabecera_territorial, clave_electoral_enc, origen_ciudadano,
            rol, ocupacion, nivel_educativo, nivel_participacion,
            disposicion_tiempo, temas_de_interes, red_social,
            red_social_descripcion, residencia_si_no, contactado, respuesta,
            lista, aprobado, procesado, observaciones, id_mc,
            username_legacy, project_id_legacy, created_legacy, created_by_legacy,
            updated_legacy, updated_by_legacy, imported_at
        )
        VALUES (
            :legacy_id, :org_id, :alcaldia_id, :unidad_territorial_id,
            :promotor_legacy_id, :nombre, :apellido_paterno, :apellido_materno,
            CASE WHEN CAST(:fecha_nacimiento AS text) IS NOT NULL THEN pgp_sym_encrypt(CAST(:fecha_nacimiento AS text), CAST(:pii_key AS text)) END,
            :edad, :sexo, :identidad_de_genero,
            CASE WHEN CAST(:email AS text) IS NOT NULL THEN pgp_sym_encrypt(CAST(:email AS text), CAST(:pii_key AS text)) END,
            CASE WHEN CAST(:phone_01 AS text) IS NOT NULL THEN pgp_sym_encrypt(CAST(:phone_01 AS text), CAST(:pii_key AS text)) END,
            CASE WHEN CAST(:phone_02 AS text) IS NOT NULL THEN pgp_sym_encrypt(CAST(:phone_02 AS text), CAST(:pii_key AS text)) END,
            CASE WHEN CAST(:whatsapp AS text) IS NOT NULL THEN pgp_sym_encrypt(CAST(:whatsapp AS text), CAST(:pii_key AS text)) END,
            :calle, :numero, :numero_interior,
            :colonia_texto, :codigo_postal, :municipio_texto, :direccion_libre,
            :manzana, :latitud, :longitud, :latitud_cd, :longitud_cd,
            :seccion, :cabecera_territorial,
            CASE WHEN CAST(:clave_electoral AS text) IS NOT NULL THEN pgp_sym_encrypt(CAST(:clave_electoral AS text), CAST(:pii_key AS text)) END,
            :origen_ciudadano,
            :rol, :ocupacion, :nivel_educativo, :nivel_participacion,
            :disposicion_tiempo, :temas_de_interes, :red_social,
            :red_social_descripcion, :residencia_si_no, :contactado, :respuesta,
            :lista, :aprobado, :procesado, :observaciones, :id_mc,
            :username_legacy, :project_id_legacy, :created_legacy, :created_by_legacy,
            :updated_legacy, :updated_by_legacy, :imported_at
        )
        ON CONFLICT (legacy_id) DO UPDATE SET
            promotor_legacy_id = EXCLUDED.promotor_legacy_id,
            unidad_territorial_id = EXCLUDED.unidad_territorial_id,
            alcaldia_id = EXCLUDED.alcaldia_id,
            updated_legacy = EXCLUDED.updated_legacy,
            updated_by_legacy = EXCLUDED.updated_by_legacy
        """
    )
    for params in batch:
        params["pii_key"] = pii_key
        # pgp_sym_encrypt needs text, not datetime
        if params.get("fecha_nacimiento") is not None:
            params["fecha_nacimiento"] = str(params["fecha_nacimiento"])
        await session.execute(sql, params)
    return len(batch)


def _build_seccion_to_alcaldia(csv_path: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    with open(csv_path, encoding="latin-1", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            seccion = row.get("SECCION_2024", "").strip()
            alcaldia = row.get("ALCALDIA_2024", "").strip()
            if seccion and alcaldia:
                mapping[seccion] = alcaldia
    return mapping


async def _build_seccion_to_ut_id(session: AsyncSession) -> dict[str, int]:
    """One seccion may map to multiple UTs; we keep the first per seccion."""
    result = await session.execute(
        text("SELECT seccion_2024, id FROM unidades_territoriales")
    )
    out: dict[str, int] = {}
    for seccion, uid in result.all():
        if seccion and seccion not in out:
            out[seccion] = uid
    return out


async def _build_promotor_lookup(
    session: AsyncSession,
) -> dict[str, int]:
    result = await session.execute(
        text("SELECT user_name, id FROM promotores_legacy")
    )
    return {name: pid for name, pid in result.all()}


async def _pilot_project_ids(
    users_csv: Path, master_csv: Path
) -> dict[str, str]:
    """Project ids for the pilot alcaldias (derived from users + alcaldia match).

    We need the PROJECT_ID → alcaldia_nombre mapping for the pilot. The
    users CSV has the project_id but not the alcaldia name. The alcaldias
    CSV has the project_id ↔ name. Let's read alcaldias.csv to build this.
    """
    path = users_csv.parent / "alcaldias.csv"
    mapping: dict[str, str] = {}
    if path.exists():
        with open(path, encoding="latin-1", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                project_id = row.get("ID", "").strip()
                project_name = row.get("PROJECT", "").strip().upper()
                if project_id and project_name in PILOT_ALCALDIAS:
                    mapping[project_id] = project_name
    return mapping


async def run() -> None:
    raw_dir = _raw_dir()
    if not raw_dir.exists():
        log.error("raw dir not found: %s", raw_dir)
        log.error(
            "Set CRECE_MC_RAW_DIR or place files at backend/data/raw/mc_original/"
        )
        sys.exit(2)

    master_csv = raw_dir / "master_catalogo.csv"
    users_csv = raw_dir / "users (promotores).csv"
    ciudadanos_csv = raw_dir / "ciudadanos.csv"

    for p in [master_csv, users_csv, ciudadanos_csv]:
        if not p.exists():
            log.error("missing file: %s", p)
            sys.exit(2)

    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        # Ensure we're allowed to write to org_id=3 (bypass RLS via superuser
        # crece dev role — see D-S4-06).
        alcaldia_map = await _load_alcaldia_map(session)
        log.info("alcaldia_map loaded: %d entries", len(alcaldia_map))

        # 1. unidades_territoriales (full)
        await import_unidades_territoriales(session, master_csv, alcaldia_map)

        # 2. Lookup tables for next steps
        seccion_to_alcaldia = _build_seccion_to_alcaldia(master_csv)
        seccion_to_ut_id = await _build_seccion_to_ut_id(session)
        log.info(
            "lookup built: seccion→alcaldia=%d, seccion→ut=%d",
            len(seccion_to_alcaldia),
            len(seccion_to_ut_id),
        )

        # 3. Pilot project IDs (from alcaldias.csv)
        pilot_projects = await _pilot_project_ids(users_csv, master_csv)
        log.info("pilot project ids: %s", list(pilot_projects.keys()))

        # 4. promotores_legacy (filtered to pilot project IDs)
        await import_promotores(session, users_csv, alcaldia_map, pilot_projects)

        promotor_lookup = await _build_promotor_lookup(session)

        # 5. ciudadanos_legacy (filtered to pilot alcaldias by seccion match)
        await import_ciudadanos(
            session,
            ciudadanos_csv,
            alcaldia_map,
            seccion_to_alcaldia,
            seccion_to_ut_id,
            promotor_lookup,
        )

        await session.commit()
    await engine.dispose()
    log.info("import complete")


if __name__ == "__main__":
    asyncio.run(run())
