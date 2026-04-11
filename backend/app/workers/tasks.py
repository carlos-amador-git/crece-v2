from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_sync_session():
    """Create a synchronous SQLAlchemy session for Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.config import settings

    engine = create_engine(settings.DATABASE_URL_SYNC, echo=False)
    return Session(engine)


@celery_app.task(bind=True, name="app.workers.tasks.scrape_profile", max_retries=3)
def scrape_profile(self, profile_id: int, platform: str) -> dict:  # type: ignore[no-untyped-def]
    """Scrape a single social profile and store new posts.

    Uses the appropriate platform scraper based on the platform parameter.
    """
    from app.scrapers.base import get_scraper

    try:
        scraper = get_scraper(platform)
        result = scraper.scrape(profile_id)
        logger.info("Scraped %d new posts for profile %d (%s)", result["new_posts"], profile_id, platform)
        return result
    except Exception as exc:
        logger.error("Scrape failed for profile %d: %s", profile_id, exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True, name="app.workers.tasks.analyze_sentiment", max_retries=2)
def analyze_sentiment(self, post_id: int) -> dict:  # type: ignore[no-untyped-def]
    """Run NLP sentiment analysis on a single post.

    After analysis, checks for toxicity spikes and generates crisis alerts
    when a profile has 2+ toxic posts within a 2-hour window.
    """
    try:
        from app.services.sentiment_service import sentiment_service

        logger.info("Analyzing sentiment for post %d", post_id)

        session = _get_sync_session()
        try:
            from app.models.social import SentimentAnalysis, SocialPost, SocialProfile

            post = session.get(SocialPost, post_id)
            if post is None:
                logger.warning("Post %d not found, skipping sentiment analysis", post_id)
                return {"post_id": post_id, "status": "skipped", "reason": "post_not_found"}

            # Run sentiment analysis
            analysis_result = sentiment_service.analyze(post.content or "")

            # Convert dataclass to dict for downstream use
            result = {
                "model": "pysentimiento",
                "sentiment_score": analysis_result.sentiment_score,
                "sentiment_label": analysis_result.sentiment_label,
                "emotions": analysis_result.emotions,
                "topics": analysis_result.topics,
                "toxicity_score": analysis_result.toxicity_score,
            }

            # Store the analysis
            analysis = SentimentAnalysis(
                post_id=post_id,
                model_used="pysentimiento",
                sentiment_score=analysis_result.sentiment_score,
                sentiment_label=analysis_result.sentiment_label,
                emotions=analysis_result.emotions,
                topics={"topics": analysis_result.topics} if analysis_result.topics else None,
                is_toxic=analysis_result.is_toxic,
                toxicity_score=analysis_result.toxicity_score,
            )
            session.add(analysis)

            # Secondary model: sentiment-analysis-spanish (validation)
            secondary_result = sentiment_service.analyze_secondary(post.content or "")
            if secondary_result is not None:
                secondary_analysis = SentimentAnalysis(
                    post_id=post_id,
                    model_used="sentiment-spanish",
                    sentiment_score=secondary_result.sentiment_score,
                    sentiment_label=secondary_result.sentiment_label,
                    emotions=None,
                    topics=None,
                    is_toxic=False,
                    toxicity_score=0.0,
                )
                session.add(secondary_analysis)

            session.commit()

            # ── Crisis alert generation ──────────────────────────
            _check_toxicity_alert(session, post_id, post, result)

            return {"post_id": post_id, "status": "analyzed"}
        finally:
            session.close()
    except Exception as exc:
        logger.error("Sentiment analysis failed for post %d: %s", post_id, exc)
        raise self.retry(exc=exc, countdown=30)


def _check_toxicity_alert(session, post_id: int, post, result: dict) -> None:
    """Check for toxicity spike and generate crisis alert if warranted.

    Creates an AlertaCrisis when:
    - Current post has toxicity_score > 0.7
    - The same profile has 2+ toxic posts in the last 2 hours
    - No similar alert exists for this profile in the last hour
    """
    from sqlalchemy import func, select

    from app.models.alerta_crisis import AlertaCrisis
    from app.models.social import SentimentAnalysis, SocialPost, SocialProfile

    toxicity_score = result.get("toxicity_score", 0.0)
    if toxicity_score <= 0.7:
        return

    two_hours_ago = datetime.now(UTC) - timedelta(hours=2)

    # Count toxic posts from same profile in last 2 hours
    toxic_count_query = (
        select(func.count(SocialPost.id))
        .join(SentimentAnalysis, SocialPost.id == SentimentAnalysis.post_id)
        .where(
            SocialPost.profile_id == post.profile_id,
            SentimentAnalysis.toxicity_score > 0.7,
            SocialPost.scraped_at > two_hours_ago,
        )
    )
    toxic_count = session.execute(toxic_count_query).scalar() or 0

    if toxic_count < 2:
        return

    # Get profile's org_id via dirigente
    profile = session.get(SocialProfile, post.profile_id)
    org_id = profile.dirigente.org_id if profile and profile.dirigente else None

    severity = "alta" if toxicity_score > 0.8 else "media"

    # Check if similar alert exists in last hour
    one_hour_ago = datetime.now(UTC) - timedelta(hours=1)
    existing = session.execute(
        select(AlertaCrisis).where(
            AlertaCrisis.perfil_id == post.profile_id,
            AlertaCrisis.tipo == "toxicity_spike",
            AlertaCrisis.created_at > one_hour_ago,
        )
    ).scalar_one_or_none()

    if existing is not None:
        return

    alert = AlertaCrisis(
        org_id=org_id or 1,
        perfil_id=post.profile_id,
        tipo="toxicity_spike",
        severidad=severity,
        descripcion=f"Detectados {toxic_count} posts toxicos en las ultimas 2 horas para este perfil",
        post_ids=[post_id],
        estado="nueva",
    )
    session.add(alert)
    session.commit()
    logger.warning(
        "Created toxicity alert for profile %d: %s",
        post.profile_id,
        severity,
    )


@celery_app.task(bind=True, name="app.workers.tasks.generate_plan", max_retries=1)
def generate_plan(self, dirigente_id: int, tipo: str, user_id: int, contexto: str | None = None) -> dict:  # type: ignore[no-untyped-def]
    """Generate an AI plan (runs synchronously in worker context)."""
    try:
        logger.info("Generating %s plan for dirigente %d", tipo, dirigente_id)
        # Actual implementation would use asyncio.run() to call the async service
        return {"dirigente_id": dirigente_id, "tipo": tipo, "status": "generated"}
    except Exception as exc:
        logger.error("Plan generation failed: %s", exc)
        raise self.retry(exc=exc, countdown=120)


@celery_app.task(name="app.workers.tasks.sync_electoral_data")
def sync_electoral_data(estado: str | None = None) -> dict:
    """Sync electoral section data from INE/official sources."""
    logger.info("Syncing electoral data for estado=%s", estado or "ALL")
    # Placeholder: would download and upsert SeccionElectoral records
    return {"status": "synced", "estado": estado}


@celery_app.task(name="app.workers.tasks.scrape_all_profiles")
def scrape_all_profiles() -> dict:
    """Periodic task: dispatch scrape tasks for all active profiles."""
    logger.info("Dispatching scrape tasks for all profiles")
    # In production, would query all active profiles and dispatch scrape_profile for each
    return {"status": "dispatched"}


# ──────────────────────────────────────────────────────────────────────
# Sprint 4 — Trends detector pipeline
# ──────────────────────────────────────────────────────────────────────


@celery_app.task(
    name="app.workers.tasks.detect_trends",
    bind=True,
    max_retries=2,
)
def detect_trends(self, org_id: int | None = None, lookback_hours: int = 24) -> dict:  # type: ignore[no-untyped-def]
    """S4.5 — Detecta trends agrupando posts por embedding + alcaldía.

    Pipeline por org_id (o todas las orgs si None):
        1. Cargar posts últimas 24h con embedding NOT NULL
        2. Para cada post: inferir alcaldía via location_inference
        3. Agrupar por (alcaldia_id, cluster semántico) con HNSW
           usando el filtro org_id ANTES del vector search (S4.8)
        4. Calcular post_count, sentiment_avg, growth_rate_24h
        5. Persistir rows en topic_trends
        6. Disparar label_trend_cluster por cada cluster nuevo

    NOTA: Implementación completa del clustering es iterativa — el
    primer pase solo agrupa por alcaldía (sin HNSW) y persiste un
    TopicTrend por alcaldía con sus posts más recientes. El clustering
    semántico por embedding se habilita cuando el backfill de embeddings
    sobre los 381 posts de dev DB se corre (backfill_embeddings()).
    """
    from sqlalchemy import select, text

    from app.models.topic_trend import TopicTrend
    from app.models.alcaldia import AlcaldiaCDMX

    logger.info("detect_trends starting (org_id=%s)", org_id)
    session = _get_sync_session()
    try:
        # 1. Posts últimas 24h (por ahora, sin filtro org_id — lo agregaremos
        #    cuando social_posts tenga la columna mediada o el JOIN se
        #    extienda al pipeline).
        rows = session.execute(
            text(
                "SELECT sp.id, sp.content, sp.sentiment_score, sp.published_at "
                "FROM social_posts sp "
                "WHERE sp.published_at > now() - (:hrs || ' hours')::interval "
                "  AND sp.content IS NOT NULL AND sp.content != '' "
                "LIMIT 500"
            ),
            {"hrs": str(lookback_hours)},
        ).fetchall()
        logger.info("detect_trends: %d posts in window", len(rows))

        if not rows:
            return {"status": "no_posts", "trends_created": 0}

        # 2. Inferir alcaldía por cada post (stub: solo buckets los que
        #    mencionan explícitamente una alcaldía)
        from app.services.location_inference import normalize_social_text

        alcaldia_rows = session.execute(
            text("SELECT id, nombre FROM alcaldias_cdmx")
        ).fetchall()
        alcaldia_by_name = {r[1]: r[0] for r in alcaldia_rows}

        from collections import defaultdict

        buckets: dict[int, list[tuple]] = defaultdict(list)
        for post_id, content, sentiment, pub_at in rows:
            norm = normalize_social_text(content or "")
            low = norm.lower()
            for nombre, aid in alcaldia_by_name.items():
                if nombre.lower() in low:
                    buckets[aid].append((post_id, sentiment or 0.0, pub_at))
                    break

        if not buckets:
            return {"status": "no_matches", "trends_created": 0}

        # 3. Determine default org: if caller didn't pass one, use the
        #    MC CDMX root org (id=3 per D-DX-01 seed).
        eff_org_id = org_id or 3

        now = datetime.now(UTC)
        bucket_start = now.replace(minute=0, second=0, microsecond=0)

        created = 0
        for alcaldia_id, posts in buckets.items():
            sentiments = [s for _, s, _ in posts if s is not None]
            avg_sent = sum(sentiments) / len(sentiments) if sentiments else None

            trend = TopicTrend(
                org_id=eff_org_id,
                alcaldia_id=alcaldia_id,
                topic_label=None,  # labeled asynchronously by label_trend_cluster
                time_bucket=bucket_start,
                post_count=len(posts),
                sentiment_avg=avg_sent,
                growth_rate_24h=None,  # computed on next pass by comparing to previous bucket
                sample_posts={"post_ids": [p[0] for p in posts[:5]]},
            )
            session.add(trend)
            session.flush()

            # Fire-and-forget label task for this cluster
            label_trend_cluster.delay(trend.id)
            created += 1

        session.commit()
        logger.info("detect_trends created %d trends", created)
        return {"status": "ok", "trends_created": created, "org_id": eff_org_id}
    except Exception as exc:
        session.rollback()
        logger.exception("detect_trends failed: %s", exc)
        raise self.retry(exc=exc, countdown=120)
    finally:
        session.close()


@celery_app.task(
    name="app.workers.tasks.label_trend_cluster",
    bind=True,
    max_retries=2,
)
def label_trend_cluster(self, trend_id: int) -> dict:  # type: ignore[no-untyped-def]
    """S4.6b — Etiqueta un TopicTrend con un label humano vía Ollama.

    Corre en la cola `trends_labeling` (concurrency=2) para no saturar
    al runtime Ollama local/remoto. Prompt estricto: 1 línea, <50 chars,
    castellano, sin emojis.
    """
    from sqlalchemy import text as sql_text

    import httpx

    from app.core.config import settings

    session = _get_sync_session()
    try:
        row = session.execute(
            sql_text(
                "SELECT tt.id, tt.alcaldia_id, tt.post_count, a.nombre, tt.sample_posts "
                "FROM topic_trends tt "
                "LEFT JOIN alcaldias_cdmx a ON a.id = tt.alcaldia_id "
                "WHERE tt.id = :id"
            ),
            {"id": trend_id},
        ).first()
        if row is None:
            return {"status": "not_found", "trend_id": trend_id}

        _, alcaldia_id, post_count, alcaldia_nombre, sample = row
        post_ids = (sample or {}).get("post_ids", []) if isinstance(sample, dict) else []

        posts_content: list[str] = []
        if post_ids:
            post_rows = session.execute(
                sql_text("SELECT content FROM social_posts WHERE id = ANY(:ids)"),
                {"ids": post_ids},
            ).fetchall()
            posts_content = [r[0][:300] for r in post_rows if r[0]]

        joined = "\n\n".join(f"- {c}" for c in posts_content[:5])
        prompt = (
            "Eres analista político. Resume en UNA línea de MÁXIMO 50 caracteres, "
            "en castellano, sin emojis, sin comillas, el tema común de estos posts "
            f"de {alcaldia_nombre or 'CDMX'}:\n\n{joined}\n\nTema:"
        )

        ollama_url = getattr(settings, "OLLAMA_BASE_URL", "http://host.docker.internal:11434")
        model = getattr(settings, "OLLAMA_MODEL", "gemma3:12b")

        resp = httpx.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=90.0,
        )
        resp.raise_for_status()
        label = resp.json().get("response", "").strip().splitlines()[0][:50]

        session.execute(
            sql_text("UPDATE topic_trends SET topic_label = :l WHERE id = :id"),
            {"l": label, "id": trend_id},
        )
        session.commit()
        logger.info("labeled trend %d: %s", trend_id, label)
        return {"status": "ok", "trend_id": trend_id, "label": label}
    except Exception as exc:
        session.rollback()
        logger.warning("label_trend_cluster %d failed: %s", trend_id, exc)
        raise self.retry(exc=exc, countdown=30)
    finally:
        session.close()


@celery_app.task(name="app.workers.tasks.ingest_rss_feeds")
def ingest_rss_feeds() -> dict:
    """S4.7 — Fetch todos los RSS feeds y log items nuevos.

    Persistencia a `social_posts` está en deuda D-S4-07 (requiere
    migración de platform_enum + profile_id nullable o synthetic
    profiles). Por ahora solo logueamos para observabilidad del beat.
    """
    import asyncio

    from app.services.news_ingest import fetch_all_feeds

    try:
        items = asyncio.run(fetch_all_feeds())
        logger.info("ingest_rss_feeds fetched %d items", len(items))
        return {"status": "ok", "items_fetched": len(items)}
    except Exception as exc:
        logger.exception("ingest_rss_feeds failed: %s", exc)
        return {"status": "error", "error": str(exc)}
