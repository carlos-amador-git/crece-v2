"""TopicExtractor — Sprint S1 T5.

Extracción dual (emoción Plutchik-6 + 1-3 topics del seed 12) usando Gemma 3:12b
vía Ollama. Prompt validado en S0 T0.4 con Kappa=0.810 (emoción) y precisión=75%
(topics). Ver `backend/research/2026-04-19/t04_prompt.txt` y el reporte
`plutchik_topics_validation.md`.

Decisiones vinculantes:
- D-15/D-16: Gemma 3:12b local como baseline NLP (reproducibilidad + costo $0)
- D-21: dual-mode Mac M4 (host.docker.internal) primario → Coolify VPS failover
- Temperature=0.0, seed=42 → outputs reproducibles
- SLO: warm 60s, cold 180s (primera inferencia tras idle del modelo)

Contrato de retorno:
    {
        "emocion": "trust" | "anger" | "joy" | "fear" | "sadness" | "disgust" | None,
        "topics": list[str],        # 1-3 elementos del seed 12
        "model": "gemma3:12b",
        "extracted_at": ISO-8601 UTC
    }

Fallback ante fallo de Gemma o JSON inválido:
    {"emocion": None, "topics": ["otro"], "_err": "mensaje", ...}
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# Seed fijo validado en S0 T0.4 (12 topics políticos MX)
TOPIC_SEED: frozenset[str] = frozenset(
    {
        "economia",
        "seguridad",
        "educacion",
        "salud",
        "corrupcion",
        "movilidad",
        "genero",
        "medioambiente",
        "gobierno",
        "politica_electoral",
        "institucional",
        "otro",
    }
)

EMOTION_SEED: frozenset[str] = frozenset(
    {"trust", "anger", "joy", "fear", "sadness", "disgust"}
)

# Prompt EXACTO del archivo validado (no modificar texto)
_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "research"
    / "2026-04-19"
    / "t04_prompt.txt"
)


def _load_prompt_template() -> str:
    """Carga el prompt EXACTO del archivo validado en S0 T0.4.

    Si el archivo no existe (contexto test / instalación parcial), cae al
    fallback inline idéntico al archivo.
    """
    try:
        return _PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning(
            "t04_prompt.txt no encontrado en %s — usando fallback inline",
            _PROMPT_PATH,
        )
        return (
            'Clasifica este comentario politico mexicano en DOS dimensiones simultaneas.\n\n'
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


_PROMPT_TEMPLATE = _load_prompt_template()

# Regex para extraer JSON aun cuando Gemma añada preámbulo o code-fences
_JSON_OBJ_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)


class TopicExtractor:
    """Cliente async para extracción emoción+topics con Gemma 3:12b.

    Params:
        base_url: URL de Ollama. Default: settings.OLLAMA_BASE_URL
                  (Mac M4 primario vía `host.docker.internal:11434` desde container;
                   Coolify VPS `http://163.245.208.96:11434` como failover D-21).
        model:    nombre exacto del modelo. Default: "gemma3:12b".
        timeout_warm:  timeout en segundos para inferencias con modelo ya cargado.
        timeout_cold:  timeout en segundos para la primera inferencia tras idle
                       (carga ~8GB desde disco puede tardar hasta 180s).
    """

    MODEL = "gemma3:12b"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_warm: float = 60.0,
        timeout_cold: float = 180.0,
    ) -> None:
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or self.MODEL
        self.timeout_warm = timeout_warm
        self.timeout_cold = timeout_cold
        self._warm = False  # se marca True tras primera inferencia exitosa

    def _build_prompt(
        self,
        comment_text: str,
        post_text: str | None,
        plataforma: str,
    ) -> str:
        """Rellena las placeholders del prompt validado."""
        return _PROMPT_TEMPLATE.format(
            comment_text=(comment_text or "").strip()[:2000],
            post_text=(post_text or "").strip()[:500] if post_text else "N/A",
            plataforma=plataforma or "desconocida",
        )

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any] | None:
        """Extrae un objeto JSON válido del output del modelo.

        Gemma ocasionalmente envuelve en ```json ... ``` o añade texto antes.
        """
        if not raw:
            return None
        cleaned = raw.strip()
        # quita code fences si aparecen
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        # último recurso: primer objeto JSON que haga match en el string
        m = _JSON_OBJ_RE.search(cleaned)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None

    @classmethod
    def _normalize(cls, parsed: dict[str, Any]) -> dict[str, Any]:
        """Valida y normaliza emoción + topics al seed fijo."""
        emocion_raw = parsed.get("emocion")
        emocion: str | None = None
        if isinstance(emocion_raw, str):
            e = emocion_raw.strip().lower()
            if e in EMOTION_SEED:
                emocion = e

        topics_raw = parsed.get("topics")
        topics: list[str] = []
        if isinstance(topics_raw, list):
            for t in topics_raw:
                if not isinstance(t, str):
                    continue
                tn = t.strip().lower()
                if tn in TOPIC_SEED and tn not in topics:
                    topics.append(tn)
                if len(topics) >= 3:
                    break
        if not topics:
            topics = ["otro"]

        return {"emocion": emocion, "topics": topics}

    async def extract(
        self,
        text: str,
        post_text: str | None = None,
        plataforma: str = "desconocida",
    ) -> dict[str, Any]:
        """Extrae emoción+topics del `text` usando Gemma 3:12b.

        Args:
            text:       comentario/post a clasificar.
            post_text:  post original al que responde el comment (opcional).
            plataforma: TWITTER | INSTAGRAM | FACEBOOK | TIKTOK | YOUTUBE | ...

        Returns:
            Dict con emocion, topics, model, extracted_at. En caso de fallo se
            añade `_err` con el mensaje y se retorna `topics=["otro"]`.
        """
        now = lambda: datetime.now(UTC).isoformat()

        if not settings.OLLAMA_ENABLED:
            return {
                "emocion": None,
                "topics": ["otro"],
                "model": self.model,
                "extracted_at": now(),
                "_err": "ollama_disabled",
            }

        if not text or not text.strip():
            return {
                "emocion": None,
                "topics": ["otro"],
                "model": self.model,
                "extracted_at": now(),
                "_err": "empty_text",
            }

        prompt = self._build_prompt(text, post_text, plataforma)
        timeout = self.timeout_warm if self._warm else self.timeout_cold
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "seed": 42,
                "num_predict": 100,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
                body = resp.json()
        except httpx.HTTPError as e:
            logger.warning("Gemma HTTP error: %s", e)
            return {
                "emocion": None,
                "topics": ["otro"],
                "model": self.model,
                "extracted_at": now(),
                "_err": f"http_error: {e.__class__.__name__}: {e}",
            }
        except Exception as e:
            logger.warning("Gemma unexpected error: %s", e)
            return {
                "emocion": None,
                "topics": ["otro"],
                "model": self.model,
                "extracted_at": now(),
                "_err": f"unexpected: {e.__class__.__name__}: {e}",
            }

        raw_response = str(body.get("response", ""))
        parsed = self._parse_json(raw_response)
        if parsed is None:
            return {
                "emocion": None,
                "topics": ["otro"],
                "model": self.model,
                "extracted_at": now(),
                "_err": "json_parse_failed",
                "_raw": raw_response[:500],
            }

        normalized = self._normalize(parsed)
        self._warm = True  # primera corrida OK → subsecuentes usan timeout_warm
        return {
            **normalized,
            "model": self.model,
            "extracted_at": now(),
        }
