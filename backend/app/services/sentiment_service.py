from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Sprint S2 T3 — Plutchik-6 classifier (Gemma 3:12b). Prompt validado en S0 T0.4
# (Kappa=0.810, precisión topic=75%). Ver:
#   backend/research/2026-04-19/plutchik_topics_validation.md
#   backend/research/2026-04-19/t04_prompt.txt

_PLUTCHIK_EMOTIONS: tuple[str, ...] = (
    "trust",
    "anger",
    "joy",
    "fear",
    "sadness",
    "disgust",
)

_PLUTCHIK_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "research"
    / "2026-04-19"
    / "t04_prompt.txt"
)


def _load_plutchik_prompt() -> str:
    """Carga el prompt exacto validado en T0.4. Fallback inline si el archivo no existe."""
    try:
        return _PLUTCHIK_PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning(
            "t04_prompt.txt no encontrado en %s — usando fallback inline",
            _PLUTCHIK_PROMPT_PATH,
        )
        return (
            "Clasifica este comentario politico mexicano en DOS dimensiones simultaneas.\n\n"
            "CONTEXTO:\n"
            "- Post original (del politico): {post_text}\n"
            "- Plataforma: {plataforma}\n\n"
            "COMENTARIO:\n"
            '"{comment_text}"\n\n'
            "INSTRUCCIONES:\n"
            "(a) Identifica la EMOCION dominante (UNA sola) del conjunto Plutchik-6:\n"
            "    trust, anger, joy, fear, sadness, disgust\n"
            "(b) Identifica 1 a 3 TOPICS del seed fijo de 12 (en orden de relevancia):\n"
            "    economia, seguridad, educacion, salud, corrupcion, movilidad,\n"
            "    genero, medioambiente, gobierno, politica_electoral, institucional, otro\n\n"
            "RESPONDE EXCLUSIVAMENTE un objeto JSON valido sin texto adicional, sin markdown,\n"
            "sin bloques de codigo. Usa exactamente estas llaves:\n\n"
            '{{"emocion": "<una de las 6>", "topics": ["<topic1>", "<topic2?>", "<topic3?>"]}}\n\n'
            "Si el comentario es ambiguo, elige la emocion predominante y el topic principal.\n"
            'Si no hay topic politico claro, usa "otro".\n'
        )


_PLUTCHIK_PROMPT_TEMPLATE = _load_plutchik_prompt()
_JSON_OBJ_RE = re.compile(r"\{[\s\S]+?\}")


