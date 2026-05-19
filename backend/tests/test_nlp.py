"""Tests for NLP analyzer and platform weights modules.

These tests mock pysentimiento and spaCy since they may not be installed
in the test environment. The focus is on the logic wrappers, not the models.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.nlp.analyzer import NLPAnalyzer, SentimentResult
from app.nlp.platform_weights import (
    ENGAGEMENT_NORMALIZATION,
    SENTIMENT_BIAS_CORRECTION,
    SENTIMENT_CONFIDENCE_WEIGHT,
    normalize_engagement,
    normalize_sentiment,
    weighted_sentiment,
)

# ---------------------------------------------------------------------------
# NLPAnalyzer (with mocked models)
# ---------------------------------------------------------------------------


class TestNLPAnalyzerWithMocks:
    """Test the NLPAnalyzer logic paths by mocking the underlying ML models."""

    def _build_analyzer_with_mocks(
        self,
        sentiment_output: str = "POS",
        sentiment_probas: dict | None = None,
        emotion_probas: dict | None = None,
        hate_probas: dict | None = None,
    ) -> NLPAnalyzer:
        """Build an NLPAnalyzer with fully mocked internal models."""
        analyzer = NLPAnalyzer()

        if sentiment_probas is None:
            sentiment_probas = {"POS": 0.8, "NEG": 0.1, "NEU": 0.1}
        if emotion_probas is None:
            emotion_probas = {"joy": 0.6, "anger": 0.1, "sadness": 0.05, "surprise": 0.25}
        if hate_probas is None:
            hate_probas = {"hateful": 0.05, "targeted": 0.02, "aggressive": 0.03}

        # Mock sentiment analyzer
        mock_sent = MagicMock()
        mock_sent_result = MagicMock()
        mock_sent_result.probas = sentiment_probas
        mock_sent_result.output = sentiment_output
        mock_sent.predict.return_value = mock_sent_result
        analyzer._sentiment = mock_sent

        # Mock emotion analyzer
        mock_emo = MagicMock()
        mock_emo_result = MagicMock()
        mock_emo_result.probas = emotion_probas
        mock_emo.predict.return_value = mock_emo_result
        analyzer._emotion = mock_emo

        # Mock hate speech analyzer
        mock_hate = MagicMock()
        mock_hate_result = MagicMock()
        mock_hate_result.probas = hate_probas
        mock_hate.predict.return_value = mock_hate_result
        analyzer._hate = mock_hate

        # spaCy mock
        mock_nlp = MagicMock()
        mock_doc = MagicMock()
        mock_doc.ents = []
        mock_doc.__iter__ = MagicMock(return_value=iter([]))
        mock_nlp.return_value = mock_doc
        analyzer._spacy_nlp = mock_nlp

        analyzer._loaded = True
        return analyzer

    def test_sentiment_analysis_positive(self) -> None:
        """Positive text produces positive label and score > 0."""
        analyzer = self._build_analyzer_with_mocks(
            sentiment_output="POS",
            sentiment_probas={"POS": 0.85, "NEG": 0.05, "NEU": 0.10},
        )
        result = analyzer.analyze("Excelente gestion del gobierno municipal!")
        assert result.sentiment_label == "positive"
        assert result.sentiment_score > 0
        assert result.sentiment_score == pytest.approx(0.85 - 0.05, abs=0.001)

    def test_sentiment_analysis_negative(self) -> None:
        """Negative text produces negative label and score < 0."""
        analyzer = self._build_analyzer_with_mocks(
            sentiment_output="NEG",
            sentiment_probas={"POS": 0.05, "NEG": 0.85, "NEU": 0.10},
        )
        result = analyzer.analyze("Pesima administracion, todo esta peor.")
        assert result.sentiment_label == "negative"
        assert result.sentiment_score < 0
        assert result.sentiment_score == pytest.approx(0.05 - 0.85, abs=0.001)

    def test_sentiment_analysis_neutral(self) -> None:
        """Neutral text produces near-zero score."""
        analyzer = self._build_analyzer_with_mocks(
            sentiment_output="NEU",
            sentiment_probas={"POS": 0.30, "NEG": 0.30, "NEU": 0.40},
        )
        result = analyzer.analyze("Hoy se realizo la sesion ordinaria del congreso.")
        assert result.sentiment_label == "neutral"
        assert abs(result.sentiment_score) < 0.01

    def test_sentiment_analysis_empty(self) -> None:
        """Empty or whitespace-only text returns neutral defaults."""
        analyzer = NLPAnalyzer()
        analyzer._loaded = True  # skip model loading

        result_empty = analyzer.analyze("")
        assert result_empty.sentiment_score == 0.0
        assert result_empty.sentiment_label == "neutral"

        result_whitespace = analyzer.analyze("   \n\t  ")
        assert result_whitespace.sentiment_score == 0.0
        assert result_whitespace.sentiment_label == "neutral"

    def test_toxicity_detection(self) -> None:
        """High hate speech probabilities flag content as toxic."""
        analyzer = self._build_analyzer_with_mocks(
            hate_probas={"hateful": 0.75, "targeted": 0.60, "aggressive": 0.80},
        )
        result = analyzer.analyze("Some toxic content")
        assert result.is_toxic is True
        assert result.toxicity_score > 0.5

    def test_toxicity_not_flagged(self) -> None:
        """Low hate speech probabilities do not flag content as toxic."""
        analyzer = self._build_analyzer_with_mocks(
            hate_probas={"hateful": 0.05, "targeted": 0.02, "aggressive": 0.03},
        )
        result = analyzer.analyze("Normal political content")
        assert result.is_toxic is False
        assert result.toxicity_score <= 0.5

    def test_emotions_returned(self) -> None:
        """Emotions dict is populated from pysentimiento emotion analyzer."""
        analyzer = self._build_analyzer_with_mocks(
            emotion_probas={"joy": 0.7, "anger": 0.1, "fear": 0.05, "surprise": 0.15},
        )
        result = analyzer.analyze("Que alegria!")
        assert "joy" in result.emotions
        assert result.emotions["joy"] == pytest.approx(0.7, abs=0.001)

    def test_text_truncation(self) -> None:
        """Extremely long texts are truncated before processing."""
        analyzer = self._build_analyzer_with_mocks()
        long_text = "A" * 20_000
        result = analyzer.analyze(long_text)
        # Should not raise, and the sentiment mock should have been called
        # with the truncated text (first 10k chars)
        analyzer._sentiment.predict.assert_called_once()
        called_text = analyzer._sentiment.predict.call_args[0][0]
        assert len(called_text) == 10_000

    def test_ner_extraction(self) -> None:
        """Named entities from spaCy are returned in the result."""
        analyzer = self._build_analyzer_with_mocks()

        # Set up spaCy mock to return entities
        mock_ent = MagicMock()
        mock_ent.text = "AMLO"
        mock_ent.label_ = "PER"
        mock_doc = MagicMock()
        mock_doc.ents = [mock_ent]
        mock_doc.__iter__ = MagicMock(return_value=iter([]))
        analyzer._spacy_nlp.return_value = mock_doc

        result = analyzer.analyze("AMLO dijo algo en la manana")
        assert len(result.entities) == 1
        assert result.entities[0]["text"] == "AMLO"
        assert result.entities[0]["label"] == "PER"


# ---------------------------------------------------------------------------
# NLPAnalyzer without models (graceful degradation)
# ---------------------------------------------------------------------------


class TestNLPAnalyzerNoModels:
    """Test that the analyzer degrades gracefully when models fail to load."""

    def test_analyze_without_loaded_models(self) -> None:
        """When no models loaded, analyze still returns a valid SentimentResult."""
        analyzer = NLPAnalyzer()
        analyzer._loaded = True  # pretend we tried to load but all failed

        result = analyzer.analyze("Some text here")
        assert isinstance(result, SentimentResult)
        assert result.sentiment_score == 0.0
        assert result.sentiment_label == "neutral"
        assert result.emotions == {}
        assert result.topics == []
        assert result.entities == []
        assert result.is_toxic is False


# ---------------------------------------------------------------------------
# Platform weights
# ---------------------------------------------------------------------------


class TestPlatformWeights:
    """Test platform-specific normalization functions."""

    def test_platform_weights_normalization(self) -> None:
        """Sentiment bias corrections clamp output to [-1, 1]."""
        # Twitter correction is +0.08
        corrected = normalize_sentiment(0.95, "twitter")
        assert corrected <= 1.0
        assert corrected >= -1.0

        # Negative extreme
        corrected_neg = normalize_sentiment(-0.98, "instagram")  # -0.06 correction
        assert corrected_neg >= -1.0

    def test_normalize_sentiment_correction_applied(self) -> None:
        """The correction value is correctly added to the raw score."""
        raw = 0.5
        corrected = normalize_sentiment(raw, "twitter")
        expected = raw + SENTIMENT_BIAS_CORRECTION["twitter"]
        assert corrected == pytest.approx(expected, abs=0.001)

    def test_normalize_sentiment_unknown_platform(self) -> None:
        """Unknown platforms get zero correction."""
        raw = 0.3
        corrected = normalize_sentiment(raw, "unknown_platform")
        assert corrected == pytest.approx(raw, abs=0.001)

    def test_weighted_sentiment_returns_tuple(self) -> None:
        """weighted_sentiment returns (corrected_score, confidence_weight)."""
        score, weight = weighted_sentiment(0.5, "facebook")
        expected_score = 0.5 + SENTIMENT_BIAS_CORRECTION["facebook"]
        assert score == pytest.approx(expected_score, abs=0.001)
        assert weight == SENTIMENT_CONFIDENCE_WEIGHT["facebook"]

    def test_weighted_sentiment_unknown_platform(self) -> None:
        """Unknown platform gets default weight of 0.75."""
        _, weight = weighted_sentiment(0.0, "mastodon")
        assert weight == 0.75

    def test_engagement_normalization(self) -> None:
        """Engagement normalization multiplies by platform factor."""
        raw_rate = 0.05
        normalized = normalize_engagement(raw_rate, "tiktok")
        expected = raw_rate * ENGAGEMENT_NORMALIZATION["tiktok"]
        assert normalized == pytest.approx(expected, abs=0.0001)

    def test_engagement_normalization_unknown(self) -> None:
        """Unknown platform gets multiplier of 1.0."""
        raw_rate = 0.03
        assert normalize_engagement(raw_rate, "threads") == pytest.approx(raw_rate, abs=0.0001)

    def test_all_platforms_have_corrections(self) -> None:
        """Every known platform has entries in all three dicts."""
        platforms = {"twitter", "instagram", "facebook", "tiktok", "youtube", "bluesky"}
        assert set(SENTIMENT_BIAS_CORRECTION.keys()) == platforms
        assert set(SENTIMENT_CONFIDENCE_WEIGHT.keys()) == platforms
        assert set(ENGAGEMENT_NORMALIZATION.keys()) == platforms

    def test_confidence_weights_bounded(self) -> None:
        """All confidence weights are between 0 and 1."""
        for platform, weight in SENTIMENT_CONFIDENCE_WEIGHT.items():
            assert 0.0 < weight <= 1.0, f"{platform} weight {weight} out of range"

    def test_engagement_multipliers_positive(self) -> None:
        """All engagement multipliers are positive."""
        for platform, mult in ENGAGEMENT_NORMALIZATION.items():
            assert mult > 0, f"{platform} multiplier {mult} must be positive"
