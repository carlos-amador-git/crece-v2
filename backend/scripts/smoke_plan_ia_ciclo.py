"""Smoke test para Sprint S4 T8/T9/T10/T11 — Plan IA ciclo de cierre.

Crea 2 filas test en `recomendaciones_plan_ia` (una en ventana activa, una vencida),
ejecuta los 3 servicios de cierre y genera un PDF sample. Idempotente por tagging
en `notas_cliente='[smoke-T8-T11]'`.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.dirigente import Dirigente
from app.models.recomendacion_plan_ia import RecomendacionPlanIA
from app.models.social import SocialPost
from app.services.plan_ia.cierre_service import cerrar_ventanas_vencidas
from app.services.plan_ia.memoria_service import compute as memoria_compute
from app.services.plan_ia.reporte_semanal import generar_pdf_dirigente
from app.services.plan_ia.seguimiento_service import actualizar_seguimiento

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SMOKE_TAG = "[smoke-T8-T11]"


def _clean_smoke_rows(session: Session) -> None:
    rows = (
        session.query(RecomendacionPlanIA)
        .filter(RecomendacionPlanIA.notas_cliente.like(f"%{SMOKE_TAG}%"))
        .all()
    )
    for r in rows:
        session.delete(r)
    session.commit()
    logger.info("smoke: limpiadas %d filas previas", len(rows))


def _pick_test_dirigente(session: Session) -> Dirigente:
    """Usa Piña si está disponible, sino el primer dirigente."""
    pina = session.execute(
        select(Dirigente).where(Dirigente.full_name.ilike("%piña%"))
    ).scalar_one_or_none()
    if pina is not None:
        logger.info("smoke: usando dirigente Piña id=%d", pina.id)
        return pina
    any_d = session.execute(select(Dirigente).limit(1)).scalar_one_or_none()
    if any_d is None:
        raise RuntimeError("No hay dirigentes en la DB para correr smoke")
    logger.info("smoke: usando dirigente fallback id=%d (%s)", any_d.id, any_d.full_name)
    return any_d


def _pick_test_post(session: Session, dirigente_id: int) -> SocialPost | None:
    """Busca un SocialPost del dirigente; si no, el primero disponible."""
    row = session.execute(
        text(
            "SELECT sp.id FROM social_posts sp "
            "JOIN social_profiles pr ON pr.id = sp.profile_id "
            "WHERE pr.dirigente_id = :did LIMIT 1"
        ),
        {"did": dirigente_id},
    ).first()
    if row:
        return session.get(SocialPost, row[0])
    # Fallback: any post
    return session.execute(select(SocialPost).limit(1)).scalar_one_or_none()


def _create_smoke_rows(session: Session) -> tuple[int, int]:
    """Crea 2 filas: una en ventana activa (T8 target) y otra vencida (T9 target)."""
    dirigente = _pick_test_dirigente(session)
    post = _pick_test_post(session, dirigente.id)

    now = datetime.now(UTC)

    # Fila 1: ventana activa (ejecutada + ventana_fin en futuro)
    activa = RecomendacionPlanIA(
        dirigente_id=dirigente.id,
        org_id=dirigente.org_id,
        tipo="start",
        accion_texto=(
            "Publicar un reel semanal mostrando recorridos en territorio con vecinos, "
            "priorizando zonas con mayor abstencionismo según B07."
        ),
        ventana_inicio=now - timedelta(days=5),
        ventana_fin=now + timedelta(days=9),
        ventana_duracion_dias=14,
        criterio_exito={
            "metrica": "engagement_rate",
            "objetivo": 0.03,
            "tipo": "min",
            "umbral_desviacion_pct": 0.15,
        },
        principio_conductual="proximidad_territorial",
        evidencia_respaldo={
            "bloques_citados": ["B07", "B13"],
            "post_ids": [post.id] if post else [],
        },
        estado="ejecutada",
        post_ejecutor_id=post.id if post else None,
        metricas_predichas={
            "engagement_rate": 0.035,
            "likes": 180,
            "comments": 22,
            "views": 4500,
        },
        notas_cliente=f"{SMOKE_TAG} ventana-activa",
    )

    # Fila 2: ventana vencida (ejecutada + ventana_fin en pasado)
    vencida = RecomendacionPlanIA(
        dirigente_id=dirigente.id,
        org_id=dirigente.org_id,
        tipo="continue",
        accion_texto=(
            "Continuar agenda de Miércoles Vecinales en Álvaro Obregón, "
            "documentando con foto + texto breve cada sesión."
        ),
        ventana_inicio=now - timedelta(days=20),
        ventana_fin=now - timedelta(days=1),
        ventana_duracion_dias=14,
        criterio_exito={
            "metrica": "likes",
            "objetivo": 100,
            "tipo": "min",
        },
        principio_conductual="consistencia_agenda",
        evidencia_respaldo={"bloques_citados": ["B03"]},
        estado="ejecutada",
        post_ejecutor_id=post.id if post else None,
        metricas_predichas={"likes": 120, "engagement_rate": 0.025},
        # Simular métricas ya registradas por seguimiento
        metricas_observadas={
            "ultimo_snapshot": {
                "fecha": (now - timedelta(days=1)).date().isoformat(),
                "likes": int(post.likes) if post else 95,
                "comments": int(post.comments) if post else 8,
                "engagement_rate": float(post.engagement_rate or 0.022),
            }
        },
        notas_cliente=f"{SMOKE_TAG} ventana-vencida",
    )

    session.add_all([activa, vencida])
    session.commit()
    session.refresh(activa)
    session.refresh(vencida)
    logger.info("smoke: creadas filas id_activa=%d id_vencida=%d", activa.id, vencida.id)
    return activa.id, vencida.id


def main() -> None:
    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
    session = Session(engine)
    try:
        _clean_smoke_rows(session)
        activa_id, vencida_id = _create_smoke_rows(session)

        print("\n=== T8 · plan_ia_seguimiento_diario ===")
        seg_result = actualizar_seguimiento(session)
        print(seg_result)

        # Refresh y mostrar métricas observadas de la fila activa
        session.expire_all()
        activa = session.get(RecomendacionPlanIA, activa_id)
        print(f"  activa.metricas_observadas = {activa.metricas_observadas}")

        print("\n=== T9 · plan_ia_cierre_diario ===")
        cierre_result = cerrar_ventanas_vencidas(session)
        print(cierre_result)

        session.expire_all()
        vencida = session.get(RecomendacionPlanIA, vencida_id)
        print(
            f"  vencida.estado={vencida.estado} veredicto={vencida.veredicto} "
            f"veredicto_original={vencida.veredicto_original}"
        )

        print("\n=== T10 · memoria_service.compute ===")
        dirigente_id = activa.dirigente_id
        memoria = memoria_compute(session, dirigente_id=dirigente_id)
        print(
            f"  dirigente_id={memoria['dirigente_id']} "
            f"total_completadas={memoria['total_completadas']} "
            f"tasa_exito_global={memoria['tasa_exito_global']}"
        )
        print(f"  por_tipo={memoria['por_tipo']}")
        print(f"  historico[0]={memoria['historico'][0] if memoria['historico'] else 'n/a'}")

        print("\n=== T11 · reporte_semanal.generar_pdf_dirigente ===")
        output_path = Path("/app/research/2026-04-19/reporte_semanal_sample.pdf")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_bytes = generar_pdf_dirigente(
            session,
            dirigente_id=dirigente_id,
            output_path=output_path,
        )
        print(f"  PDF generado: {output_path} · {len(pdf_bytes)} bytes")

        print("\nSMOKE OK")
    finally:
        session.close()


if __name__ == "__main__":
    main()
