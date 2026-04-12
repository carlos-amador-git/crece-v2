"""Main NLP analysis pipeline for CRECE v2.0 political content.

Combines pysentimiento (sentiment, emotion, hate-speech), spaCy NER, and
HuggingFace transformer models (controversy, toxicity, zero-shot topic
classification) into a single ``analyze()`` call.

All models are lazy-loaded on first use.  If any model is unavailable the
corresponding field degrades to ``None`` without crashing the pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.nlp.platform_weights import normalize_sentiment

logger = logging.getLogger(__name__)

# Version tag attached to every multi-model result.
_MULTI_MODEL_VERSION = "multi-model-v1"


# ---------------------------------------------------------------------------
# Result dataclass — kept for backward compatibility with existing consumers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SentimentResult:
    """Structured NLP analysis output."""

    sentiment_score: float
    sentiment_label: str
    emotions: dict[str, float] = field(default_factory=dict)
    topics: list[str] = field(default_factory=list)
    entities: list[dict[str, str]] = field(default_factory=list)
    is_toxic: bool = False
    toxicity_score: float = 0.0
    propaganda_labels: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------


class NLPAnalyzer:
    """Multi-model NLP analysis class.

    Loads pysentimiento (sentiment, emotion, hate speech), spaCy NER, and
    HuggingFace transformer pipelines.  Models are loaded lazily on first
    call to ``analyze()`` or ``analyze_full()``.
    """

    def __init__(self) -> None:
        self._sentiment = None
        self._emotion = None
        self._hate = None
        self._spacy_nlp = None
        self._sentiment_spanish = None
        self._loaded = False

    # ---- model loading -----------------------------------------------------

    def _load_models(self) -> None:
        if self._loaded:
            return

        try:
            from pysentimiento import create_analyzer  # type: ignore[import-untyped]

            self._sentiment = create_analyzer(task="sentiment", lang="es")
            self._emotion = create_analyzer(task="emotion", lang="es")
            self._hate = create_analyzer(task="hate_speech", lang="es")
            logger.info("pysentimiento models loaded successfully")
        except Exception as e:
            logger.warning("Failed to load pysentimiento models: %s", e)

        try:
            from sentiment_analysis_spanish import (
                sentiment_analysis,  # type: ignore[import-untyped]
            )

            self._sentiment_spanish = sentiment_analysis.SentimentAnalysisSpanish()
            logger.info("sentiment-analysis-spanish model loaded successfully")
        except Exception as e:
            logger.warning("Failed to load sentiment-analysis-spanish: %s", e)

        try:
            import spacy  # type: ignore[import-untyped]

            self._spacy_nlp = spacy.load("es_core_news_md")
            logger.info("spaCy es_core_news_md loaded successfully")
        except Exception as e:
            logger.warning("Failed to load spaCy model: %s", e)

        self._loaded = True

    # ---- legacy interface (backward compatible) ----------------------------

    def analyze(self, text: str) -> SentimentResult:
        """Full NLP pipeline: sentiment, emotion, toxicity, NER, topic extraction.

        Returns the legacy ``SentimentResult`` dataclass.  For the enriched
        output format with controversy / toxicity / zero-shot topics use
        ``analyze_full()`` instead.
        """
        self._load_models()

        if not text or not text.strip():
            return SentimentResult(sentiment_score=0.0, sentiment_label="neutral")

        text = text[:10_000]

        # Sentiment
        score = 0.0
        label = "neutral"
        if self._sentiment:
            out = self._sentiment.predict(text)
            p = out.probas
            score = p.get("POS", 0.0) - p.get("NEG", 0.0)
            raw_label = out.output.lower()
            label = {"pos": "positive", "neg": "negative", "neu": "neutral"}.get(
                raw_label, raw_label
            )

        # Emotions
        emotions: dict[str, float] = {}
        if self._emotion:
            emo = self._emotion.predict(text)
            emotions = {k.lower(): round(v, 4) for k, v in emo.probas.items()}

        # Toxicity (pysentimiento hate-speech)
        is_toxic = False
        tox_score = 0.0
        if self._hate:
            h = self._hate.predict(text)
            tox_score = max(
                h.probas.get("hateful", 0.0),
                h.probas.get("targeted", 0.0),
                h.probas.get("aggressive", 0.0),
            )
            is_toxic = tox_score > 0.5

        # NER + topics
        entities: list[dict[str, str]] = []
        topics: list[str] = []
        if self._spacy_nlp:
            doc = self._spacy_nlp(text[:5000])
            entities = [{"text": e.text, "label": e.label_} for e in doc.ents]
            topics = list(
                {t.lemma_.lower() for t in doc if t.pos_ in ("NOUN", "PROPN") and len(t.text) > 2}
            )[:20]

        return SentimentResult(
            sentiment_score=round(score, 4),
            sentiment_label=label,
            emotions=emotions,
            topics=topics,
            entities=entities,
            is_toxic=is_toxic,
            toxicity_score=round(tox_score, 4),
        )

    # ---- enriched interface ------------------------------------------------

    def analyze_full(
        self,
        text: str,
        *,
        platform: str | None = None,
    ) -> dict[str, Any]:
        """Enriched NLP pipeline returning a dict with all model outputs.

        Parameters
        ----------
        text:
            Raw post / comment text.
        platform:
            One of ``twitter``, ``instagram``, ``facebook``, ``tiktok``,
            ``youtube``, ``bluesky``.  When provided, an additional
            ``platform_adjusted_sentiment`` field is included, normalised
            for known platform bias.

        Returns
        -------
        dict with keys:
            - sentiment
            - sentiment_secondary
            - controversy_score
            - toxicity
            - topics
            - platform_adjusted_sentiment
            - modelo_ia
        """
        self._load_models()

        # Fast-path for empty input.
        if not text or not text.strip():
            return _empty_result()

        text = text[:10_000]

        # -- 1. Sentiment (pysentimiento) ------------------------------------
        sentiment_dict = self._predict_sentiment(text)

        # -- 1b. Secondary sentiment (sentiment-analysis-spanish CNN) ---------
        sentiment_secondary = self._predict_sentiment_spanish(text)

        # -- 2. Controversy (HuggingFace) ------------------------------------
        controversy_score = self._predict_controversy(text)

        # -- 3. Toxicity (HuggingFace, with pysentimiento fallback) ----------
        toxicity_score = self._predict_toxicity(text)

        # -- 4. Topic classification (HuggingFace zero-shot) -----------------
        topics = self._predict_topics(text)

        # -- 5. Platform-adjusted sentiment ----------------------------------
        raw_score = sentiment_dict["score"]
        platform_adjusted: float | None = None
        if platform:
            # normalize_sentiment expects [-1, 1]; our raw_score is already
            # in that range (POS - NEG).
            platform_adjusted = round(_remap_to_unit(normalize_sentiment(raw_score, platform)), 4)

        return {
            "sentiment": sentiment_dict,
            "sentiment_secondary": sentiment_secondary,
            "controversy_score": controversy_score,
            "toxicity": toxicity_score,
            "topics": topics,
            "platform_adjusted_sentiment": platform_adjusted,
            "modelo_ia": _MULTI_MODEL_VERSION,
        }

    # ---- private predict helpers -------------------------------------------

    def _predict_sentiment(self, text: str) -> dict[str, Any]:
        """Run pysentimiento sentiment and return structured dict."""
        if not self._sentiment:
            return {
                "label": "NEU",
                "score": 0.0,
                "modelo_ia": None,
            }

        try:
            out = self._sentiment.predict(text)
            p = out.probas
            raw_label = out.output.upper()
            score = p.get("POS", 0.0) - p.get("NEG", 0.0)
            return {
                "label": raw_label,
                "score": round(score, 4),
                "modelo_ia": "pysentimiento/robertuito",
            }
        except Exception:
            logger.warning("Sentiment prediction failed", exc_info=True)
            return {
                "label": "NEU",
                "score": 0.0,
                "modelo_ia": None,
            }

    def _predict_sentiment_spanish(self, text: str) -> dict[str, Any]:
        """Run sentiment-analysis-spanish CNN model as secondary validation.

        Returns a dict with label, score, and modelo_ia.  The underlying model
        returns a float in [0, 1] where 0 = negative, 1 = positive.  We remap
        to a bipolar [-1, 1] score for consistency with pysentimiento output.
        """
        if not self._sentiment_spanish:
            return {
                "label": "NEU",
                "score": 0.0,
                "modelo_ia": None,
            }

        try:
            # sentiment() returns float in [0, 1]: 0=negative, 1=positive
            raw = self._sentiment_spanish.sentiment(text)
            # Remap [0, 1] -> [-1, 1] for consistency
            bipolar_score = round((raw * 2.0) - 1.0, 4)

            if bipolar_score > 0.15:
                label = "POS"
            elif bipolar_score < -0.15:
                label = "NEG"
            else:
                label = "NEU"

            return {
                "label": label,
                "score": bipolar_score,
                "modelo_ia": "sentiment-spanish/cnn",
            }
        except Exception:
            logger.warning("sentiment-spanish prediction failed", exc_info=True)
            return {
                "label": "NEU",
                "score": 0.0,
                "modelo_ia": None,
            }

    def _predict_controversy(self, text: str) -> float | None:
        """Delegate to HuggingFace controversy model."""
        try:
            from app.nlp.huggingface_models import predict_controversy

            return predict_controversy(text)
        except Exception:
            logger.warning("Controversy import/prediction failed", exc_info=True)
            return None

    def _predict_toxicity(self, text: str) -> float | None:
        """Try HuggingFace toxicity first, fall back to pysentimiento hate-speech."""
        # Primary: HuggingFace multilingual toxicity model
        try:
            from app.nlp.huggingface_models import predict_toxicity

            hf_score = predict_toxicity(text)
            if hf_score is not None:
                return hf_score
        except Exception:
            logger.warning("HF toxicity import/prediction failed", exc_info=True)

        # Fallback: pysentimiento hate-speech model
        if self._hate:
            try:
                h = self._hate.predict(text)
                score = max(
                    h.probas.get("hateful", 0.0),
                    h.probas.get("targeted", 0.0),
                    h.probas.get("aggressive", 0.0),
                )
                return round(score, 4)
            except Exception:
                logger.warning("pysentimiento hate fallback failed", exc_info=True)

        return None

    def _predict_topics(self, text: str) -> list[dict[str, float]] | None:
        """Delegate to HuggingFace zero-shot topic classifier."""
        try:
            from app.nlp.huggingface_models import predict_topics

            return predict_topics(text)
        except Exception:
            logger.warning("Topic classification import/prediction failed", exc_info=True)
            return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _remap_to_unit(bipolar: float) -> float:
    """Map a [-1, 1] score to [0, 1] for ``platform_adjusted_sentiment``."""
    return (bipolar + 1.0) / 2.0


def _empty_result() -> dict[str, Any]:
    """Canonical empty result when input text is blank."""
    return {
        "sentiment": {
            "label": "NEU",
            "score": 0.0,
            "modelo_ia": None,
        },
        "sentiment_secondary": {
            "label": "NEU",
            "score": 0.0,
            "modelo_ia": None,
        },
        "controversy_score": None,
        "toxicity": None,
        "topics": None,
        "platform_adjusted_sentiment": None,
        "modelo_ia": _MULTI_MODEL_VERSION,
    }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

nlp_analyzer = NLPAnalyzer()
