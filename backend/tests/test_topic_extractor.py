"""Tests Sprint S1 T5 — TopicExtractor + endpoint /posts/{id}/topics.

Dos niveles:
1. Unit: mock del POST a Ollama → valida parsing, normalización, fallbacks.
2. Integration HTTP: fixture dirigente + post con topics_extracted ya poblado →
   llama al endpoint real y valida el shape de la respuesta.

No hacemos test live contra Gemma dentro de pytest (la verificación empírica
vive en `scripts/run_topic_extraction.py` ejecutado manualmente por el CEO,
según regla MD "un commit por funcionalidad verificada").
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente
from app.models.social import (
    Platform,
    PostType,
    SocialPost,
    SocialProfile,
)
from app.nlp.topic_extractor import EMOTION_SEED, TOPIC_SEED, TopicExtractor
from tests.conftest import auth_headers


# ---------------------------------------------------------------------------
# Unit tests — TopicExtractor con Ollama mockeado
# ---------------------------------------------------------------------------


def _fake_ollama_response(raw_text: str) -> MagicMock:
    """Construye una respuesta fake httpx con el `response` de Ollama."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock(return_value=None)
    resp.json = MagicMock(return_value={"response": raw_text, "done": True})
    return resp


@pytest.mark.asyncio
async def test_extract_happy_path_returns_normalized_shape() -> None:
    """Mock de Gemma devolviendo JSON perfecto → shape normalizado."""
    extractor = TopicExtractor(base_url="http://fake-ollama:11434")
    raw = '{"emocion": "anger", "topics": ["corrupcion", "gobierno"]}'

    fake_post = AsyncMock(return_value=_fake_ollama_response(raw))
    with patch("httpx.AsyncClient.post", fake_post):
        out = await extractor.extract(
            text="El gobierno es una vergüenza total, corruptos todos.",
            plataforma="TWITTER",
        )

    assert out["emocion"] == "anger"
    assert out["topics"] == ["corrupcion", "gobierno"]
    assert out["model"] == "gemma3:12b"
    assert "extracted_at" in out
    # extracted_at debe ser ISO-8601 parseable
    datetime.fromisoformat(out["extracted_at"])
    assert "_err" not in out


@pytest.mark.asyncio
async def test_extract_strips_markdown_fences_and_preamble() -> None:
    """Gemma a veces envuelve en ```json ... ``` con texto antes."""
    extractor = TopicExtractor(base_url="http://fake-ollama:11434")
    raw = (
        "Aquí está el resultado:\n"
        "```json\n"
        '{"emocion": "joy", "topics": ["educacion"]}\n'
        "```"
    )
    fake_post = AsyncMock(return_value=_fake_ollama_response(raw))
    with patch("httpx.AsyncClient.post", fake_post):
        out = await extractor.extract(text="Felicitaciones maestros!", plataforma="INSTAGRAM")
    assert out["emocion"] == "joy"
    assert out["topics"] == ["educacion"]


@pytest.mark.asyncio
async def test_extract_filters_topics_outside_seed() -> None:
    """Si Gemma inventa un topic fuera del seed fijo, debe filtrarlo."""
    extractor = TopicExtractor(base_url="http://fake-ollama:11434")
    raw = '{"emocion": "trust", "topics": ["futbol", "salud", "hackeo_bancario"]}'
    fake_post = AsyncMock(return_value=_fake_ollama_response(raw))
    with patch("httpx.AsyncClient.post", fake_post):
        out = await extractor.extract(text="algo", plataforma="FACEBOOK")
    # "futbol" y "hackeo_bancario" no están en TOPIC_SEED → deben desaparecer
    assert out["topics"] == ["salud"]
    for t in out["topics"]:
        assert t in TOPIC_SEED


@pytest.mark.asyncio
async def test_extract_invalid_emotion_becomes_none() -> None:
    """Emoción fuera de Plutchik-6 → None (no inventamos)."""
    extractor = TopicExtractor(base_url="http://fake-ollama:11434")
    raw = '{"emocion": "confusion", "topics": ["otro"]}'
    fake_post = AsyncMock(return_value=_fake_ollama_response(raw))
    with patch("httpx.AsyncClient.post", fake_post):
        out = await extractor.extract(text="raro", plataforma="TWITTER")
    assert out["emocion"] is None
    assert out["topics"] == ["otro"]


