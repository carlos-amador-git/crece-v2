"""Sección 9 · Activación final + trigger Celery scrape_all_profiles.

Requisitos duros antes de activar el piloto:
    1. perfil_1_5 declarado
    2. cuentas confirmadas ≥ 1 (is_confirmed=True)
    3. competidores declarados ≥ 1
    4. promesas declaradas ≥ 1

Al cumplir todos: encola ``scrape_all_profiles`` (solo perfiles confirmados).
Retorna ``data_fidelity_tier`` derivado del estado OAuth actual (T1/T2/T3
según SPRINT-S5-SCOPING §1.1).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.oauth_token import OAuthTokenByPlatform
from app.models.promesa_dirigente import PromesaDirigente
from app.models.social import SocialProfile


async def _contar_requisitos(
    db: AsyncSession, dirigente_id: int
) -> dict[str, Any]:
    dirigente = await db.get(Dirigente, dirigente_id)
    if dirigente is None:
        raise LookupError(f"Dirigente {dirigente_id} no existe")

    confirmed_q = await db.execute(
        select(func.count(SocialProfile.id)).where(
            SocialProfile.dirigente_id == dirigente_id,
            SocialProfile.is_confirmed.is_(True),
        )
    )
    confirmed_count = confirmed_q.scalar_one() or 0

    promesas_q = await db.execute(
        select(func.count(PromesaDirigente.id)).where(
            PromesaDirigente.dirigente_id == dirigente_id,
        )
    )
    promesas_count = promesas_q.scalar_one() or 0

    competidores_count = len(dirigente.competidor_directo_ids or [])

    oauth_q = await db.execute(
        select(OAuthTokenByPlatform).where(
            OAuthTokenByPlatform.dirigente_id == dirigente_id,
            OAuthTokenByPlatform.status == "active",
        )
    )
    tokens = oauth_q.scalars().all()
    oauth_real_count = sum(1 for t in tokens if not t.is_stub)
    oauth_stub_count = sum(1 for t in tokens if t.is_stub)

    return {
        "dirigente": dirigente,
        "confirmed_count": confirmed_count,
        "promesas_count": promesas_count,
        "competidores_count": competidores_count,
        "oauth_real_count": oauth_real_count,
        "oauth_stub_count": oauth_stub_count,
    }


def _derivar_tier(
    oauth_real_count: int, confirmed_count: int
) -> str:
    """Decide data_fidelity_tier global según SPRINT-S5-SCOPING §1.1."""
    if oauth_real_count > 0:
        return "T1"
    if confirmed_count > 0:
        return "T3"  # scraping público con confirmación humana
    return "N-A"


async def activar_dirigente(
    db: AsyncSession, *, dirigente_id: int
) -> dict[str, Any]:
    """Ejecuta los checks de activación y dispara scrape_all_profiles."""
    meta = await _contar_requisitos(db, dirigente_id)
    dirigente: Dirigente = meta["dirigente"]

    missing: list[str] = []
    if not dirigente.perfil_1_5:
        missing.append("perfil_1_5")
    if meta["confirmed_count"] < 1:
        missing.append("cuentas_confirmadas ≥ 1")
    if meta["competidores_count"] < 1:
        missing.append("competidores ≥ 1")
    if meta["promesas_count"] < 1:
        missing.append("promesas ≥ 1")

    if missing:
        return {
            "activated": False,
            "dirigente_id": dirigente_id,
            "missing": missing,
            "resumen": {
                "perfil_1_5": dirigente.perfil_1_5,
                "cuentas_confirmadas": meta["confirmed_count"],
                "competidores": meta["competidores_count"],
                "promesas": meta["promesas_count"],
            },
        }

    tier = _derivar_tier(meta["oauth_real_count"], meta["confirmed_count"])
    dirigente.data_origin = tier if tier in {"T1", "T3", "N-A"} else "T3"
    await db.commit()

    # Disparar Celery task — ventana aislada para que fallos no bloqueen la response.
    scrape_task_id: str | None = None
    scrape_error: str | None = None
    try:
        from app.workers.tasks import scrape_all_profiles

        async_result = scrape_all_profiles.apply_async()
        scrape_task_id = async_result.id
    except Exception as exc:  # pragma: no cover - Celery broker issues
        scrape_error = f"Celery unavailable: {exc}"

    return {
        "activated": True,
        "dirigente_id": dirigente_id,
        "scrape_task_id": scrape_task_id,
        "scrape_error": scrape_error,
        "data_fidelity_tier": tier,
        "resumen": {
            "perfil_1_5": dirigente.perfil_1_5,
            "cuentas_confirmadas": meta["confirmed_count"],
            "competidores": meta["competidores_count"],
            "promesas": meta["promesas_count"],
            "oauth_real": meta["oauth_real_count"],
            "oauth_stub": meta["oauth_stub_count"],
        },
    }
