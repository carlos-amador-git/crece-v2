"""Voter Scoring Engine — predicts probability of a citizen voting for MC.

Uses scikit-learn RandomForestClassifier when a trained model is available,
falling back to a deterministic rule-based scoring system otherwise.
"""

from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ciudadano import (
    Ciudadano,
    Escolaridad,
    IntencionVotoCiudadano,
    NivelInteres,
    RangoEdad,
)
from app.models.encuesta import Encuesta
from app.models.evento import EventoAsistente
from app.models.voter_score import SegmentoVotante, VoterScore

logger = logging.getLogger(__name__)

MODEL_DIR = Path("data/models")

# ── Mapping tables ───────────────────────────────────────────

RANGO_EDAD_MIDPOINT: dict[RangoEdad, float] = {
    RangoEdad.E_18_25: 21.0,
    RangoEdad.E_26_35: 30.0,
    RangoEdad.E_36_45: 40.0,
    RangoEdad.E_46_55: 50.0,
    RangoEdad.E_56_65: 60.0,
    RangoEdad.E_65_PLUS: 70.0,
}

ESCOLARIDAD_ORDINAL: dict[Escolaridad, int] = {
    Escolaridad.SIN_ESTUDIOS: 0,
    Escolaridad.PRIMARIA: 1,
    Escolaridad.SECUNDARIA: 2,
    Escolaridad.PREPARATORIA: 3,
    Escolaridad.UNIVERSIDAD: 4,
    Escolaridad.POSGRADO: 5,
}

NIVEL_INTERES_ORDINAL: dict[NivelInteres, int] = {
    NivelInteres.DESCONOCIDO: 0,
    NivelInteres.BAJO: 1,
    NivelInteres.MEDIO: 2,
    NivelInteres.ALTO: 3,
}

# Feature column order — MUST stay consistent between train and predict
FEATURE_COLUMNS = [
    "edad_numeric",
    "escolaridad_ordinal",
    "es_simpatizante_mc",
    "es_promotor",
    "nivel_interes_ordinal",
    "num_encuestas",
    "num_eventos_asistidos",
    "num_programas_sociales",
    "tiene_telefono",
    "tiene_email",
    "ultima_intencion_voto_mc",
]


@dataclass(frozen=True)
class VoterScoreResult:
    score: float
    probabilidad_mc: float
    segmento: SegmentoVotante
    features: dict[str, float]
    modelo_version: str


def _segmento_from_score(score: float) -> SegmentoVotante:
    """Classify score into voter segment using fixed thresholds."""
    if score >= 70:
        return SegmentoVotante.PROMOTABLE
    if score >= 40:
        return SegmentoVotante.PERSUADIBLE
    if score >= 20:
        return SegmentoVotante.INDECISO
    return SegmentoVotante.OPOSITOR


