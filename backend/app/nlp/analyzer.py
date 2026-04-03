from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


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


class NLPAnalyzer:
    """Main NLP analysis class.

    Loads pysentimiento (sentiment, emotion, hate speech) and spaCy NER models.
    Models are loaded lazily on first call to analyze().
    """

    def __init__(self) -> None:
        self._sentiment = None
        self._emotion = None
        self._hate = None
        self._spacy_nlp = None
        self._loaded = False

    def _load_models(self) -> None:
        if self._loaded:
            return

        try:
            from pysentimiento import create_analyzer

            self._sentiment = create_analyzer(task="sentiment", lang="es")
            self._emotion = create_analyzer(task="emotion", lang="es")
            self._hate = create_analyzer(task="hate_speech", lang="es")
            logger.info("pysentimiento models loaded successfully")
        except Exception as e:
            logger.warning("Failed to load pysentimiento models: %s", e)

        try:
            import spacy

            self._spacy_nlp = spacy.load("es_core_news_md")
            logger.info("spaCy es_core_news_md loaded successfully")
        except Exception as e:
            logger.warning("Failed to load spaCy model: %s", e)

        self._loaded = True

    def analyze(self, text: str) -> SentimentResult:
        """Full NLP pipeline: sentiment, emotion, toxicity, NER, topic extraction."""
        self._load_models()

        if not text or not text.strip():
            return SentimentResult(sentiment_score=0.0, sentiment_label="neutral")

        # Truncate extremely long texts
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

        # Toxicity
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
            topics = list({
                t.lemma_.lower()
                for t in doc
                if t.pos_ in ("NOUN", "PROPN") and len(t.text) > 2
            })[:20]

        return SentimentResult(
            sentiment_score=round(score, 4),
            sentiment_label=label,
            emotions=emotions,
            topics=topics,
            entities=entities,
            is_toxic=is_toxic,
            toxicity_score=round(tox_score, 4),
        )


# Singleton
nlp_analyzer = NLPAnalyzer()
