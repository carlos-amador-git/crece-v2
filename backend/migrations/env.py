from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.database import Base

# Import all models so Alembic sees them
from app.models import (  # noqa: F401
    alerta_crisis,
    api_key,
    campaign_integration,
    campana,
    canvassing,
    ciudadano,
    contenido,
    contenido_pieza,
    crm_interaccion,
    dirigente,
    electoral,
    encuesta,
    evento,
    gasto_electoral,
    ia_content_registry,
    metrica_social,
    organizacion,
    plan_ia,
    programa_social,
    social,
    solicitud,
    user,
    voter_score,
    voter_score_integration,
)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """Exclude PostGIS internal tables from autogenerate."""
    # Skip GeoAlchemy2 auto-created spatial indexes (they're created with the table)
    if type_ == "index" and name and name.startswith("idx_") and reflected:
        return False
    if type_ == "table" and name in (
        "spatial_ref_sys", "topology", "layer",
        # Tiger geocoder tables
        "loader_lookuptables", "loader_platform", "loader_variables",
        "state_lookup", "county_lookup", "countysub_lookup", "place_lookup",
        "zip_lookup", "zip_lookup_all", "zip_lookup_base", "zip_state", "zip_state_loc",
        "street_type_lookup", "secondary_unit_lookup", "direction_lookup",
        "geocode_settings", "geocode_settings_default",
        "state", "county", "cousub", "place", "tract", "bg", "tabblock", "tabblock20",
        "zcta5", "faces", "featnames", "edges", "addr", "addrfeat",
        "pagc_gaz", "pagc_lex", "pagc_rules",
    ):
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):  # type: ignore[no-untyped-def]
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.DATABASE_URL
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