class VoterScoringEngine:
    """Voter scoring engine with ML and rule-based fallback."""

    def __init__(self) -> None:
        self._model: object | None = None
        self._model_version: str | None = None
        self._load_latest_model()

    # ── Feature extraction ───────────────────────────────

    def extract_features(
        self,
        ciudadano: Ciudadano,
        encuestas: list[Encuesta],
        num_eventos_asistidos: int,
    ) -> dict[str, float]:
        """Build a feature dictionary from ciudadano data.

        All values are numeric (int/float) for direct use with sklearn.
        """
        # Latest encuesta by date, fallback to last in list
        latest_encuesta: Encuesta | None = None
        if encuestas:
            latest_encuesta = max(encuestas, key=lambda e: e.fecha_encuesta)

        programas_list = ciudadano.programas_sociales or []
        num_programas = len(programas_list) if isinstance(programas_list, list) else 0

        ultima_intencion_mc = 0
        if latest_encuesta is not None:
            ultima_intencion_mc = (
                1 if latest_encuesta.intencion_voto == IntencionVotoCiudadano.MC else 0
            )

        return {
            "edad_numeric": RANGO_EDAD_MIDPOINT.get(ciudadano.edad_rango, 35.0),
            "escolaridad_ordinal": float(
                ESCOLARIDAD_ORDINAL.get(ciudadano.escolaridad, 2)  # type: ignore[arg-type]
                if ciudadano.escolaridad
                else 2
            ),
            "es_simpatizante_mc": float(ciudadano.es_simpatizante_mc),
            "es_promotor": float(ciudadano.es_promotor),
            "nivel_interes_ordinal": float(NIVEL_INTERES_ORDINAL.get(ciudadano.nivel_interes, 0)),
            "num_encuestas": float(len(encuestas)),
            "num_eventos_asistidos": float(num_eventos_asistidos),
            "num_programas_sociales": float(num_programas),
            "tiene_telefono": float(bool(ciudadano.telefono)),
            "tiene_email": float(bool(ciudadano.email)),
            "ultima_intencion_voto_mc": float(ultima_intencion_mc),
        }

    # ── Rule-based fallback scoring ──────────────────────

    def _rule_based_score(
        self,
        ciudadano: Ciudadano,
        encuestas: list[Encuesta],
        num_eventos_asistidos: int,
    ) -> float:
        """Deterministic rule-based scoring when no ML model is available.

        Returns a score clamped to 0-100.
        """
        score = 50.0

        if ciudadano.es_simpatizante_mc:
            score += 20.0

        if ciudadano.es_promotor:
            score += 10.0

        # Latest encuesta intention
        latest_encuesta: Encuesta | None = None
        if encuestas:
            latest_encuesta = max(encuestas, key=lambda e: e.fecha_encuesta)

        if latest_encuesta is not None:
            iv = latest_encuesta.intencion_voto
            if iv == IntencionVotoCiudadano.MC:
                score += 15.0
            elif iv == IntencionVotoCiudadano.MORENA:
                score -= 20.0
            elif iv in (IntencionVotoCiudadano.PAN, IntencionVotoCiudadano.PRI):
                score -= 10.0

        # Events attendance bonus (max +15)
        score += min(num_eventos_asistidos * 5.0, 15.0)

        # Interest level bonus
        if ciudadano.nivel_interes == NivelInteres.ALTO:
            score += 5.0

        return max(0.0, min(100.0, score))

    # ── ML model management ──────────────────────────────

    def _load_latest_model(self) -> None:
        """Load the most recent trained model from disk, if any."""
        if not MODEL_DIR.exists():
            return

        model_files = sorted(MODEL_DIR.glob("voter_score_v*.pkl"), reverse=True)
        if not model_files:
            return

        latest = model_files[0]
        try:
            with open(latest, "rb") as f:
                self._model = pickle.load(f)
            self._model_version = latest.stem.replace("voter_score_", "")
            logger.info("Loaded voter scoring model: %s", self._model_version)
        except Exception:
            logger.exception("Failed to load voter scoring model from %s", latest)
            self._model = None
            self._model_version = None

    def _save_model(self, model: object, version: str) -> Path:
        """Persist a trained model to disk."""
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        path = MODEL_DIR / f"voter_score_{version}.pkl"
        with open(path, "wb") as f:
            pickle.dump(model, f)
        logger.info("Saved voter scoring model to %s", path)
        return path

    # ── Training ─────────────────────────────────────────

    async def train(self, db: AsyncSession) -> dict:
        """Train a RandomForestClassifier on ciudadano data.

        Target: latest encuesta.intencion_voto == MC (binary classification).
        Returns training metrics dict.
        """
        # Lazy imports — sklearn is an optional dependency
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
        from sklearn.model_selection import train_test_split

        # Fetch ciudadanos that have at least 1 encuesta
        stmt = select(Ciudadano).where(Ciudadano.id.in_(select(Encuesta.ciudadano_id).distinct()))
        result = await db.execute(stmt)
        ciudadanos = list(result.scalars().all())

        if len(ciudadanos) < 10:
            raise ValueError(
                f"Insufficient data for training: {len(ciudadanos)} ciudadanos with encuestas "
                f"(minimum 10 required)"
            )

        # Collect features and labels
        feature_rows: list[list[float]] = []
        y_labels: list[int] = []

        for c in ciudadanos:
            # Fetch encuestas for this ciudadano
            enc_result = await db.execute(
                select(Encuesta)
                .where(Encuesta.ciudadano_id == c.id)
                .order_by(Encuesta.fecha_encuesta.desc())
            )
            encuestas = list(enc_result.scalars().all())

            # Count events attended
            evt_result = await db.execute(
                select(func.count(EventoAsistente.id)).where(
                    EventoAsistente.ciudadano_id == c.id,
                    EventoAsistente.asistio.is_(True),
                )
            )
            num_eventos = evt_result.scalar_one()

            features = self.extract_features(c, encuestas, num_eventos)
            feature_vector = [features[col] for col in FEATURE_COLUMNS]
            feature_rows.append(feature_vector)

            # Target: did the latest encuesta indicate MC?
            latest = encuestas[0] if encuestas else None
            y_labels.append(
                1 if latest and latest.intencion_voto == IntencionVotoCiudadano.MC else 0
            )

        # Train/test split
        x_train, x_test, y_train, y_test = train_test_split(
            feature_rows, y_labels, test_size=0.2, random_state=42, stratify=y_labels
        )

        clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
        clf.fit(x_train, y_train)

        # Evaluate
        y_pred = clf.predict(x_test)
        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        cm = confusion_matrix(y_test, y_pred).tolist()

        # Version and persist
        version = f"v{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        self._save_model(clf, version)
        self._model = clf
        self._model_version = version

        logger.info(
            "Trained voter scoring model %s — accuracy=%.3f, f1=%.3f, samples=%d",
            version,
            acc,
            f1,
            len(feature_rows),
        )

        return {
            "modelo_version": version,
            "accuracy": round(acc, 4),
            "f1_score": round(f1, 4),
            "confusion_matrix": cm,
            "total_samples": len(feature_rows),
        }

    # ── Single scoring ───────────────────────────────────

    def score_ciudadano(
        self,
        ciudadano: Ciudadano,
        encuestas: list[Encuesta],
        num_eventos_asistidos: int,
    ) -> VoterScoreResult:
        """Score a single ciudadano. Uses ML model if available, else rule-based."""
        features = self.extract_features(ciudadano, encuestas, num_eventos_asistidos)

        if self._model is not None and self._model_version is not None:
            feature_vector = [[features[col] for col in FEATURE_COLUMNS]]
            proba = self._model.predict_proba(feature_vector)[0]  # type: ignore[union-attr]
            # proba is [p_class_0, p_class_1] where class 1 = MC
            probabilidad_mc = float(proba[1]) if len(proba) > 1 else float(proba[0])
            score = probabilidad_mc * 100.0
            modelo_version = self._model_version
        else:
            score = self._rule_based_score(ciudadano, encuestas, num_eventos_asistidos)
            probabilidad_mc = score / 100.0
            modelo_version = "rule_based_v1"

        return VoterScoreResult(
            score=round(score, 2),
            probabilidad_mc=round(probabilidad_mc, 4),
            segmento=_segmento_from_score(score),
            features=features,
            modelo_version=modelo_version,
        )

    # ── Batch scoring ────────────────────────────────────

    async def score_all(
        self,
        db: AsyncSession,
        org_id: int | None = None,
    ) -> dict:
        """Batch-score all ciudadanos, optionally filtered by org_id.

        Uses bulk upsert (ON CONFLICT) for VoterScore records.
        Returns summary with total_scored, segmento_breakdown, modelo_version.
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        # Build ciudadano query
        stmt = select(Ciudadano)
        if org_id is not None:
            stmt = stmt.where(Ciudadano.org_id == org_id)
        result = await db.execute(stmt)
        ciudadanos = list(result.scalars().all())

        if not ciudadanos:
            return {
                "total_scored": 0,
                "segmento_breakdown": {},
                "modelo_version": self._model_version or "rule_based_v1",
            }

        # Pre-fetch encuestas and event counts in batch for performance
        ciudadano_ids = [c.id for c in ciudadanos]

        # Encuestas grouped by ciudadano_id
        enc_result = await db.execute(
            select(Encuesta)
            .where(Encuesta.ciudadano_id.in_(ciudadano_ids))
            .order_by(Encuesta.fecha_encuesta.desc())
        )
        all_encuestas = list(enc_result.scalars().all())
        encuestas_by_ciudadano: dict[int, list[Encuesta]] = {}
        for enc in all_encuestas:
            encuestas_by_ciudadano.setdefault(enc.ciudadano_id, []).append(enc)

        # Event attendance counts
        evt_result = await db.execute(
            select(
                EventoAsistente.ciudadano_id,
                func.count(EventoAsistente.id).label("cnt"),
            )
            .where(
                EventoAsistente.ciudadano_id.in_(ciudadano_ids),
                EventoAsistente.asistio.is_(True),
            )
            .group_by(EventoAsistente.ciudadano_id)
        )
        eventos_count: dict[int, int] = {row.ciudadano_id: row.cnt for row in evt_result.all()}

        # Score each ciudadano
        now = datetime.now(UTC)
        upsert_values: list[dict] = []
        segmento_counts: dict[str, int] = {}

        for c in ciudadanos:
            encuestas = encuestas_by_ciudadano.get(c.id, [])
            num_eventos = eventos_count.get(c.id, 0)

            result_score = self.score_ciudadano(c, encuestas, num_eventos)

            upsert_values.append(
                {
                    "ciudadano_id": c.id,
                    "score": result_score.score,
                    "probabilidad_mc": result_score.probabilidad_mc,
                    "segmento": result_score.segmento.value,
                    "features": result_score.features,
                    "modelo_version": result_score.modelo_version,
                    "scored_at": now,
                    "org_id": c.org_id,
                }
            )

            seg_key = result_score.segmento.value
            segmento_counts[seg_key] = segmento_counts.get(seg_key, 0) + 1

        # Bulk upsert in batches of 500
        batch_size = 500
        for i in range(0, len(upsert_values), batch_size):
            batch = upsert_values[i : i + batch_size]
            insert_stmt = pg_insert(VoterScore).values(batch)
            upsert_stmt = insert_stmt.on_conflict_do_update(
                constraint="uq_voter_scores_ciudadano_id",
                set_={
                    "score": insert_stmt.excluded.score,
                    "probabilidad_mc": insert_stmt.excluded.probabilidad_mc,
                    "segmento": insert_stmt.excluded.segmento,
                    "features": insert_stmt.excluded.features,
                    "modelo_version": insert_stmt.excluded.modelo_version,
                    "scored_at": insert_stmt.excluded.scored_at,
                    "org_id": insert_stmt.excluded.org_id,
                },
            )
            await db.execute(upsert_stmt)

        await db.flush()

        return {
            "total_scored": len(upsert_values),
            "segmento_breakdown": segmento_counts,
            "modelo_version": self._model_version or "rule_based_v1",
        }


# Module-level singleton for reuse across requests
voter_scoring_engine = VoterScoringEngine()
