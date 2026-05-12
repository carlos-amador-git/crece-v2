"""Tests S4.4a — location_inference contra catálogo DB real.

Requiere que la migración `a1b2c3d4e5f6` haya corrido y que
`scripts/seed_alcaldias_cdmx.py` haya sido ejecutado (16 alcaldías
presentes). Los tests validan los 4 caminos de resolución del servicio.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.services.location_inference import (
    LocationResult,
    infer_location,
    normalize_social_text,
)


@pytest.fixture
async def db() -> AsyncSession:
    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def test_normalize_social_text_strips_handles_hashtags_emojis() -> None:
    raw = "Hola @alejandro.pinha 🔥 #CDMX el Zócalo está lleno!!! https://t.co/abc"
    out = normalize_social_text(raw)
    assert "@alejandro" not in out
    assert "#CDMX" not in out
    assert "CDMX" in out  # hashtag expanded
    assert "🔥" not in out
    assert "https" not in out
    assert "Zócalo" in out


def test_normalize_social_text_empty() -> None:
    assert normalize_social_text("") == ""
    assert normalize_social_text(None) == ""  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_resolve_by_geo_point_zocalo(db: AsyncSession) -> None:
    # Zócalo CDMX coordinates → Cuauhtémoc
    result = await infer_location(db, content="", lat=19.4326, lon=-99.1332)
    assert result.alcaldia_nombre == "Cuauhtémoc"
    assert result.method == "geo_point"
    assert result.confidence == 1.0


@pytest.mark.asyncio
async def test_resolve_by_geo_point_polanco(db: AsyncSession) -> None:
    # Polanco → Miguel Hidalgo
    result = await infer_location(db, content="", lat=19.4297, lon=-99.2049)
    assert result.alcaldia_nombre == "Miguel Hidalgo"
    assert result.method == "geo_point"


@pytest.mark.asyncio
async def test_resolve_by_name_match(db: AsyncSession) -> None:
    content = "Gran jornada de trabajo hoy en Cuauhtémoc con vecinos #CDMX"
    result = await infer_location(db, content=content)
    assert result.alcaldia_nombre == "Cuauhtémoc"
    assert result.method == "name_match"
    assert result.confidence == 0.9


@pytest.mark.asyncio
async def test_resolve_by_name_accent_insensitive(db: AsyncSession) -> None:
    # Note: "Cuauhtemoc" without accent should still match
    content = "Reunion en la alcaldia Cuauhtemoc con líderes barriales"
    result = await infer_location(db, content=content)
    assert result.alcaldia_nombre == "Cuauhtémoc"


@pytest.mark.asyncio
async def test_resolve_by_colonia_polanco(db: AsyncSession) -> None:
    content = "Caminando por Polanco esta mañana"
    result = await infer_location(db, content=content)
    assert result.alcaldia_nombre == "Miguel Hidalgo"
    assert result.method == "colonia_match"
    assert result.confidence == 0.75


@pytest.mark.asyncio
async def test_resolve_by_colonia_del_valle(db: AsyncSession) -> None:
    content = "Evento vecinal en Del Valle hoy 7pm"
    result = await infer_location(db, content=content)
    assert result.alcaldia_nombre == "Benito Juárez"
    assert result.method == "colonia_match"


@pytest.mark.asyncio
async def test_bio_fallback(db: AsyncSession) -> None:
    content = "Nuevo programa de apoyo a familias"  # no geo hints
    bio = "Alcalde electo de Benito Juárez, CDMX"
    result = await infer_location(db, content=content, account_bio=bio)
    assert result.alcaldia_nombre == "Benito Juárez"
    assert result.method == "bio_fallback"
    assert result.confidence == 0.5


@pytest.mark.asyncio
async def test_no_match(db: AsyncSession) -> None:
    content = "Discusión abstracta sobre filosofía política"
    result = await infer_location(db, content=content)
    assert result.alcaldia_id is None
    assert result.method == "none"