def _zero_plutchik(with_err: str | None = None) -> dict[str, float | str]:
    """Distribución todo-cero (fallback cuando Gemma falla 2 retries)."""
    out: dict[str, float | str] = {e: 0.0 for e in _PLUTCHIK_EMOTIONS}
    if with_err:
        out["_err"] = with_err
    return out


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
        self._sentiment_spanish = None
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
            logger.warning("pysentimiento not installed. Install with: pip install 'crece-v2[nlp]'")
        try:
            from sentiment_analysis_spanish import sentiment_analysis

            self._sentiment_spanish = sentiment_analysis.SentimentAnalysisSpanish()
        except ImportError:
            logger.warning(
                "sentiment-analysis-spanish not installed. "
                "Install with: pip install 'crece-v2[nlp]'"
            )
        except Exception as e:
            logger.warning("Failed to load sentiment-analysis-spanish: %s", e)

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
            sentiment_score = float(probas.get("POS", 0.0)) - float(probas.get("NEG", 0.0))
            sentiment_label = sent_output.output.lower()
            # Normalize labels
            label_map = {"pos": "positive", "neg": "negative", "neu": "neutral"}
            sentiment_label = label_map.get(sentiment_label, sentiment_label)

        # Emotion analysis
        emotions: dict[str, float] = {}
        if self._emotion_analyzer is not None:
            emo_output = self._emotion_analyzer.predict(text)
            emotions = {k.lower(): round(float(v), 4) for k, v in emo_output.probas.items()}

        # Hate / toxicity detection
        is_toxic = False
        toxicity_score = 0.0
        if self._hate_analyzer is not None:
            hate_output = self._hate_analyzer.predict(text)
            hateful_prob = float(hate_output.probas.get("hateful", 0.0))
            targeted_prob = float(hate_output.probas.get("targeted", 0.0))
            aggressive_prob = float(hate_output.probas.get("aggressive", 0.0))
            toxicity_score = max(hateful_prob, targeted_prob, aggressive_prob)
            is_toxic = toxicity_score > 0.5

        # Named Entity Recognition
        entities: list[dict[str, str]] = []
        topics: list[str] = []
        if self._nlp is not None:
            doc = self._nlp(text[:5000])  # cap input length
            entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]
            # Extract topics from nouns and proper nouns
            topics = list(
                {
                    token.lemma_.lower()
                    for token in doc
                    if token.pos_ in ("NOUN", "PROPN") and len(token.text) > 2
                }
            )[:20]

        return SentimentResult(
            sentiment_score=round(sentiment_score, 4),
            sentiment_label=sentiment_label,
            emotions=emotions,
            topics=topics,
            entities=entities,
            is_toxic=is_toxic,
            toxicity_score=round(toxicity_score, 4),
        )

    async def classify_plutchik_6(
        self,
        text: str,
        *,
        post_text: str | None = None,
        plataforma: str = "desconocida",
        base_url: str | None = None,
        model: str = "gemma3:12b",
        timeout: float = 60.0,
        max_retries: int = 2,
    ) -> dict[str, float | str]:
        """Clasifica texto en 6 emociones Plutchik con probabilidades normalizadas.

        Usa Gemma 3:12b (Ollama) con el prompt validado en S0 T0.4
        (Kappa 0.810). Como el prompt devuelve una sola emoción dominante,
        la distribución resultante asigna 1.0 a esa emoción y 0.0 al resto
        (one-hot). Cuando el parse falla o el modelo retorna string simple,
        se intenta fallback a emoción dominante única. Si tras ``max_retries``
        fallas, retorna todas 0.0 con flag ``_err``.

        Args:
            text:         comentario / post a clasificar.
            post_text:    post original al que responde (opcional, para contexto).
            plataforma:   TWITTER | INSTAGRAM | FACEBOOK | TIKTOK | YOUTUBE | ...
            base_url:     override de ``settings.OLLAMA_BASE_URL``.
            model:        modelo Ollama (default ``gemma3:12b``).
            timeout:      segundos por intento.
            max_retries:  número de intentos totales contra Gemma.

        Returns:
            dict con claves ``trust, anger, joy, fear, sadness, disgust`` cuyos
            valores suman ≈ 1.0. En caso de error, todas las claves son 0.0 y
            se añade ``_err`` con el diagnóstico.
        """
        if not text or not text.strip():
            return _zero_plutchik(with_err="empty_text")

        ollama_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        endpoint = f"{ollama_url}/api/generate"

        prompt = _PLUTCHIK_PROMPT_TEMPLATE.format(
            comment_text=(text or "").strip()[:2000],
            post_text=(post_text or "").strip()[:500] if post_text else "N/A",
            plataforma=plataforma or "desconocida",
        )
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0, "seed": 42, "num_predict": 256},
        }

        last_err: str | None = None
        raw_response: str = ""
        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.post(endpoint, json=payload)
                    resp.raise_for_status()
                    raw_response = str(resp.json().get("response", ""))
                break
            except httpx.HTTPError as e:
                last_err = f"http[{attempt}]: {e.__class__.__name__}: {e}"
                logger.warning("Gemma Plutchik %s", last_err)
                continue
            except Exception as e:
                last_err = f"unexpected[{attempt}]: {e.__class__.__name__}: {e}"
                logger.warning("Gemma Plutchik %s", last_err)
                continue
        else:
            return _zero_plutchik(with_err=last_err or "max_retries_exceeded")

        # Parse robusto: Gemma con format=json suele devolver JSON limpio, pero
        # ocasionalmente añade texto o devuelve string simple.
        dominant: str | None = None
        parsed = None
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            m = _JSON_OBJ_RE.search(cleaned)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                except json.JSONDecodeError:
                    parsed = None

        if isinstance(parsed, dict):
            emo_raw = parsed.get("emocion") or parsed.get("emotion")
            if isinstance(emo_raw, str):
                e = emo_raw.strip().lower()
                if e in _PLUTCHIK_EMOTIONS:
                    dominant = e
        elif isinstance(parsed, str):
            e = parsed.strip().lower()
            if e in _PLUTCHIK_EMOTIONS:
                dominant = e

        # Fallback final: el modelo a veces devuelve una palabra suelta sin
        # JSON. Intentar emoción dominante buscando la palabra en el raw.
        if dominant is None:
            lc = raw_response.lower()
            for e in _PLUTCHIK_EMOTIONS:
                if e in lc:
                    dominant = e
                    break

        if dominant is None:
            return _zero_plutchik(with_err="parse_failed")

        # One-hot → suma 1.0
        return {e: (1.0 if e == dominant else 0.0) for e in _PLUTCHIK_EMOTIONS}

    def analyze_secondary(self, text: str) -> SentimentResult | None:
        """Run sentiment-analysis-spanish CNN as a secondary validation model.

        Returns ``None`` if the model is unavailable.  The result contains only
        sentiment score/label (no emotions, topics, or toxicity — those come
        from the primary pipeline).
        """
        self._ensure_initialized()

        if self._sentiment_spanish is None:
            return None

        if not text or not text.strip():
            return None

        try:
            # sentiment() returns float in [0, 1]: 0 = negative, 1 = positive
            raw = float(self._sentiment_spanish.sentiment(text[:10_000]))
            # Remap [0, 1] -> [-1, 1] for consistency with pysentimiento
            bipolar_score = round((raw * 2.0) - 1.0, 4)

            if bipolar_score > 0.15:
                label = "positive"
            elif bipolar_score < -0.15:
                label = "negative"
            else:
                label = "neutral"

            return SentimentResult(
                sentiment_score=bipolar_score,
                sentiment_label=label,
            )
        except Exception:
            logger.warning("sentiment-spanish prediction failed", exc_info=True)
            return None


# Module-level singleton
sentiment_service = SentimentService()


async def classify_plutchik_6(
    text: str,
    *,
    post_text: str | None = None,
    plataforma: str = "desconocida",
    base_url: str | None = None,
    model: str = "gemma3:12b",
    timeout: float = 60.0,
    max_retries: int = 2,
) -> dict[str, float | str]:
    """Shortcut async que usa el singleton ``sentiment_service``.

    Ver :meth:`SentimentService.classify_plutchik_6` para detalles.
    """
    return await sentiment_service.classify_plutchik_6(
        text,
        post_text=post_text,
        plataforma=plataforma,
        base_url=base_url,
        model=model,
        timeout=timeout,
        max_retries=max_retries,
    )
