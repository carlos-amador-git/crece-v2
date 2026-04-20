"""Fixtures compartidas para tests de diagnóstico Tier 2 (Sprint S3)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dirigente import Dirigente, DirigenteSyncStatus
from app.models.organizacion import Organizacion
from app.models.promesa_dirigente import PromesaDirigente, PromesaEstado
from app.models.social import (
    DataSource,
    Platform,
    PostType,
    SocialPost,
    SocialProfile,
)


@pytest.fixture
async def org_tier2(db_session: AsyncSession) -> Organizacion:
    org = Organizacion(
        nombre="Org Tier2 Test",
        slug="org-tier2-test",
        partido="MC",
        estado="CDMX",
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest.fixture
async def dirigente_tier2(
    db_session: AsyncSession, org_tier2: Organizacion
) -> Dirigente:
    """Dirigente con 1 profile + 6 posts + 30 comments (mezcla partidista)."""
    d = Dirigente(
        full_name="Test Dirigente Tier2",
        cargo="Regidor",
        partido="MC",
        estado="CDMX",
        org_id=org_tier2.id,
        estrato_politico="Nano",
        sync_status=DirigenteSyncStatus.READY,
    )
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)

    profile = SocialProfile(
        dirigente_id=d.id,
        platform=Platform.TWITTER,
        handle="@tier2_test",
        followers_count=2200,
        data_source=DataSource.AUTOMATED_SCRAPER,
    )
    db_session.add(profile)
    await db_session.commit()
    await db_session.refresh(profile)

    now = datetime.now(UTC)
    post_ids: list[int] = []
    contenidos = [
        "Movimiento Ciudadano propone seguridad barrio colonia vecinos",
        "Trabajando por mi colonia, gracias vecinos por su apoyo",
        "Rechazo categóricamente la corrupción y el abuso",
        "Agenda de seguridad publica con propuestas concretas",
        "Hola familia y vecinos, hoy inauguramos obra pública",
        "Propuesta electoral: voto a favor del candidato MC",
    ]
    for i, c in enumerate(contenidos):
        published = now - timedelta(days=i * 2)
        post = SocialPost(
            profile_id=profile.id,
            platform_post_id=f"t2_{i}",
            content=c,
            post_type=PostType.TEXT,
            published_at=published,
            likes=50 + i * 10,
            comments=8 + i,
            shares=3,
            views=2200 + i * 50,
            engagement_rate=0.03 + i * 0.005,
        )
        db_session.add(post)
        await db_session.commit()
        await db_session.refresh(post)
        post_ids.append(post.id)

    # 30 comments: 5 por post. Mezcla partidista + 2 rage + 1 amenaza + 1 VPG.
    comment_seed = [
        # post 0 — comments muy similares (coro_cluster)
        ("hash_AA01", "Apoyo total a Movimiento Ciudadano y la naranja", None, None),
        ("hash_AA02", "Apoyo total a Movimiento Ciudadano y la naranja", None, None),
        ("hash_BB01", "Morena y la 4T son el cambio", "hostil", -0.5),
        ("hash_CC01", "Esto es muy buena propuesta MC", "positivo", 0.4),
        ("hash_DD01", "Que vergüenza de político ratero renuncia corrupto", "hostil", -0.7),
        # post 1 — maestros de ceremonias (mismo author >=3)
        ("hash_MC01", "Primer comment del maestro", None, None),
        ("hash_MC01", "Segundo comment del maestro", None, None),
        ("hash_MC01", "Tercer comment del maestro", None, None),
        ("hash_EE01", "Excelente trabajo en la colonia", "positivo", 0.3),
        ("hash_FF01", "Me voy a matar si sigue esta corrupción jaja", "hostil", -0.8),
        # post 2 — comments heterogéneos
        ("hash_GG01", "Que pendejo eres, mejor cállate putita", "hostil", -0.9),  # VPG + hate
        ("hash_HH01", "Eres una mujerzuela corrupta renuncia", "hostil", -0.9),  # VPG
        ("hash_II01", "PRI y PAN deben unirse contra MC", None, None),
        ("hash_JJ01", "Apoyo al PAN y acción nacional", None, None),
        ("hash_KK01", "Comentario neutro sobre politica", "neutral", 0.0),
        # post 3 — comments positivos
        ("hash_LL01", "Buena propuesta de seguridad", "positivo", 0.5),
        ("hash_MM01", "Excelente agenda", "positivo", 0.4),
        ("hash_NN01", "Bien por MC", "positivo", 0.3),
        ("hash_OO01", "morena gobierno federal cuarta transformación", None, None),
        ("hash_PP01", "Gracias por trabajar en la colonia", "positivo", 0.6),
        # post 4 — comments mezclados con rage
        ("hash_QQ01", "Renuncia ya corrupto ratero", "hostil", -0.8),
        ("hash_RR01", "Eres impresentable cínico", "hostil", -0.6),
        ("hash_SS01", "Fuera ladrón", "hostil", -0.7),
        ("hash_TT01", "Apoyo total", "positivo", 0.4),
        ("hash_UU01", "Buena obra pública", "positivo", 0.3),
        # post 5 — comments con violencia política directa
        ("hash_VV01", "te voy a matar maldito traidor", "hostil", -1.0),
        ("hash_WW01", "muerte a los corruptos del PAN", "hostil", -0.9),
        ("hash_XX01", "No voy a votar por ningún corrupto", "neutral", -0.1),
        ("hash_YY01", "PRI PAN deben unirse", None, None),
        ("hash_ZZ01", "apoyamos a MC", "positivo", 0.5),
    ]

    for i, (author_hash, content, tono, polaridad) in enumerate(comment_seed):
        post_id = post_ids[i // 5]
        published = now - timedelta(days=(i // 5) * 2, hours=i % 5)
        await db_session.execute(
            text(
                "INSERT INTO social_comments "
                "(parent_post_id, platform_comment_id, content, author_hash, likes, "
                "published_at, nlp_tono, nlp_polaridad, is_reply_to_comment, data_source) "
                "VALUES (:pid, :cid, :content, :ah, 1, :pa, :tono, :pol, false, 'test-tier2')"
            ),
            {
                "pid": post_id,
                "cid": f"test_tier2_{i}",
                "content": content,
                "ah": author_hash,
                "pa": published,
                "tono": tono,
                "pol": polaridad,
            },
        )

    # B16 seed promesa
    db_session.add(
        PromesaDirigente(
            dirigente_id=d.id,
            texto_promesa="Trabajaré para la seguridad pública de mi colonia",
            fecha_compromiso=None,
            estado=PromesaEstado.PENDIENTE,
        )
    )
    db_session.add(
        PromesaDirigente(
            dirigente_id=d.id,
            texto_promesa="Voy a cancelar toda colaboración con gobierno federal",
            fecha_compromiso=None,
            estado=PromesaEstado.PENDIENTE,
        )
    )

    await db_session.commit()
    await db_session.refresh(d)
    return d


@pytest.fixture
async def dirigente_tier2_sin_data(
    db_session: AsyncSession, org_tier2: Organizacion
) -> Dirigente:
    d = Dirigente(
        full_name="Sin Data Tier2",
        cargo="Regidor",
        partido="MC",
        estado="Oaxaca",
        org_id=org_tier2.id,
        sync_status=DirigenteSyncStatus.PENDING,
    )
    db_session.add(d)
    await db_session.commit()
    await db_session.refresh(d)
    return d
