"""HuggingFace model wrappers for political content analysis in Spanish.

Provides lazy-loaded, singleton-cached pipelines for:
- Controversy detection (Spanish RoBERTa)
- Toxicity classification (multilingual/Spanish)
- Zero-shot topic classification (XLM-RoBERTa XNLI)

All models degrade gracefully: if a model fails to load, the corresponding
method returns ``None`` instead of raising.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Political topic candidates for zero-shot classification
# ---------------------------------------------------------------------------
POLITICAL_TOPICS: list[str] = [
    "campaña",
    "gobierno",
    "seguridad",
    "economía",
    "salud",
    "educación",
    "corrupción",
    "medio_ambiente",
]

# ---------------------------------------------------------------------------
# Model identifiers — centralised so they can be overridden via env vars later
# ---------------------------------------------------------------------------
CONTROVERSY_MODEL_ID = "PlanTL-GOB-ES/roberta-base-bne"
TOXICITY_MODEL_ID = "citizenlab/distilbert-base-multilingual-cased-toxicity"
TOPIC_MODEL_ID = "joeddav/xlm-roberta-large-xnli"

# Maximum input length (characters) to send to transformer models.
_MAX_INPUT_LEN = 2048


class _ModelRegistry:
    """Thread-safe, lazy-loading registry for HuggingFace pipelines.

    Each model is loaded at most once.  If loading fails the slot is set to
    a sentinel (``_FAILED``) so we never retry a broken import inside the
    same worker process.
    """

    _FAILED = object()

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._controversy_pipeline: Any | None = None
        self._toxicity_pipeline: Any | None = None
        self._topic_pipeline: Any | None = None

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _safe_import_pipeline():  # noqa: ANN205
        """Import ``transformers.pipeline`` with a clear error message."""
        try:
            from transformers import pipeline  # type: ignore[import-untyped]
            return pipeline
        except ImportError:
            logger.error(
                "transformers library not installed. "
                "Install with: pip install 'transformers[torch]'"
            )
            return None

    # -- controversy ---------------------------------------------------------

    @property
    def controversy(self) -> Any | None:
        if self._controversy_pipeline is self._FAILED:
            return None
        if self._controversy_pipeline is not None:
            return self._controversy_pipeline

        with self._lock:
            # Double-check after acquiring the lock.
            if self._controversy_pipeline is not None:
                return None if self._controversy_pipeline is self._FAILED else self._controversy_pipeline

            pipeline_fn = self._safe_import_pipeline()
            if pipeline_fn is None:
                self._controversy_pipeline = self._FAILED
                return None

            try:
                self._controversy_pipeline = pipeline_fn(
                    "text-classification",
                    model=CONTROVERSY_MODEL_ID,
                    truncation=True,
                    max_length=512,
                )
                logger.info(
                    "Controversy model loaded: %s", CONTROVERSY_MODEL_ID
                )
            except Exception:
                logger.warning(
                    "Failed to load controversy model (%s)",
                    CONTROVERSY_MODEL_ID,
                    exc_info=True,
                )
                self._controversy_pipeline = self._FAILED
                return None

        return self._controversy_pipeline

    # -- toxicity ------------------------------------------------------------

    @property
    def toxicity(self) -> Any | None:
        if self._toxicity_pipeline is self._FAILED:
            return None
        if self._toxicity_pipeline is not None:
            return self._toxicity_pipeline

        with self._lock:
            if self._toxicity_pipeline is not None:
                return None if self._toxicity_pipeline is self._FAILED else self._toxicity_pipeline

            pipeline_fn = self._safe_import_pipeline()
            if pipeline_fn is None:
                self._toxicity_pipeline = self._FAILED
                return None

            try:
                self._toxicity_pipeline = pipeline_fn(
                    "text-classification",
                    model=TOXICITY_MODEL_ID,
                    truncation=True,
                    max_length=512,
                )
                logger.info(
                    "Toxicity model loaded: %s", TOXICITY_MODEL_ID
                )
            except Exception:
                logger.warning(
                    "Failed to load toxicity model (%s)",
                    TOXICITY_MODEL_ID,
                    exc_info=True,
                )
                self._toxicity_pipeline = self._FAILED
                return None

        return self._toxicity_pipeline

    # -- topic (zero-shot) ---------------------------------------------------

    @property
    def topic(self) -> Any | None:
        if self._topic_pipeline is self._FAILED:
            return None
        if self._topic_pipeline is not None:
            return self._topic_pipeline

        with self._lock:
            if self._topic_pipeline is not None:
                return None if self._topic_pipeline is self._FAILED else self._topic_pipeline

            pipeline_fn = self._safe_import_pipeline()
            if pipeline_fn is None:
                self._topic_pipeline = self._FAILED
                return None

            try:
                self._topic_pipeline = pipeline_fn(
                    "zero-shot-classification",
                    model=TOPIC_MODEL_ID,
                )
                logger.info(
                    "Topic classification model loaded: %s", TOPIC_MODEL_ID
                )
            except Exception:
                logger.warning(
                    "Failed to load topic model (%s)",
                    TOPIC_MODEL_ID,
                    exc_info=True,
                )
                self._topic_pipeline = self._FAILED
                return None

        return self._topic_pipeline


# Module-level singleton — shared by all Celery workers in the same process.
model_registry = _ModelRegistry()


# ---------------------------------------------------------------------------
# Public inference helpers
# ---------------------------------------------------------------------------

def predict_controversy(text: str) -> float | None:
    """Return a controversy score in [0.0, 1.0] or ``None`` on failure.

    Uses the Spanish RoBERTa model's output probabilities.  Because this is a
    masked-language model repurposed via ``text-classification``, we interpret
    the *negative / toxic* label probability as the controversy signal.
    """
    pipe = model_registry.controversy
    if pipe is None:
        return None

    try:
        text = text[:_MAX_INPUT_LEN]
        results: list[dict[str, Any]] = pipe(text, top_k=None)  # type: ignore[operator]

        # The model returns label probabilities.  We look for the label most
        # associated with controversy / negativity.  Different fine-tuned heads
        # expose different label sets, so we search flexibly.
        neg_labels = {"LABEL_0", "negative", "toxic", "hateful", "controversy"}
        score = 0.0
        for item in results:
            if item.get("label", "").lower() in neg_labels:
                score = max(score, item["score"])

        # If none of the expected labels matched we fall back to the highest-
        # scoring non-neutral label capped at 0.5 (conservative).
        if score == 0.0 and results:
            score = min(max(r["score"] for r in results), 0.5)

        return round(score, 4)
    except Exception:
        logger.warning("Controversy prediction failed", exc_info=True)
        return None


def predict_toxicity(text: str) -> float | None:
    """Return a toxicity score in [0.0, 1.0] or ``None`` on failure."""
    pipe = model_registry.toxicity
    if pipe is None:
        return None

    try:
        text = text[:_MAX_INPUT_LEN]
        results: list[dict[str, Any]] = pipe(text, top_k=None)  # type: ignore[operator]

        # citizenlab model uses "toxic" / "non-toxic" labels.
        for item in results:
            label = item.get("label", "").lower()
            if label in {"toxic", "toxicity", "LABEL_1".lower()}:
                return round(item["score"], 4)

        # Fallback: 1 - non-toxic score
        for item in results:
            label = item.get("label", "").lower()
            if label in {"non-toxic", "non_toxic", "LABEL_0".lower()}:
                return round(1.0 - item["score"], 4)

        return 0.0
    except Exception:
        logger.warning("Toxicity prediction failed", exc_info=True)
        return None


def predict_topics(
    text: str,
    candidate_labels: list[str] | None = None,
    *,
    threshold: float = 0.25,
    max_topics: int = 5,
) -> list[dict[str, float]] | None:
    """Return a list of ``{"label": ..., "score": ...}`` dicts or ``None``.

    Only topics whose confidence exceeds *threshold* are included, sorted by
    score descending.
    """
    pipe = model_registry.topic
    if pipe is None:
        return None

    if candidate_labels is None:
        candidate_labels = POLITICAL_TOPICS

    try:
        text = text[:_MAX_INPUT_LEN]
        result = pipe(  # type: ignore[operator]
            text,
            candidate_labels=candidate_labels,
            multi_label=True,
            hypothesis_template="Este texto trata sobre {}.",
        )

        topics: list[dict[str, float]] = []
        for label, score in zip(result["labels"], result["scores"], strict=False):
            if score >= threshold:
                topics.append({"label": label, "score": round(score, 4)})

        return topics[:max_topics]
    except Exception:
        logger.warning("Topic classification failed", exc_info=True)
        return None
