from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SentimentResult:
    """Structured output from NLP sentiment analysis."""

    sentiment_score: float  # -1.0 to 1.0
    sentiment_label: str  # positive / negative / neutral / mixed
    emotions: dict[str, float] = field(default_factory=dict)
    topics: list[str] = field(default_factory=list)
    entities: list[dict[str, str]] = field(default_factory=list)
    is_toxic: bool = False
    toxicity_score: float = 0.0
    propaganda_labels: list[str] = field(default_factory=list)


class SentimentService:
    """Interface for NLP analysis using pysentimiento and spaCy.

    Loads models lazily on first use to avoid startup overhead.
    """

    def __init__(self) -> None:
        self._sentiment_analyzer = None
        self._emotion_analyzer = None
        self._hate_analyzer = None
        self._nlp = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        try:
            from pysentimiento import create_analyzer

            self._sentiment_analyzer = create_analyzer(task="sentiment", lang="es")
            self._emotion_analyzer = create_analyzer(task="emotion", lang="es")
            self._hate_analyzer = create_analyzer(task="hate_speech", lang="es")
        except ImportError:
            logger.warning(
                "pysentimiento not installed. Install with: pip install 'crece-v2[nlp]'"
            )
        try:
            import spacy

            try:
                self._nlp = spacy.load("es_core_news_md")
            except OSError:
                logger.warning(
                    "spaCy Spanish model not found. "
                    "Install with: python -m spacy download es_core_news_md"
                )
        except ImportError:
            logger.warning("spaCy not installed. Install with: pip install 'crece-v2[nlp]'")

        self._initialized = True

    def analyze(self, text: str) -> SentimentResult:
        """Run full NLP pipeline on a text string."""
        self._ensure_initialized()

        if not text or not text.strip():
            return SentimentResult(
                sentiment_score=0.0,
                sentiment_label="neutral",
            )

        # Sentiment analysis
        sentiment_score = 0.0
        sentiment_label = "neutral"
        if self._sentiment_analyzer is not None:
            sent_output = self._sentiment_analyzer.predict(text)
            probas = sent_output.probas
            # Map to score: POS=+1, NEU=0, NEG=-1
            sentiment_score = probas.get("POS", 0.0) - probas.get("NEG", 0.0)
            sentiment_label = sent_output.output.lower()
            # Normalize labels
            label_map = {"pos": "positive", "neg": "negative", "neu": "neutral"}
            sentiment_label = label_map.get(sentiment_label, sentiment_label)

        # Emotion analysis
        emotions: dict[str, float] = {}
        if self._emotion_analyzer is not None:
            emo_output = self._emotion_analyzer.predict(text)
            emotions = {k.lower(): round(v, 4) for k, v in emo_output.probas.items()}

        # Hate / toxicity detection
        is_toxic = False
        toxicity_score = 0.0
        if self._hate_analyzer is not None:
            hate_output = self._hate_analyzer.predict(text)
            hateful_prob = hate_output.probas.get("hateful", 0.0)
            targeted_prob = hate_output.probas.get("targeted", 0.0)
            aggressive_prob = hate_output.probas.get("aggressive", 0.0)
            toxicity_score = max(hateful_prob, targeted_prob, aggressive_prob)
            is_toxic = toxicity_score > 0.5

        # Named Entity Recognition
        entities: list[dict[str, str]] = []
        topics: list[str] = []
        if self._nlp is not None:
            doc = self._nlp(text[:5000])  # cap input length
            entities = [
                {"text": ent.text, "label": ent.label_}
                for ent in doc.ents
            ]
            # Extract topics from nouns and proper nouns
            topics = list({
                token.lemma_.lower()
                for token in doc
                if token.pos_ in ("NOUN", "PROPN") and len(token.text) > 2
            })[:20]

        return SentimentResult(
            sentiment_score=round(sentiment_score, 4),
            sentiment_label=sentiment_label,
            emotions=emotions,
            topics=topics,
            entities=entities,
            is_toxic=is_toxic,
            toxicity_score=round(toxicity_score, 4),
        )


# Module-level singleton
sentiment_service = SentimentService()
