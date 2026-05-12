"""Aplica framework político a comments pendientes.

Flujo: para cada comment sin nlp_model_version:
 1) pysentimiento sentiment + polaridad
 2) reglas ligeras para tono/target (sin LLM externo → costo $0)
 3) score agregado: +1 positivo/aprobación, 0 neutral, -1 rechazo
"""
from __future__ import annotations

import asyncio
import re
from typing import Optional

from sqlalchemy import text

from app.core.database import async_session_factory
from app.nlp.analyzer import NLPAnalyzer


TONO_KEYWORDS = {
    "celebratorio": [r"\b(felicid|bravo|excelente|gracias|bien hecho|grande)\b"],
    "critico": [r"\b(pésimo|malo|horrible|decepcionante|fracaso|corrupto|mentira|fraude)\b"],
    "ataque": [r"\b(pendejo|idiota|estúpido|imbécil|rata|ladrón|lárgate|renuncia)\b"],
    "propositivo": [r"\b(propongo|sugiero|sería mejor|podríamos|debería|hay que)\b"],
    "solidario": [r"\b(apoyo|respaldo|estoy contigo|cuenta conmigo|animo)\b"],
    "informativo": [r"\b(según|dato|fuente|cifra|estadística|porcentaje)\b"],
    "personal": [r"\b(saludos|cariño|abrazo|jaja|jeje|😂|❤|🙏)\b"],
}

TARGET_KEYWORDS = {
    "gobierno": [r"\b(gobierno|amlo|sheinbaum|morena|presidenta|4t|federal)\b"],
    "oposicion": [r"\b(pri|pan|mc|prd|oposición|derecha)\b"],
    "autopromocion": [r"\b(yo|mi|conmigo|sígueme|suscrib)\b"],
    "ciudadania": [r"\b(pueblo|gente|mexicanos|ciudadan|vecinos|comunidad)\b"],
    "medios": [r"\b(medios|prensa|periodist|noticia|reforma|milenio)\b"],
    "tema_especifico": [r"\b(salud|educación|seguridad|inflación|impuestos|movilidad)\b"],
}


def detect_tono(text_norm: str) -> str:
    scores: dict[str, int] = {}
    for tono, patterns in TONO_KEYWORDS.items():
        for p in patterns:
            if re.search(p, text_norm, re.IGNORECASE):
                scores[tono] = scores.get(tono, 0) + 1
    if not scores:
        return "personal"
    return max(scores, key=scores.get)


def detect_target(text_norm: str) -> str:
    scores: dict[str, int] = {}
    for target, patterns in TARGET_KEYWORDS.items():
        for p in patterns:
            if re.search(p, text_norm, re.IGNORECASE):
                scores[target] = scores.get(target, 0) + 1
    if not scores:
        return "autopromocion"
    return max(scores, key=scores.get)


def polaridad_from(sentiment_label: str, tono: str) -> int:
    """Mapea sentiment pysentimiento + tono a polaridad política -1/0/+1."""
    if tono == "ataque" or tono == "critico":
        if sentiment_label in {"NEG", "negative"}:
            return -1
        return 0
    if tono in {"solidario", "celebratorio"}:
        if sentiment_label in {"POS", "positive"}:
            return 1
        return 0
    if tono == "propositivo":
        return 0
    if sentiment_label in {"POS", "positive"}:
        return 1
    if sentiment_label in {"NEG", "negative"}:
        return -1
    return 0


async def main(limit: int = 500, batch_size: int = 50):
    analyzer = NLPAnalyzer()

    async with async_session_factory() as session:
        pending = (await session.execute(
            text("""
                SELECT id, content FROM social_comments
                WHERE nlp_model_version IS NULL
                LIMIT :limit
            """),
            {"limit": limit},
        )).fetchall()

    print(f"Pendientes: {len(pending)}")
    if not pending:
        return

    import concurrent.futures
    results = []
    # Run sync analyzer calls in thread pool (pysentimiento not async)
    loop = asyncio.get_event_loop()

    def score_one(cid: int, content: str) -> tuple[int, str, str, int]:
        sent = analyzer.analyze(content or "")
        label = sent.sentiment_label or "neutral"
        tono = detect_tono(content or "")
        target = detect_target(content or "")
        pol = polaridad_from(label, tono)
        return (cid, tono, target, pol)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futs = [loop.run_in_executor(ex, score_one, row[0], row[1]) for row in pending]
        for i, f in enumerate(await asyncio.gather(*futs)):
            results.append(f)
            if (i+1) % 50 == 0:
                print(f"  scored {i+1}/{len(pending)}")

    async with async_session_factory() as session:
        for cid, tono, target, pol in results:
            await session.execute(
                text("""
                    UPDATE social_comments
                    SET nlp_tono = :tono,
                        nlp_target = :target,
                        nlp_polaridad = :pol,
                        nlp_model_version = 'comment-framework-v1'
                    WHERE id = :id
                """),
                {"tono": tono, "target": target, "pol": pol, "id": cid},
            )
        await session.commit()

    print(f"\n✅ {len(results)} comments analizados")


if __name__ == "__main__":
    asyncio.run(main())
