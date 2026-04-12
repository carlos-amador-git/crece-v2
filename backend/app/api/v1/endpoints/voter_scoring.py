"""Voter Scoring API — predict and query citizen voting probability for MC."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import Role, RoleChecker, get_current_user
from app.models.ciudadano import Ciudadano
from app.models.encuesta import Encuesta
from app.models.evento import EventoAsistente
from app.models.user import User
from app.models.voter_score import VoterScore
from app.schemas.voter_score import (
    SeccionScoreSummary,
    SegmentDistribution,
    TrainResponse,
    VoterScoreResponse,
    VoterScoreRunRequest,
    VoterScoreRunResponse,
)
from app.services.voter_scoring import voter_scoring_engine

router = APIRouter()


@router.post(
    "/run",
    response_model=VoterScoreRunResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN, Role.ANALYST]))],
)
async def run_scoring(
    payload: VoterScoreRunRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> VoterScoreRunResponse:
    """Trigger batch scoring for all ciudadanos.

    Optionally filter by org_id. If force_retrain is True, retrain the ML
    model before scoring.
    """
    if payload.force_retrain:
        try:
            await voter_scoring_engine.train(db)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

    result = await voter_scoring_engine.score_all(db, org_id=payload.org_id)

    return VoterScoreRunResponse(
        total_scored=result["total_scored"],
        segmento_breakdown=result["segmento_breakdown"],
        modelo_version=result["modelo_version"],
    )


@router.post(
    "/train",
    response_model=TrainResponse,
    dependencies=[Depends(RoleChecker([Role.ADMIN]))],
)
async def train_model(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TrainResponse:
    """Train the ML model on current ciudadano and encuesta data. Admin only."""
    try:
        metrics = await voter_scoring_engine.train(db)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return TrainResponse(
        modelo_version=metrics["modelo_version"],
        accuracy=metrics["accuracy"],
        f1_score=metrics["f1_score"],
        confusion_matrix=metrics["confusion_matrix"],
        total_samples=metrics["total_samples"],
        message="Model trained successfully",
    )


@router.get(
    "/segments",
    response_model=list[SegmentDistribution],
)
async def get_segment_distribution(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    org_id: int | None = None,
) -> list[SegmentDistribution]:
    """Return the distribution of voter segments for dashboard charts."""
    query = (
        select(
            VoterScore.segmento,
            func.count(VoterScore.id).label("cnt"),
        )
        .group_by(VoterScore.segmento)
    )
    if org_id is not None:
        query = query.where(VoterScore.org_id == org_id)

    result = await db.execute(query)
    rows = result.all()

    total = sum(row.cnt for row in rows)
    if total == 0:
        return []

    return [
        SegmentDistribution(
            segmento=row.segmento,
            count=row.cnt,
            percentage=round(row.cnt / total * 100, 2),
        )
        for row in rows
    ]


@router.get(
    "/by-seccion",
    response_model=list[SeccionScoreSummary],
)
async def list_scores_by_seccion(
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(50, ge=1, le=500),
) -> list[SeccionScoreSummary]:
    """Aggregated voter scores grouped by electoral section.

    Returns one row per section that has at least one scored citizen, ordered
    by total citizens desc. Used by the scoring dashboard table.
    """
    # Aggregate per seccion_id in a single query
    agg_query = (
        select(
            Ciudadano.seccion_id.label("seccion_id"),
            func.avg(VoterScore.score).label("avg_score"),
            func.count(VoterScore.id).label("total"),
        )
        .join(Ciudadano, Ciudadano.id == VoterScore.ciudadano_id)
        .where(Ciudadano.seccion_id.is_not(None))
        .group_by(Ciudadano.seccion_id)
        .order_by(func.count(VoterScore.id).desc())
        .limit(limit)
    )
    agg_rows = (await db.execute(agg_query)).all()

    if not agg_rows:
        return []

    seccion_ids = [row.seccion_id for row in agg_rows]

    # Segment breakdown per seccion (single grouped query)
    seg_query = (
        select(
            Ciudadano.seccion_id.label("seccion_id"),
            VoterScore.segmento.label("segmento"),
            func.count(VoterScore.id).label("cnt"),
        )
        .join(Ciudadano, Ciudadano.id == VoterScore.ciudadano_id)
        .where(Ciudadano.seccion_id.in_(seccion_ids))
        .group_by(Ciudadano.seccion_id, VoterScore.segmento)
    )
    seg_rows = (await db.execute(seg_query)).all()

    seg_by_seccion: dict[int, dict[str, int]] = {}
    for row in seg_rows:
        seg_by_seccion.setdefault(row.seccion_id, {})[row.segmento.value] = row.cnt

    return [
        SeccionScoreSummary(
            seccion_id=row.seccion_id,
            avg_score=round(float(row.avg_score), 2),
            segmento_counts=seg_by_seccion.get(row.seccion_id, {}),
            total_ciudadanos=row.total,
        )
        for row in agg_rows
    ]


@router.get(
    "/by-seccion/{seccion_id}",
    response_model=SeccionScoreSummary,
)
async def get_scores_by_seccion(
    seccion_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
) -> SeccionScoreSummary:
    """Aggregated voter scores for a given electoral section."""
    # Average score and total
    agg_query = (
        select(
            func.avg(VoterScore.score).label("avg_score"),
            func.count(VoterScore.id).label("total"),
        )
        .join(Ciudadano, Ciudadano.id == VoterScore.ciudadano_id)
        .where(Ciudadano.seccion_id == seccion_id)
    )
    agg_result = await db.execute(agg_query)
    agg_row = agg_result.one()

    if agg_row.total == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No scored ciudadanos in seccion {seccion_id}",
        )

    # Segment breakdown
    seg_query = (
        select(
            VoterScore.segmento,
            func.count(VoterScore.id).label("cnt"),
        )
        .join(Ciudadano, Ciudadano.id == VoterScore.ciudadano_id)
        .where(Ciudadano.seccion_id == seccion_id)
        .group_by(VoterScore.segmento)
    )
    seg_result = await db.execute(seg_query)
    segmento_counts = {row.segmento.value: row.cnt for row in seg_result.all()}

    return SeccionScoreSummary(
        seccion_id=seccion_id,
        avg_score=round(float(agg_row.avg_score), 2),
        segmento_counts=segmento_counts,
        total_ciudadanos=agg_row.total,
    )


@router.get(
    "/{ciudadano_id}",
    response_model=VoterScoreResponse,
)
async def get_voter_score(
    ciudadano_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    _current_user: Annotated[User, Depends(get_current_user)],
    recompute: bool = Query(False, description="If True, recompute score on the fly"),
) -> VoterScoreResponse:
    """Get the voter score for a specific ciudadano.

    If recompute=True, scores the ciudadano in real-time instead of returning
    the stored score.
    """
    if recompute:
        # Fetch ciudadano
        c_result = await db.execute(
            select(Ciudadano).where(Ciudadano.id == ciudadano_id)
        )
        ciudadano = c_result.scalar_one_or_none()
        if ciudadano is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ciudadano not found",
            )

        # Fetch encuestas
        enc_result = await db.execute(
            select(Encuesta)
            .where(Encuesta.ciudadano_id == ciudadano_id)
            .order_by(Encuesta.fecha_encuesta.desc())
        )
        encuestas = list(enc_result.scalars().all())

        # Count events attended
        evt_result = await db.execute(
            select(func.count(EventoAsistente.id))
            .where(
                EventoAsistente.ciudadano_id == ciudadano_id,
                EventoAsistente.asistio.is_(True),
            )
        )
        num_eventos = evt_result.scalar_one()

        score_result = voter_scoring_engine.score_ciudadano(
            ciudadano, encuestas, num_eventos
        )

        return VoterScoreResponse(
            id=0,  # not persisted
            ciudadano_id=ciudadano_id,
            score=score_result.score,
            probabilidad_mc=score_result.probabilidad_mc,
            segmento=score_result.segmento,
            features=score_result.features,
            modelo_version=score_result.modelo_version,
            scored_at=ciudadano.updated_at,
        )

    # Return stored score
    result = await db.execute(
        select(VoterScore).where(VoterScore.ciudadano_id == ciudadano_id)
    )
    voter_score = result.scalar_one_or_none()
    if voter_score is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Voter score not found. Run scoring first or use ?recompute=true",
        )
    return VoterScoreResponse.model_validate(voter_score)
