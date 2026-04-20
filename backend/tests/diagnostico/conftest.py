"""Fixtures compartidas para tests de diagnóstico Tier 1 (Sprint S2)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente, DirigenteSyncStatus
from app.models.organizacion import Organizacion
from app.models.social import (
    DataSource,
    Platform,
    PostType,
    SentimentAnalysis,
    SocialPost,
    SocialProfile,
    SocialProfileSnapshot,
)


@pytest.fixture
async def org_fixture(db_session: AsyncSession) -> Organizacion:
    org = Organizacion(
        nombre="Org Test Diagnóstico",
        slug="org-diag-test",
        partido="MC",
        estado="CDMX",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def dirigente_with_data(
    db_session: AsyncSession, org_fixture: Organizacion
) -> Dirigente:
    """Dirigente tipo Piña con 1 profile TWITTER + 12 posts variados."""
    d = Dirigente(
        full_name="Test Dirigente Alfa",
        cargo="Diputado Local",
        partido="MC",
        estado="CDMX",
        org_id=org_fixture.id,
        estrato_politico="Nano",
        sync_status=DirigenteSyncStatus.READY,
    )
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)

    profile = SocialProfile(
        dirigente_id=d.id,
        platform=Platform.TWITTER,
        handle="@alfa_test",
        followers_count=3100,
        data_source=DataSource.AUTOMATED_SCRAPER,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    now = datetime.now(UTC)
    for i in range(12):
        published = now - timedelta(days=i * 3)
        likes = 100 + i * 10
        post = SocialPost(
            profile_id=profile.id,
            platform_post_id=f"t_alfa_{i}",
            content=f"Hola familia de mi colonia, gracias por su apoyo. Post {i}",
            post_type=PostType.TEXT,
            published_at=published,
            likes=likes,
            comments=20 + i,
            shares=5 + i,
            views=5000 + i * 100,
            engagement_rate=(likes + 20 + 5) / 3100,
            sentiment_score=0.2 - (i * 0.05),  # pendiente de positivo a negativo
            emotions={"trust": 0.4 - i * 0.02, "anger": 0.1 + i * 0.01, "joy": 0.2,
                      "fear": 0.05, "sadness": 0.1, "disgust": 0.05},
            topics_extracted={"topics": ["seguridad", "economia"] if i % 2 == 0 else ["salud"]},
        )
        db_session.add(post)

    # 2 snapshots para B07
    db_session.add(
        SocialProfileSnapshot(
            profile_id=profile.id,
            dirigente_id=d.id,
            org_id=org_fixture.id,
            platform=Platform.TWITTER,
            followers_count=3050,
            posts_count=50,
            taken_at=now - timedelta(days=13),
        )
    )
    db_session.add(
        SocialProfileSnapshot(
            profile_id=profile.id,
            dirigente_id=d.id,
            org_id=org_fixture.id,
            platform=Platform.TWITTER,
            followers_count=3100,
            posts_count=62,
            taken_at=now - timedelta(hours=6),
        )
    )

    await db_session.commit()
    await db_session.refresh(d)
    return d


@pytest.fixture
async def dirigente_sin_posts(
    db_session: AsyncSession, org_fixture: Organizacion
) -> Dirigente:
    """Dirigente sin profiles — para probar insufficient_data paths."""
    d = Dirigente(
        full_name="Test Dirigente Beta Sin Data",
        cargo="Regidor",
        partido="MC",
        estado="Oaxaca",
        org_id=org_fixture.id,
        sync_status=DirigenteSyncStatus.PENDING,
    )
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)
    return d