@pytest.mark.asyncio
async def test_extract_json_parse_failure_returns_fallback() -> None:
    """Si el output NO es JSON válido, retornar fallback con _err."""
    extractor = TopicExtractor(base_url="http://fake-ollama:11434")
    raw = "No puedo clasificar este comentario, lo siento."
    fake_post = AsyncMock(return_value=_fake_ollama_response(raw))
    with patch("httpx.AsyncClient.post", fake_post):
        out = await extractor.extract(text="hola", plataforma="TWITTER")
    assert out["emocion"] is None
    assert out["topics"] == ["otro"]
    assert "_err" in out
    assert out["_err"] == "json_parse_failed"


@pytest.mark.asyncio
async def test_extract_empty_text_short_circuit() -> None:
    """Texto vacío → no llamar a Ollama, fallback inmediato."""
    extractor = TopicExtractor(base_url="http://fake-ollama:11434")
    fake_post = AsyncMock()
    with patch("httpx.AsyncClient.post", fake_post):
        out = await extractor.extract(text="   ", plataforma="TWITTER")
    fake_post.assert_not_called()
    assert out["_err"] == "empty_text"
    assert out["topics"] == ["otro"]


def test_seed_invariants() -> None:
    """Garantías de diseño: 12 topics, 6 emociones, 'otro' siempre presente."""
    assert len(TOPIC_SEED) == 12
    assert len(EMOTION_SEED) == 6
    assert "otro" in TOPIC_SEED


# ---------------------------------------------------------------------------
# Integration test — endpoint /api/v1/posts/{id}/topics con DB real
# ---------------------------------------------------------------------------


async def _seed_post_with_topics(
    db: AsyncSession,
    *,
    org_id: int | None = None,
    with_topics: bool = True,
) -> tuple[Dirigente, SocialProfile, SocialPost]:
    dirigente = Dirigente(
        full_name="T5 Test Dirigente",
        cargo="Diputada",
        partido="MC",
        estado="CDMX",
        org_id=org_id,
    )
    db.add(dirigente)
    await db.flush()

    profile = SocialProfile(
        dirigente_id=dirigente.id,
        platform=Platform.TWITTER,
        handle="@t5_test",
        followers_count=1000,
        posts_count=1,
    )
    db.add(profile)
    await db.flush()

    topics_payload = None
    if with_topics:
        topics_payload = {
            "emocion": "anger",
            "topics": ["corrupcion", "gobierno"],
            "model": "gemma3:12b",
            "extracted_at": datetime.now(UTC).isoformat(),
        }

    post = SocialPost(
        profile_id=profile.id,
        platform_post_id=f"t5_test_post_{dirigente.id}",
        content="Contenido de prueba T5.",
        post_type=PostType.TEXT,
        published_at=datetime.now(UTC),
        likes=10,
        comments=2,
        shares=1,
        views=100,
        engagement_rate=0.01,
        is_political=True,
        topics_extracted=topics_payload,
    )
    db.add(post)
    await db.flush()
    await db.refresh(post)
    return dirigente, profile, post


@pytest.mark.asyncio
async def test_get_post_topics_endpoint_returns_persisted_payload(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
) -> None:
    """Endpoint real: post con topics poblados → 200 + shape correcto."""
    _, _, post = await _seed_post_with_topics(db_session, with_topics=True)
    await db_session.commit()

    r = await client.get(
        f"/api/v1/posts/{post.id}/topics",
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["post_id"] == post.id
    assert body["platform"] == "TWITTER"
    assert body["has_extraction"] is True
    te = body["topics_extracted"]
    assert te["emocion"] == "anger"
    assert te["topics"] == ["corrupcion", "gobierno"]
    assert te["model"] == "gemma3:12b"


@pytest.mark.asyncio
async def test_get_post_topics_endpoint_handles_missing_extraction(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
) -> None:
    """Post sin topics_extracted → 200 con has_extraction=false."""
    _, _, post = await _seed_post_with_topics(db_session, with_topics=False)
    await db_session.commit()

    r = await client.get(
        f"/api/v1/posts/{post.id}/topics",
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["post_id"] == post.id
    assert body["topics_extracted"] is None
    assert body["has_extraction"] is False


@pytest.mark.asyncio
async def test_get_post_topics_endpoint_404_on_missing_post(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
) -> None:
    r = await client.get(
        "/api/v1/posts/9999999/topics",
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 404
