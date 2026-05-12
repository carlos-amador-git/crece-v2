"""Sección 1 · Detección de perfil §1.5 — 4 opciones onboarding wizard.

Los 4 perfiles son descriptivos del estado comercial del cliente y ajustan
downstream:
    politico_activo       — en cargo electo o elegido
    funcionario_gobierno  — posición designada en gobierno
    figura_precampaña     — buscando candidatura futura
    empresario_transicion — empresario evaluando entrar a política

No se inventa el perfil: el cliente lo declara explícitamente en el wizard.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente


PERFILES_VALIDOS: frozenset[str] = frozenset(
    {
        "politico_activo",
        "funcionario_gobierno",
        "figura_precampaña",
        "empresario_transicion",
    }
)


class PerfilInvalidoError(ValueError):
    """Se intentó asignar un perfil que no está en PERFILES_VALIDOS."""


async def set_perfil(
    db: AsyncSession, *, dirigente_id: int, perfil: str
) -> Dirigente:
    """Persiste el perfil §1.5 declarado por el cliente.

    Raises:
        PerfilInvalidoError si el perfil no es uno de los 4 canónicos.
        LookupError si el dirigente no existe.
    """
    if perfil not in PERFILES_VALIDOS:
        raise PerfilInvalidoError(
            f"Perfil '{perfil}' no válido. Opciones: {sorted(PERFILES_VALIDOS)}"
        )

    dirigente = await db.get(Dirigente, dirigente_id)
    if dirigente is None:
        raise LookupError(f"Dirigente {dirigente_id} no existe")

    dirigente.perfil_1_5 = perfil
    await db.commit()
    await db.refresh(dirigente)
    return dirigente


async def get_perfil(
    db: AsyncSession, *, dirigente_id: int
) -> dict[str, str | int | None]:
    """Devuelve perfil actual + metadata mínima para el wizard."""
    result = await db.execute(select(Dirigente).where(Dirigente.id == dirigente_id))
    dirigente = result.scalar_one_or_none()
    if dirigente is None:
        raise LookupError(f"Dirigente {dirigente_id} no existe")

    return {
        "dirigente_id": dirigente.id,
        "full_name": dirigente.full_name,
        "cargo": dirigente.cargo,
        "perfil_1_5": dirigente.perfil_1_5,
        "perfiles_disponibles": sorted(PERFILES_VALIDOS),
    }
