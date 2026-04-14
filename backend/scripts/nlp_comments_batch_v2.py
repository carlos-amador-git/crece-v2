"""NLP comments batch v2 — usa matriz BD con contexto='comment_tercero'.

Diferencias vs v1:
 - Query matriz `framework_matrix_defaults` por (rol, tono, target, contexto)
 - Fallback a contexto='post_dirigente' si no hay match comment-specific
 - Incluye target='dirigente' (nuevo en v2) en detector keyword
 - nlp_model_version='comment-framework-v2'

Flujo:
 1. pysentimiento → sentiment
 2. Keyword detect → tono + target (sin LLM externo)
 3. JOIN dirigente.rol_politico via social_posts → social_profiles
 4. Lookup matriz → polaridad
 5. UPDATE social_comments

Pipeline MANUAL (sin LLM remoto) — costo $0.
"""
from __future__ import annotations

import asyncio
import re

from sqlalchemy import text

from app.core.database import async_session_factory
from app.nlp.analyzer import NLPAnalyzer


TONO_KEYWORDS = {
    "celebratorio": [r"\b(felicid|bravo|excelente|gracias|bien hecho|grande|genial|increíble|aplauso)\b"],
    "critico": [r"\b(pésimo|malo|horrible|decepcionante|fracaso|corrupto|mentira|fraude|chayotero|fracaso)\b"],
    "ataque": [r"\b(pendejo|idiota|estúpido|imbécil|rata|ladrón|lárgate|renuncia|basura|maldit)\b"],
    "propositivo": [r"\b(propongo|sugiero|sería mejor|podríamos|debería|hay que|propuesta|iniciativa)\b"],
    "solidario": [r"\b(apoyo|respaldo|estoy contigo|cuenta conmigo|animo|fuerza|contigo)\b"],
    "informativo": [r"\b(según|dato|fuente|cifra|estadística|porcentaje|reporte|informa)\b"],
    "personal": [r"\b(saludos|cariño|abrazo|jaja|jeje|😂|❤|🙏|linda|hermosa|guapa)\b"],
}

# Target detection — NOW includes 'dirigente' via @ mentions or 2nd person.
TARGET_KEYWORDS = {
    "dirigente": [
        r"\b(usted|tú|ti|contigo|su señoría|diputad[oa]|presidenta?|señor|señora)\b",
        r"@\w+",  # @ mention likely targets the dirigente
    ],
    "gobierno": [r"\b(gobierno|amlo|sheinbaum|morena|presidenta|4t|federal|régimen|régimen)\b"],
    "oposicion": [r"\b(pri|pan|mc movimiento|prd|oposición|derecha)\b"],
    "autopromocion": [r"\b(mi marca|mi canal|mi página|sígueme|suscrib|mi perfil)\b"],
    "ciudadania": [r"\b(pueblo|gente|mexicanos|ciudadan|vecinos|comunidad|ciudadanía)\b"],
    "medios": [r"\b(medios|prensa|periodist|noticia|reforma|milenio|televis|tv azteca)\b"],
    "tema_especifico": [r"\b(salud|educación|seguridad|inflación|impuestos|movilidad|agua|vivienda)\b"],
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
        return "dirigente"  # fallback: a comment without clear target is likely directed at post author
    return max(scores, key=scores.get)


async def load_matrix(session) -> dict:
    """Return nested dict: {contexto: {(rol, tono, target): score}}."""
    rows = (await session.execute(
        text("""
            SELECT contexto, rol, tono, target, score_politico
            FROM framework_matrix_defaults
            WHERE version='v1'
        """)
    )).fetchall()
    matrix: dict = {}
    for ctx, rol, tono, target, score in rows:
        matrix.setdefault(ctx, {})[(rol, tono, target)] = score
    return matrix


def lookup_polaridad(matrix: dict, rol: str, tono: str, target: str) -> int:
    """Look up matrix with comment→post fallback."""
    comment_rules = matrix.get("comment_tercero", {})
    post_rules = matrix.get("post_dirigente", {})
    key = (rol, tono, target)
    if key in comment_rules:
        return comment_rules[key]
    if key in post_rules:
        return post_rules[key]
    return 0


async def main(limit: int = 2000, batch_size: int = 100):
    analyzer = NLPAnalyzer()
    async with async_session_factory() as session:
        matrix = await load_matrix(session)
        print(f"Loaded matrix: {sum(len(v) for v in matrix.values())} rules in {list(matrix.keys())}")

        pending = (await session.execute(
            text("""
                SELECT sc.id, sc.content, COALESCE(d.rol_politico, 'independiente') as rol
                FROM social_comments sc
                JOIN social_posts sp ON sp.id = sc.parent_post_id
                JOIN social_profiles p ON p.id = sp.profile_id
                JOIN dirigentes d ON d.id = p.dirigente_id
                WHERE sc.nlp_model_version IS NULL
                   OR sc.nlp_model_version = 'comment-framework-v1'
                LIMIT :limit
            """),
            {"limit": limit},
        )).fetchall()

    print(f"Pendientes: {len(pending)}")
    if not pending:
        return

    import concurrent.futures
    loop = asyncio.get_event_loop()

    def score_one(cid: int, content: str, rol: str) -> tuple[int, str, str, int]:
        sent = analyzer.analyze(content or "")
        label = sent.sentiment_label or "neutral"
        tono = detect_tono(content or "")
        target = detect_target(content or "")
        pol = lookup_polaridad(matrix, rol, tono, target)
        # Refine: if sentiment is strong negative and tono is personal, prefer critico
        if label in {"NEG", "negative"} and tono == "personal":
            tono = "critico"
            pol = lookup_polaridad(matrix, rol, tono, target)
        return (cid, tono, target, pol)

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        futs = [loop.run_in_executor(ex, score_one, row[0], row[1], row[2]) for row in pending]
        for i, f in enumerate(await asyncio.gather(*futs)):
            results.append(f)
            if (i + 1) % 100 == 0:
                print(f"  scored {i+1}/{len(pending)}")

    async with async_session_factory() as session:
        for cid, tono, target, pol in results:
            await session.execute(
                text("""
                    UPDATE social_comments
                    SET nlp_tono = :tono,
                        nlp_target = :target,
                        nlp_polaridad = :pol,
                        nlp_model_version = 'comment-framework-v2'
                    WHERE id = :id
                """),
                {"tono": tono, "target": target, "pol": pol, "id": cid},
            )
        await session.commit()

    print(f"\n✅ {len(results)} comments analizados con matriz v2 (contexto=comment_tercero + fallback post_dirigente)")


if __name__ == "__main__":
    asyncio.run(main())
