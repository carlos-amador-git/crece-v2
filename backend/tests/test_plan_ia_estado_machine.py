"""Tests de máquina de estados del endpoint PUT /plan-ia/{id}/estado.

Garantiza que transiciones inválidas devuelvan HTTP 409 Conflict, protegiendo
la integridad del ciclo D-17 (propuesta → aprobada/modificada → ejecutada →
completada/fallida) documentado en MASTER §6.3.

Creado 2026-04-20 tras hotfix PR #32 · prevenir regresión.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recomendacion_plan_ia import RecomendacionPlanIA


@pytest.fixture
async def prop_recomendacion(db: AsyncSession):
    r = RecomendacionPlanIA(
        dirigente_id=1,
        org_id=1,
        tipo="start",
        accion_texto="test fixture · máquina estados 409",
        ventana_duracion_dias=14,
        principio_conductual="test",
        estado="propuesta",
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    yield r
    await db.delete(r)
    await db.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "estado_actual, estado_target",
    [
        ("propuesta", "completada"),   # salta aprobada + ejecutada
        ("propuesta", "ejecutada"),    # salta aprobada
        ("propuesta", "fallida"),      # salta todo
        ("aprobada", "completada"),    # salta ejecutada
        ("aprobada", "fallida"),       # salta ejecutada
        ("ejecutada", "propuesta"),    # reverso no permitido
        ("ejecutada", "aprobada"),     # reverso no permitido
        ("completada", "aprobada"),    # terminal no sale
        ("completada", "ejecutada"),   # terminal no sale
        ("rechazada", "aprobada"),     # terminal no sale
        ("rechazada", "propuesta"),    # terminal no sale
        ("fallida", "completada"),     # terminal no sale
    ],
)
async def test_transicion_invalida_devuelve_409(
    async_client_admin: AsyncClient,
    db: AsyncSession,
    prop_recomendacion: RecomendacionPlanIA,
    estado_actual: str,
    estado_target: str,
):
    """Verifica que transiciones fuera del DAG permitido devuelvan 409.

    DAG canónico del endpoint (MASTER §6.3 D-17 · implementado en plan_ia.py):
        propuesta → {aprobada, rechazada, modificada}
        aprobada → {ejecutada, rechazada, modificada}
        modificada → {aprobada, ejecutada, rechazada}
        ejecutada → {completada, fallida}
        rechazada, completada, fallida = terminales
    """
    # Forzar estado actual
    prop_recomendacion.estado = estado_actual
    db.add(prop_recomendacion)
    await db.commit()

    response = await async_client_admin.put(
        f"/api/v1/plan-ia/{prop_recomendacion.id}/estado",
        json={"estado": estado_target},
    )
    assert response.status_code == 409, (
        f"Esperaba 409 para {estado_actual}→{estado_target}, "
        f"got {response.status_code}: {response.text}"
    )
    body = response.json()
    assert "no permitida" in body.get("detail", "").lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "estado_actual, estado_target",
    [
        ("propuesta", "aprobada"),
        ("propuesta", "rechazada"),
        ("propuesta", "modificada"),
        ("aprobada", "ejecutada"),
        ("aprobada", "rechazada"),
        ("aprobada", "modificada"),
        ("modificada", "aprobada"),
        ("modificada", "ejecutada"),
        ("modificada", "rechazada"),
        ("ejecutada", "completada"),
        ("ejecutada", "fallida"),
    ],
)
async def test_transicion_valida_devuelve_200(
    async_client_admin: AsyncClient,
    db: AsyncSession,
    prop_recomendacion: RecomendacionPlanIA,
    estado_actual: str,
    estado_target: str,
):
    """Verifica que las transiciones del DAG pasen 200 (caso positivo)."""
    prop_recomendacion.estado = estado_actual
    db.add(prop_recomendacion)
    await db.commit()

    response = await async_client_admin.put(
        f"/api/v1/plan-ia/{prop_recomendacion.id}/estado",
        json={"estado": estado_target},
    )
    assert response.status_code == 200, (
        f"Esperaba 200 para {estado_actual}→{estado_target}, "
        f"got {response.status_code}: {response.text}"
    )
    assert response.json()["estado"] == estado_target


@pytest.mark.asyncio
async def test_payload_sin_estado_devuelve_422(
    async_client_admin: AsyncClient,
    prop_recomendacion: RecomendacionPlanIA,
):
    """Payload sin campo 'estado' requerido debe devolver 422."""
    response = await async_client_admin.put(
        f"/api/v1/plan-ia/{prop_recomendacion.id}/estado",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_recomendacion_inexistente_devuelve_404(
    async_client_admin: AsyncClient,
):
    """PUT sobre id inexistente debe devolver 404."""
    response = await async_client_admin.put(
        "/api/v1/plan-ia/999999/estado",
        json={"estado": "aprobada"},
    )
    assert response.status_code == 404
