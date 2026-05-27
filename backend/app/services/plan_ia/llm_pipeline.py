"""Plan IA · T1 Pipeline LLM — Sprint S4 D-17 ciclo completo.

Orquesta la generación de recomendaciones Plan IA:

1. Carga diagnóstico 18 bloques (10 Tier 1 + 8 Tier 2) vía servicios existentes.
2. Carga histórico dirigente vía RAG (`rag_memory.py`).
3. Calcula delta B13 dinámico per-dirigente (nunca literal 16%).
4. Lee el prompt vivo de `PROMPT-PLAN-IA-v{N}.md` (D-24).
5. Renderiza el prompt sustituyendo tokens `{{VARIABLE}}`.
6. Envía a Claude (default, prefill JSON) o Gemma 3:12b vía Ollama si
   AI_PROVIDER=ollama y OLLAMA_ENABLED (temperature=0.2).
7. Parsea JSON estricto.
8. Valida cada recomendación con `AntiVanityValidator`.
9. Si ≥1 rechazo: retry hasta 2 veces inyectando feedback.
10. Persiste las recomendaciones aprobadas en `recomendaciones_plan_ia` con
    estado='propuesta'.

NO mockear en servicio. La llamada al modelo es real (mockeada solo en tests).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.dirigente import Dirigente
from app.models.recomendacion_plan_ia import RecomendacionPlanIA
from app.services.diagnostico import (
    benchmark_service,
    breakout_service,
    crisis_spike_service,
    er_service,
    growth_attribution_service,
    humanizacion_service,
    matrix_2x2_service,
    sentiment_plutchik_service,
    share_like_ratio_service,
    sov_service,
)
from app.services.diagnostico_tier2 import (
    cib_detector_service,
    cross_partisan_service,
    filtro_realidad_service,
    promesas_service,
    rage_click_service,
    topic_drift_service,
    veda_compliance_service,
    violencia_politica_service,
)
from app.services.plan_ia.anti_vanity_validator import AntiVanityValidator
from app.services.plan_ia.rag_memory import fetch_historico, format_historico_for_prompt

logger = logging.getLogger(__name__)

# Path absoluto al prompt versionable (artefacto de producto, leído al runtime)
_PROMPT_VERSION = "v1"
_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "research"
    / "2026-04-19"
    / f"PROMPT-PLAN-IA-{_PROMPT_VERSION}.md"
)

# Prompt body extraction: el archivo MD tiene el prompt dentro de un fence
# ```...``` marcado "El prompt (cuerpo a enviar a Gemma 3:12b)". Extraemos ese fence.
_PROMPT_FENCE_RE = re.compile(
    r"## El prompt \(cuerpo a enviar a Gemma 3:12b\)\s*\n```\s*\n([\s\S]+?)\n```",
    re.MULTILINE,
)

# Targets de humanización por perfil §1.5 (de UMBRALES-OPERATIVOS-S4.md)
_HUMANIZ_TARGETS = {
    "politico_activo": "45-65 (action <35)",
    "funcionario_gobierno": "25-45 (action <15 o >55)",
    "figura_precampaña": "50-70 (action <40)",
    "empresario_transicion": "35-55 (action <25 o >65)",
}


def _load_prompt_body() -> str:
    """Carga el cuerpo del prompt del archivo versionable D-24.

    Raises:
        FileNotFoundError si el archivo no existe.
        ValueError si el fence no se encuentra.
    """
    text = _PROMPT_PATH.read_text(encoding="utf-8")
    m = _PROMPT_FENCE_RE.search(text)
    if not m:
        raise ValueError(
            f"Fence de prompt no encontrado en {_PROMPT_PATH}. "
            "Revisa que el archivo tenga la sección '## El prompt (cuerpo...)' "
            "con bloque ``` ... ```."
        )
    return m.group(1).strip()


def _classify_perfil_1_5(dirigente: Dirigente) -> str:
    """Heurística S4 (S5 añadirá columna explícita perfil_1_5).

    Basada en cargo actual. Regla conservadora:
    - contiene 'Secretari' / 'Director' / 'Ejecutivo' / 'Subsecretari' → funcionario_gobierno
    - contiene 'candidat' / 'aspirant' → figura_precampaña
    - contiene 'Diputad' / 'Senador' / 'Coordinador' / 'Presidente' / 'Alcald' → politico_activo
    - default → politico_activo
    """
    cargo = (dirigente.cargo or "").lower()
    if any(k in cargo for k in ("secretari", "director", "ejecutivo", "subsecretari")):
        return "funcionario_gobierno"
    if any(k in cargo for k in ("candidat", "aspirant", "precampa")):
        return "figura_precampaña"
    if any(k in cargo for k in ("diputad", "senador", "coordinador", "presidente", "alcald")):
        return "politico_activo"
    return "politico_activo"


def _compact_bloque(raw: dict) -> dict:
    """Reduce un bloque del diagnóstico a KPIs escalares esenciales.

    Gemma 3:12b en M4 16GB rinde lentamente; prompt >13k chars supera 450s.
    Solo preservamos scalars (int/float/bool/str corto) en el primer nivel y
    primer nivel de dicts anidados. Listas se resumen por conteo.
    """
    status = raw.get("status")
    if status != "ok":
        return {"status": status}
    data = raw.get("data") or {}
    compact: dict = {}
    for k, v in data.items():
        if isinstance(v, int | float | bool):
            compact[k] = v
        elif isinstance(v, str) and len(v) < 100:
            compact[k] = v
        elif isinstance(v, list):
            compact[k] = f"list[{len(v)}]"
        elif isinstance(v, dict):
            inner = {
                kk: vv
                for kk, vv in v.items()
                if isinstance(vv, int | float | bool)
                or (isinstance(vv, str) and len(vv) < 60)
            }
            if inner:
                compact[k] = dict(list(inner.items())[:8])
    return {"status": "ok", "data": compact}


async def _load_diagnostico_18_bloques(
    db: AsyncSession, dirigente_id: int, org_id: int
) -> dict[str, dict]:
    """Carga los 18 bloques del diagnóstico llamando a los servicios existentes.

    Los servicios Tier 2 de filtro_realidad y otros dependen de cib_detector;
    se ejecuta cib_result primero para compartirlo.
    """
    cib_result = await cib_detector_service.compute(db, dirigente_id, org_id)
    filtro = await filtro_realidad_service.compute(
        db, dirigente_id, org_id, cib_result=cib_result
    )

    bloques = {
        "B01_er_normalizado": await er_service.compute(db, dirigente_id, org_id),
        "B02_breakout_scale": await breakout_service.compute(db, dirigente_id, org_id),
        "B03_matriz_2x2": await matrix_2x2_service.compute(db, dirigente_id, org_id),
        "B04_benchmark": await benchmark_service.compute(db, dirigente_id, org_id),
        "B05_sentiment_plutchik": await sentiment_plutchik_service.compute(
            db, dirigente_id, org_id
        ),
        "B06_crisis_spike": await crisis_spike_service.compute(db, dirigente_id, org_id),
        "B07_growth_attribution": await growth_attribution_service.compute(
            db, dirigente_id, org_id
        ),
        "B08_sov": await sov_service.compute(db, dirigente_id, org_id),
        "B09_share_like_ratio": await share_like_ratio_service.compute(
            db, dirigente_id, org_id
        ),
        "B10_humanizacion": await humanizacion_service.compute(db, dirigente_id, org_id),
        "B11_cross_partisan": await cross_partisan_service.compute(
            db, dirigente_id, org_id
        ),
        "B12_cib_detector": cib_result,
        "B13_filtro_realidad": filtro,
        "B14_topic_drift": await topic_drift_service.compute(db, dirigente_id, org_id),
        "B15_rage_click": await rage_click_service.compute(db, dirigente_id, org_id),
        "B16_promesas": await promesas_service.compute(db, dirigente_id, org_id),
        "B17_veda_compliance": await veda_compliance_service.compute(
            db, dirigente_id, org_id, en_veda=settings.VEDA_ELECTORAL_ACTIVE
        ),
        "B18_violencia_politica": await violencia_politica_service.compute(
            db, dirigente_id, org_id
        ),
    }
    return bloques


def _extract_delta_b13(
    b13: dict[str, Any], b01: dict[str, Any]
) -> tuple[str, str, str]:
    """Extrae los 3 valores del bloque 4 del prompt de forma defensiva.

    Returns:
        (er_baseline_pct_str, er_organico_pct_str, delta_pct_str)
    """
    if b13.get("status") != "ok":
        return ("insufficient_data", "insufficient_data", "N/A")

    data = b13.get("data") or {}
    er_total = data.get("er_total_comments") or 0
    er_organico = data.get("er_organico_comments") or 0
    delta_pct = data.get("pct_comments_flagged")

    # Proxy de ER baseline desde B01 si existe
    b01_data = (b01 or {}).get("data") or {}
    er_baseline = (
        b01_data.get("er_pct")
        or b01_data.get("er_normalizado_pct")
        or b01_data.get("er_dirigente_pct")
    )
    er_baseline_str = f"{er_baseline:.2f}" if isinstance(er_baseline, int | float) else "n/a"

    # ER orgánico como pct de comments que sobreviven al filtro sobre total
    if er_total > 0:
        er_organico_pct = (er_organico / er_total) * 100
        er_organico_str = f"{er_organico_pct:.2f}"
    else:
        er_organico_str = "n/a"

    delta_str = f"{delta_pct:.2f}" if isinstance(delta_pct, int | float) else "N/A"
    return (er_baseline_str, er_organico_str, delta_str)


def _render_prompt(
    body: str,
    *,
    dirigente: Dirigente,
    bloques: dict[str, dict],
    historico_json: str,
    perfil_1_5: str,
    retry_feedback: str = "",
) -> str:
    """Sustituye tokens `{{VARIABLE}}` en el cuerpo del prompt."""
    # Seguro: followers total desde data_fidelity_tier / default 0
    # El modelo Dirigente no expone followers agregado directo — podríamos
    # hacer una query pero es costosa; para S4 enviamos 'unknown' si no hay
    # (el LLM tolera valor desconocido).
    followers = "unknown"

    b13 = bloques.get("B13_filtro_realidad") or {}
    b01 = bloques.get("B01_er_normalizado") or {}
    er_baseline, er_organico, delta = _extract_delta_b13(b13, b01)

    b10_data = (bloques.get("B10_humanizacion") or {}).get("data") or {}
    humaniz_score = b10_data.get("score")
    humaniz_score_str = (
        f"{humaniz_score:.2f}" if isinstance(humaniz_score, int | float) else "insufficient_data"
    )
    humaniz_target = _HUMANIZ_TARGETS.get(perfil_1_5, "n/a")

    data_fidelity_json = json.dumps(dirigente.data_fidelity_tier or {}, ensure_ascii=False)
    competidor_ids_json = json.dumps(
        list(dirigente.competidor_directo_ids or []), ensure_ascii=False
    )
    bloques_compactos = {k: _compact_bloque(v) for k, v in bloques.items()}
    bloques_json = json.dumps(bloques_compactos, ensure_ascii=False, default=str)

    replacements = {
        "{{DIRIGENTE_FULL_NAME}}": dirigente.full_name or "",
        "{{DIRIGENTE_CARGO}}": dirigente.cargo or "",
        "{{ESTRATO}}": dirigente.estrato_politico or "unknown",
        "{{FOLLOWERS_TOTAL}}": str(followers),
        "{{DATA_FIDELITY_TIER_JSON}}": data_fidelity_json,
        "{{PERFIL_1_5}}": perfil_1_5,
        "{{VEDA_ACTIVE}}": str(bool(settings.VEDA_ELECTORAL_ACTIVE)).lower(),
        "{{COMPETIDOR_IDS}}": competidor_ids_json,
        "{{DIAGNOSTICO_18_BLOQUES_JSON}}": bloques_json,
        "{{DELTA_B13_PCT}}": delta,
        "{{ER_ORGANICO_PCT}}": er_organico,
        "{{ER_BASELINE_PCT}}": er_baseline,
        "{{HISTORICO_RAG_JSON}}": historico_json,
        "{{HUMANIZACION_SCORE}}": humaniz_score_str,
        "{{HUMANIZACION_TARGET}}": humaniz_target,
        "{{RETRY_FEEDBACK}}": retry_feedback or "(sin retries previos — primer intento)",
    }

    rendered = body
    for token, value in replacements.items():
        rendered = rendered.replace(token, value)
    return rendered


def _parse_llm_json(raw_text: str) -> dict[str, Any] | None:
    """Parse robusto del output JSON del LLM.

    Intenta:
    1. JSON directo.
    2. Extraer primer bloque entre ```...``` si el modelo añade fence.
    3. Extraer el primer objeto `{...}` balanceado.
    """
    cleaned = (raw_text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Buscar el primer objeto JSON top-level balanceado
    depth = 0
    start = None
    for i, ch in enumerate(cleaned):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                candidate = cleaned[start : i + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    start = None
                    continue
    return None


class PlanIAPipeline:
    """Orquestador del pipeline Plan IA — T1..T4 Sprint S4."""

    def __init__(
        self,
        *,
        ollama_base_url: str | None = None,
        model: str = "gemma3:12b",
        claude_model: str | None = None,
        temperature: float = 0.2,
        seed: int = 42,
        num_predict: int = 2000,
        max_tokens: int = 8192,
        timeout_s: float = 600.0,
        max_retries: int = 1,
    ) -> None:
        self.ollama_base_url = (ollama_base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model
        self.claude_model = claude_model or settings.CLAUDE_MODEL
        self.temperature = temperature
        self.seed = seed
        self.num_predict = num_predict
        self.max_tokens = max_tokens
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self.validator = AntiVanityValidator()
        # Provider selection: Claude by default. Ollama only when explicitly
        # enabled (the ~8GB gemma3:12b model OOMs the shared VPS — see
        # OLLAMA_ENABLED). This pipeline was migrated to Claude.
        self.provider = (
            "ollama"
            if settings.AI_PROVIDER == "ollama" and settings.OLLAMA_ENABLED
            else "claude"
        )
        self.active_model = self.model if self.provider == "ollama" else self.claude_model

    def _call_ollama_sync(self, prompt: str) -> str:
        """Sync HTTP call a Ollama. Se envuelve vía anyio.to_thread.

        Sincrónico porque async httpx a host.docker.internal en Docker Desktop
        macOS se cuelga silenciosamente en payloads grandes (Sprint S4
        empírico 2026-04-19). Sync httpx en 16-460s según prompt.
        """
        if not settings.OLLAMA_ENABLED:
            raise RuntimeError(
                "Ollama deshabilitado (OLLAMA_ENABLED=false); el pipeline Plan IA "
                "requiere migración a Claude antes de reactivarse."
            )
        endpoint = f"{self.ollama_base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.temperature,
                "seed": self.seed,
                "num_predict": self.num_predict,
                "num_ctx": 16384,
            },
        }
        with httpx.Client(timeout=self.timeout_s) as client:
            resp = client.post(endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return str(data.get("response") or "")

    async def _call_ollama(self, prompt: str) -> str:
        """Async wrapper sobre sync call; no bloquea event loop."""
        from anyio import to_thread

        return await to_thread.run_sync(self._call_ollama_sync, prompt)

    def _call_claude_sync(self, prompt: str) -> str:
        """Sync Claude call que devuelve el texto JSON crudo.

        Envuelto en anyio.to_thread igual que el path Ollama para no bloquear
        el event loop del worker. Usa prefill '{' para forzar que la respuesta
        sea un objeto JSON (mismo patrón probado en plan_structured).
        """
        import anthropic

        if not settings.CLAUDE_API_KEY:
            raise RuntimeError(
                "CLAUDE_API_KEY no configurada; el pipeline Plan IA requiere Claude."
            )
        client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY, timeout=self.timeout_s)
        message = client.messages.create(
            model=self.claude_model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=(
                "Eres un estratega de comunicación política. Devuelve EXCLUSIVAMENTE "
                "un objeto JSON válido con la clave 'recomendaciones' (array). Nada de "
                "texto adicional, markdown ni fences."
            ),
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "{"},  # prefill JSON opening
            ],
        )
        return "{" + message.content[0].text

    async def _call_claude(self, prompt: str) -> str:
        """Async wrapper sobre la llamada sync a Claude."""
        from anyio import to_thread

        return await to_thread.run_sync(self._call_claude_sync, prompt)

    async def _call_llm(self, prompt: str) -> str:
        """Dispatch a Claude (default) u Ollama según el provider activo."""
        if self.provider == "ollama":
            return await self._call_ollama(prompt)
        return await self._call_claude(prompt)

    async def _generate_and_validate(
        self,
        *,
        dirigente: Dirigente,
        bloques: dict,
        historico_json: str,
        perfil_1_5: str,
        prompt_body: str,
    ) -> tuple[list[dict], list[dict], str]:
        """Run generate → parse → validate loop with retries.

        Returns:
            (valid_recomendaciones, rejected_with_reasons, last_raw_response)
        """
        feedback = ""
        last_raw = ""
        last_rejected: list[dict] = []
        for attempt in range(1, self.max_retries + 2):  # 1 initial + max_retries
            rendered = _render_prompt(
                prompt_body,
                dirigente=dirigente,
                bloques=bloques,
                historico_json=historico_json,
                perfil_1_5=perfil_1_5,
                retry_feedback=feedback,
            )
            logger.info(
                "PlanIA attempt=%d dirigente_id=%d prompt_chars=%d",
                attempt,
                dirigente.id,
                len(rendered),
            )
            try:
                last_raw = await self._call_llm(rendered)
            except Exception as e:  # noqa: BLE001 — resiliencia LLM (Claude/Ollama)
                logger.error(
                    "PlanIA %s LLM fail attempt=%d: %s", self.provider, attempt, e
                )
                continue

            parsed = _parse_llm_json(last_raw)
            if not isinstance(parsed, dict):
                logger.warning(
                    "PlanIA parse fail attempt=%d raw_head=%r",
                    attempt,
                    (last_raw or "")[:200],
                )
                feedback = (
                    "El intento anterior no devolvió JSON válido. Devuelve "
                    "EXCLUSIVAMENTE un objeto JSON con la clave 'recomendaciones'."
                )
                continue

            recs = parsed.get("recomendaciones")
            if not isinstance(recs, list) or not recs:
                feedback = (
                    "Faltó la clave 'recomendaciones' o estaba vacía. Genera "
                    "entre 3 y 5 recomendaciones dentro del array 'recomendaciones'."
                )
                continue

            valid, rejected = self.validator.validate_batch(recs)
            last_rejected = rejected
            logger.info(
                "PlanIA attempt=%d valid=%d rejected=%d",
                attempt,
                len(valid),
                len(rejected),
            )
            if valid and not rejected:
                return (valid, rejected, last_raw)
            if valid and rejected and attempt == self.max_retries + 1:
                # Último intento: devolver lo válido aunque haya algunos rechazos
                return (valid, rejected, last_raw)

            feedback = self.validator.feedback_for_retry(rejected)

        return ([], last_rejected, last_raw)

    async def generate(
        self,
        db: AsyncSession,
        dirigente_id: int,
        org_id: int,
    ) -> dict[str, Any]:
        """Genera recomendaciones para un dirigente y persiste las válidas.

        Returns:
            {
              "pipeline": {"attempts": int, "parse_rate": float, ...},
              "recomendaciones_creadas": [{"id":..., "tipo":..., "accion_texto":...}],
              "rechazadas": [...]
            }
        """
        start = datetime.now(UTC)

        dirigente = await db.get(Dirigente, dirigente_id)
        if dirigente is None:
            return {
                "error": f"dirigente {dirigente_id} no existe",
                "recomendaciones_creadas": [],
                "rechazadas": [],
            }

        if dirigente.org_id is not None and dirigente.org_id != org_id:
            return {
                "error": f"cross-tenant: dirigente pertenece a org {dirigente.org_id}, no {org_id}",
                "recomendaciones_creadas": [],
                "rechazadas": [],
            }

        perfil_1_5 = _classify_perfil_1_5(dirigente)

        # Paralelización posible; secuencial para simplicidad S4
        bloques = await _load_diagnostico_18_bloques(db, dirigente_id, org_id)
        historico = await fetch_historico(db, dirigente_id, org_id, limit=10)
        historico_json = format_historico_for_prompt(historico)

        prompt_body = _load_prompt_body()

        valid, rejected, last_raw = await self._generate_and_validate(
            dirigente=dirigente,
            bloques=bloques,
            historico_json=historico_json,
            perfil_1_5=perfil_1_5,
            prompt_body=prompt_body,
        )

        # Persistencia
        created_ids: list[dict[str, Any]] = []
        for rec in valid:
            now = datetime.now(UTC)
            ventana_dias = int(rec.get("ventana_duracion_dias") or 14)
            row = RecomendacionPlanIA(
                plan_ia_id=None,
                dirigente_id=dirigente_id,
                org_id=org_id,
                tipo=rec.get("tipo", "start"),
                accion_texto=(rec.get("accion_texto") or "").strip(),
                ventana_inicio=now,
                ventana_fin=now + timedelta(days=ventana_dias),
                ventana_duracion_dias=ventana_dias,
                criterio_exito=rec.get("criterio_exito") or {},
                principio_conductual=(rec.get("principio_conductual") or None),
                evidencia_respaldo=rec.get("evidencia_respaldo") or {},
                estado="propuesta",
                created_at=now,
                updated_at=now,
            )
            db.add(row)
            await db.flush()
            created_ids.append(
                {
                    "id": row.id,
                    "tipo": row.tipo,
                    "accion_texto": row.accion_texto[:200],
                    "principio_conductual": row.principio_conductual,
                    "bloques_citados": (row.evidencia_respaldo or {}).get(
                        "bloques_citados", []
                    ),
                }
            )

        await db.commit()

        elapsed = (datetime.now(UTC) - start).total_seconds()
        logger.info(
            "PlanIA dirigente_id=%d done elapsed=%.2fs valid=%d rejected=%d",
            dirigente_id,
            elapsed,
            len(valid),
            len(rejected),
        )

        return {
            "pipeline": {
                "elapsed_s": round(elapsed, 2),
                "valid_count": len(valid),
                "rejected_count": len(rejected),
                "parse_rate": round(
                    len(valid) / max(len(valid) + len(rejected), 1), 3
                ),
                "delta_b13_pct": _extract_delta_b13(
                    bloques.get("B13_filtro_realidad") or {},
                    bloques.get("B01_er_normalizado") or {},
                )[2],
                "perfil_1_5": perfil_1_5,
                "prompt_version": _PROMPT_VERSION,
                "provider": self.provider,
                "model": self.active_model,
            },
            "recomendaciones_creadas": created_ids,
            "rechazadas": rejected,
            "raw_tail": (last_raw or "")[-500:],
        }


# Singleton conveniente — opcional
default_pipeline = PlanIAPipeline()


async def generate_for_dirigente(
    db: AsyncSession, dirigente_id: int, org_id: int
) -> dict[str, Any]:
    """Functional facade for the default pipeline instance."""
    return await default_pipeline.generate(db, dirigente_id, org_id)
