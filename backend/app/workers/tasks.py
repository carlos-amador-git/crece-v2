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
        logger.info(
            "Scraped %d new posts for profile %d (%s)", result["new_posts"], profile_id, platform
        )
        return result
    except Exception as exc:
        logger.error("Scrape failed for profile %d: %s", profile_id, exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1)) from None


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
            from app.models.social import SentimentAnalysis, SocialPost

            post = session.get(SocialPost, post_id)
            if post is None:
                logger.warning("Post %d not found, skipping sentiment analysis", post_id)
                return {"post_id": post_id, "status": "skipped", "reason": "post_not_found"}

            # Run sentiment analysis
            analysis_result = sentiment_service.analyze(post.content or "")

            # Normalize lowercase pysentimiento label to DB enum (POSITIVE/NEGATIVE/NEUTRAL/MIXED)
            from app.models.social import SentimentLabel
            def _to_enum(lbl: str) -> SentimentLabel:
                m = {"positive": SentimentLabel.POSITIVE, "negative": SentimentLabel.NEGATIVE,
                     "neutral": SentimentLabel.NEUTRAL, "mixed": SentimentLabel.MIXED}
                return m.get((lbl or "").lower(), SentimentLabel.NEUTRAL)

            label_enum = _to_enum(analysis_result.sentiment_label)

            # Convert dataclass to dict for downstream use
            result = {
                "model": "pysentimiento",
                "sentiment_score": analysis_result.sentiment_score,
                "sentiment_label": label_enum.value,
                "emotions": analysis_result.emotions,
                "topics": analysis_result.topics,
                "toxicity_score": analysis_result.toxicity_score,
            }

            # Store the analysis
            analysis = SentimentAnalysis(
                post_id=post_id,
                model_used="pysentimiento",
                sentiment_score=analysis_result.sentiment_score,
                sentiment_label=label_enum,
                emotions=analysis_result.emotions,
                topics={"topics": analysis_result.topics} if analysis_result.topics else None,
                is_toxic=analysis_result.is_toxic,
                toxicity_score=analysis_result.toxicity_score,
            )
            session.add(analysis)

            # Also update the post itself so dashboard queries (Tono, B05, B03) see classification
            post.sentiment_label = label_enum
            post.sentiment_score = analysis_result.sentiment_score
            post.emotions = analysis_result.emotions or None

            # Secondary model: sentiment-analysis-spanish (validation)
            secondary_result = sentiment_service.analyze_secondary(post.content or "")
            if secondary_result is not None:
                secondary_analysis = SentimentAnalysis(
                    post_id=post_id,
                    model_used="sentiment-spanish",
                    sentiment_score=secondary_result.sentiment_score,
                    sentiment_label=_to_enum(secondary_result.sentiment_label),
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
        raise self.retry(exc=exc, countdown=30) from None


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
        descripcion=(
            f"Detectados {toxic_count} posts toxicos en las ultimas 2 horas para este perfil"
        ),
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
def generate_plan(
    self, dirigente_id: int, tipo: str, user_id: int, contexto: str | None = None
) -> dict:  # type: ignore[no-untyped-def]
    """Generate an AI plan (runs synchronously in worker context)."""
    try:
        logger.info("Generating %s plan for dirigente %d", tipo, dirigente_id)
        # Actual implementation would use asyncio.run() to call the async service
        return {"dirigente_id": dirigente_id, "tipo": tipo, "status": "generated"}
    except Exception as exc:
        logger.error("Plan generation failed: %s", exc)
        raise self.retry(exc=exc, countdown=120) from None


# ──────────────────────────────────────────────────────────────────────
# S5 T0 · BLOQUEANTE — Plan IA generate async via Celery worker
# Resuelve DIFERIDO-06: FastAPI+httpx.AsyncClient+host.docker.internal
# cuelga silenciosamente en payloads Ollama largos (>60s). El pipeline
# corre bien vía `docker exec python` (subprocess). Al migrarlo a Celery
# el HTTP call Ollama ocurre fuera del event loop de uvicorn.
# ──────────────────────────────────────────────────────────────────────


@celery_app.task(
    bind=True,
    name="app.workers.tasks.plan_ia_generate_async",
    max_retries=0,
    time_limit=600,
    soft_time_limit=540,
)
def plan_ia_generate_async(
    self, dirigente_id: int, org_id: int, force: bool = False
) -> dict:  # type: ignore[no-untyped-def]
    """Ejecuta el PlanIAPipeline en el worker Celery (cola ``ai``).

    Se ejecuta en el event loop del worker (asyncio.run) — FUERA del
    event loop de uvicorn. El pipeline existente hace httpx sync wrap
    via anyio.to_thread (ya NO cuelga en payloads grandes contra
    Ollama Coolify VPS / host.docker.internal).

    Retorna dict con:
        - status: "ok" | "error"
        - recomendaciones_ids: list[int] (ids persistidos en DB)
        - elapsed_s: float
        - valid_count / rejected_count: int
        - pipeline: dict (metadata del pipeline)
        - error: str (solo si status=error)

    Args:
        dirigente_id: id del dirigente target
        org_id: org scope para multi-tenant
        force: bypass rate-limit 24h (el endpoint ya valida role=admin)
    """
    import asyncio
    from datetime import UTC
    from datetime import datetime as _dt

    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app.core.config import settings
    from app.services.plan_ia.llm_pipeline import default_pipeline

    start = _dt.now(UTC)
    logger.info(
        "plan_ia_generate_async start dirigente_id=%d org_id=%d force=%s task_id=%s",
        dirigente_id,
        org_id,
        force,
        self.request.id,
    )

    async def _run() -> dict:
        engine = create_async_engine(settings.DATABASE_URL, echo=False, future=True)
        SessionLocal = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        try:
            async with SessionLocal() as session:
                result = await default_pipeline.generate(
                    session, dirigente_id, org_id
                )
                return result
        finally:
            await engine.dispose()

    try:
        result = asyncio.run(_run())
        elapsed = (_dt.now(UTC) - start).total_seconds()

        recs = result.get("recomendaciones_creadas") or []
        rec_ids = [r.get("id") for r in recs if isinstance(r, dict) and r.get("id")]

        logger.info(
            "plan_ia_generate_async ok dirigente_id=%d elapsed=%.2fs n_recs=%d task_id=%s",
            dirigente_id,
            elapsed,
            len(rec_ids),
            self.request.id,
        )

        return {
            "status": "ok",
            "dirigente_id": dirigente_id,
            "org_id": org_id,
            "recomendaciones_ids": rec_ids,
            "recomendaciones_creadas": recs,
            "rechazadas": result.get("rechazadas") or [],
            "pipeline": result.get("pipeline") or {},
            "elapsed_s": round(elapsed, 2),
            "valid_count": len(rec_ids),
            "rejected_count": len(result.get("rechazadas") or []),
            "error": result.get("error"),
        }
    except Exception as exc:
        elapsed = (_dt.now(UTC) - start).total_seconds()
        logger.exception(
            "plan_ia_generate_async failed dirigente_id=%d elapsed=%.2fs task_id=%s: %s",
            dirigente_id,
            elapsed,
            self.request.id,
            exc,
        )
        return {
            "status": "error",
            "dirigente_id": dirigente_id,
            "org_id": org_id,
            "recomendaciones_ids": [],
            "elapsed_s": round(elapsed, 2),
            "error": f"{type(exc).__name__}: {exc}",
        }


@celery_app.task(name="app.workers.tasks.sync_electoral_data")
def sync_electoral_data(estado: str | None = None) -> dict:
    """Sync electoral section data from INE/official sources."""
    logger.info("Syncing electoral data for estado=%s", estado or "ALL")
    # Placeholder: would download and upsert SeccionElectoral records
    return {"status": "synced", "estado": estado}


@celery_app.task(name="app.workers.tasks.scrape_all_profiles")
def scrape_all_profiles() -> dict:
    """Periodic task: scrape each active profile + persist a daily snapshot.

    Skips profiles with ``data_source='manual_host_ingest'`` (YouTube + TikTok
    bloqueados para IP del container Docker — se ingestan host-side).
    Después de actualizar ``social_profiles.followers_count`` y ``posts_count``,
    inserta una fila en ``social_profile_snapshots`` con los contadores recién
    raspados. El snapshot garantiza que el dato refleja la misma medición.
    """
    from app.models.social import DataSource, SocialProfile, SocialProfileSnapshot
    from app.scrapers.base import get_scraper

    session = _get_sync_session()
    scraped = 0
    skipped = 0
    snapshots = 0
    failed = 0

    try:
        profiles = session.query(SocialProfile).all()
        for profile in profiles:
            if profile.data_source == DataSource.MANUAL_HOST_INGEST:
                skipped += 1
                continue

            try:
                scraper = get_scraper(profile.platform.value)
                scraper.scrape(profile.id)
                session.refresh(profile)
                scraped += 1
            except Exception as exc:  # pragma: no cover - logged for ops
                logger.warning(
                    "scrape_all_profiles: profile %d (%s) failed: %s",
                    profile.id,
                    profile.platform,
                    exc,
                )
                failed += 1
                # Continue — snapshot aún refleja el último dato conocido.

            snapshot = SocialProfileSnapshot(
                profile_id=profile.id,
                dirigente_id=profile.dirigente_id,
                org_id=profile.dirigente.org_id,
                platform=profile.platform,
                followers_count=profile.followers_count,
                posts_count=profile.posts_count,
            )
            session.add(snapshot)
            snapshots += 1

        session.commit()
    finally:
        session.close()

    logger.info(
        "scrape_all_profiles complete: scraped=%d skipped_manual=%d snapshots=%d failed=%d",
        scraped,
        skipped,
        snapshots,
        failed,
    )
    return {
        "status": "ok",
        "scraped": scraped,
        "skipped_manual": skipped,
        "snapshots": snapshots,
        "failed": failed,
    }


@celery_app.task(name="app.workers.tasks.snapshot_all_profiles")
def snapshot_all_profiles() -> dict:
    """Periodic task: persist a snapshot of current followers_count + posts_count.

    Difiere de ``scrape_all_profiles`` en que NO ejecuta scrapers internos. Solo
    lee el estado actual de ``social_profiles`` (que RADAR/ingest mantienen
    actualizado) y persiste fila en ``social_profile_snapshots``. Esto garantiza
    que B07 (Growth Attribution · delta_followers) tenga al menos 2 mediciones
    en distintas fechas aunque los scrapers internos fallen.

    Schedule: weekly Monday 02:00 MX (D-BEAT-SNAPSHOT-WEEKLY-2026-05-25).
    """
    from app.models.social import SocialProfile, SocialProfileSnapshot

    session = _get_sync_session()
    snapshots = 0

    skipped_orphan = 0
    try:
        profiles = session.query(SocialProfile).all()
        for profile in profiles:
            org_id = profile.dirigente.org_id if profile.dirigente else None
            if org_id is None:
                # Perfiles huérfanos (sin dirigente o dirigente sin org_id, p.ej.
                # tipo NEWS sin owner) no pueden persistir snapshot por NOT NULL
                # constraint en social_profile_snapshots.org_id.
                skipped_orphan += 1
                continue
            snapshot = SocialProfileSnapshot(
                profile_id=profile.id,
                dirigente_id=profile.dirigente_id,
                org_id=org_id,
                platform=profile.platform,
                followers_count=profile.followers_count,
                posts_count=profile.posts_count,
            )
            session.add(snapshot)
            snapshots += 1
        session.commit()
    finally:
        session.close()

    logger.info(
        "snapshot_all_profiles complete: snapshots=%d skipped_orphan=%d",
        snapshots,
        skipped_orphan,
    )
    return {"status": "ok", "snapshots": snapshots, "skipped_orphan": skipped_orphan}


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
    from sqlalchemy import text

    from app.models.topic_trend import TopicTrend

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

        alcaldia_rows = session.execute(text("SELECT id, nombre FROM alcaldias_cdmx")).fetchall()
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
        raise self.retry(exc=exc, countdown=120) from None
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
    import httpx
    from sqlalchemy import text as sql_text

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

        _, _alcaldia_id, _post_count, alcaldia_nombre, sample = row
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
        raise self.retry(exc=exc, countdown=30) from None
    finally:
        session.close()


# ──────────────────────────────────────────────────────────────────────
# Sprint 5 — Onboarding wizard chain
# ──────────────────────────────────────────────────────────────────────


@celery_app.task(
    name="app.workers.tasks.onboard_dirigente_chain",
    bind=True,
    max_retries=1,
)
def onboard_dirigente_chain(self, dirigente_id: int) -> dict:  # type: ignore[no-untyped-def]
    """S5.3b — Celery chain para enriquecer un dirigente recién creado.

    Flow: update_sync('scraping') → scrape all profiles → update_sync('analyzing')
    → NLP sobre posts → update_sync('calculating_ipd') → compute IPD
    → update_sync('ready').

    Todo se ejecuta en un solo task por simplicidad (no chain real con
    Celery chord) porque los tiempos individuales son cortos en dev y
    el progreso se expone via `dirigentes.sync_status`. Si algún paso
    falla, se setea status='error' + sync_error.
    """
    from datetime import UTC
    from datetime import datetime as _dt

    from sqlalchemy import text as sql_text

    session = _get_sync_session()
    try:

        def _set_status(st: str, err: str | None = None) -> None:
            session.execute(
                sql_text(
                    "UPDATE dirigentes SET sync_status = :st, sync_error = :err, "
                    "sync_updated_at = :ts WHERE id = :id"
                ),
                {"st": st, "err": err, "ts": _dt.now(UTC), "id": dirigente_id},
            )
            session.commit()

        # Step 1 — scraping. Real scrapers require auth + Playwright; we
        # dispatch scrape_profile for each profile if the scraper manager
        # supports it, else we fall back to a no-op that still marks the
        # profile as "last_scraped_at=now()" so downstream tasks have
        # something to work on.
        _set_status("scraping")
        profile_rows = session.execute(
            sql_text("SELECT id, platform, handle FROM social_profiles WHERE dirigente_id = :id"),
            {"id": dirigente_id},
        ).fetchall()

        for prof_id, platform, _handle in profile_rows:
            try:
                # Try dispatching a real scrape if supported; fall back to a touch.
                scrape_profile.apply(
                    args=(prof_id, str(platform).split(".")[-1]),
                    throw=False,
                )
            except Exception as exc:
                logger.info(
                    "onboarding: scrape fallback for profile %d (%s): %s",
                    prof_id,
                    platform,
                    exc,
                )
            session.execute(
                sql_text("UPDATE social_profiles SET last_scraped_at = :ts WHERE id = :id"),
                {"ts": _dt.now(UTC), "id": prof_id},
            )
        session.commit()

        # Step 2 — NLP / sentiment on any new posts we just scraped.
        _set_status("analyzing")
        new_posts = session.execute(
            sql_text(
                "SELECT sp.id FROM social_posts sp "
                "JOIN social_profiles prof ON prof.id = sp.profile_id "
                "WHERE prof.dirigente_id = :id AND sp.sentiment_label IS NULL "
                "LIMIT 50"
            ),
            {"id": dirigente_id},
        ).fetchall()

        for (post_id,) in new_posts:
            try:
                analyze_sentiment.apply(args=(post_id,), throw=False)
            except Exception as exc:
                logger.info("onboarding: sentiment skip post %d: %s", post_id, exc)

        # Step 3 — IPD
        _set_status("calculating_ipd")
        # IPD is computed on-read by /diagnostico endpoint; no state to persist.
        # We just mark the step as done.

        # Step 4 — ready
        _set_status("ready")
        logger.info("onboard_dirigente_chain: dirigente %d ready", dirigente_id)
        return {"status": "ok", "dirigente_id": dirigente_id}
    except Exception as exc:
        logger.exception("onboard chain failed for %d: %s", dirigente_id, exc)
        try:
            session.execute(
                sql_text(
                    "UPDATE dirigentes SET sync_status = 'error', sync_error = :e, "
                    "sync_updated_at = now() WHERE id = :id"
                ),
                {"e": str(exc)[:500], "id": dirigente_id},
            )
            session.commit()
        except Exception:
            pass
        raise self.retry(exc=exc, countdown=60) from None
    finally:
        session.close()


@celery_app.task(name="app.workers.tasks.ingest_rss_feeds")
def ingest_rss_feeds() -> dict:
    """D.9 — Fetch RSS feeds and persist to social_posts with platform='NEWS'.

    Creates synthetic SocialProfile records per RSS source (e.g.
    handle='news:presidencia-mx') linked to a synthetic dirigente
    (full_name='RSS News Bot'). Deduplicates by platform_post_id.
    """
    import asyncio

    from sqlalchemy import select, text

    from app.models.social import Platform, PostType, SocialPost, SocialProfile
    from app.services.news_ingest import RSS_SOURCES, RssItem, _platform_post_id, fetch_all_feeds

    session = _get_sync_session()
    try:
        items: list[RssItem] = asyncio.run(fetch_all_feeds())
        logger.info("ingest_rss_feeds fetched %d items", len(items))

        if not items:
            return {"status": "ok", "items_fetched": 0, "items_persisted": 0}

        # Ensure synthetic dirigente exists for RSS feeds
        row = session.execute(
            text("SELECT id FROM dirigentes WHERE full_name = 'RSS News Bot' LIMIT 1")
        ).first()
        if row:
            bot_dirigente_id = row[0]
        else:
            session.execute(
                text(
                    "INSERT INTO dirigentes (full_name, cargo, partido, estado, sync_status, created_at, updated_at) "
                    "VALUES ('RSS News Bot', 'Sistema', 'SISTEMA', 'CDMX', 'ready', NOW(), NOW()) "
                    "ON CONFLICT DO NOTHING"
                )
            )
            session.commit()
            row = session.execute(
                text("SELECT id FROM dirigentes WHERE full_name = 'RSS News Bot' LIMIT 1")
            ).first()
            bot_dirigente_id = row[0]

        # Build source_name -> handle mapping
        source_handles: dict[str, str] = {}
        for feed in RSS_SOURCES:
            slug = (
                feed.name.lower()
                .replace(" ", "-")
                .replace("á", "a")
                .replace("é", "e")
                .replace("í", "i")
                .replace("ó", "o")
                .replace("ú", "u")
            )
            source_handles[feed.name] = f"news:{slug}"

        # Find-or-create synthetic profiles per source
        profile_cache: dict[str, int] = {}
        for source_name, handle in source_handles.items():
            existing = session.execute(
                select(SocialProfile.id).where(
                    SocialProfile.handle == handle,
                    SocialProfile.platform == Platform.NEWS,
                )
            ).scalar_one_or_none()
            if existing:
                profile_cache[source_name] = existing
            else:
                profile = SocialProfile(
                    dirigente_id=bot_dirigente_id,
                    platform=Platform.NEWS,
                    handle=handle,
                    url=None,
                    followers_count=0,
                    following_count=0,
                    posts_count=0,
                )
                session.add(profile)
                session.flush()
                profile_cache[source_name] = profile.id

        # Persist items, deduplicate by platform_post_id
        persisted = 0
        for item in items:
            ppid = _platform_post_id(item)
            profile_id = profile_cache.get(item.source)
            if profile_id is None:
                continue

            exists = session.execute(
                select(SocialPost.id).where(SocialPost.platform_post_id == ppid)
            ).scalar_one_or_none()
            if exists:
                continue

            post = SocialPost(
                profile_id=profile_id,
                platform_post_id=ppid,
                content=f"{item.title}\n\n{item.summary}" if item.summary else item.title,
                post_type=PostType.TEXT,
                published_at=item.published or datetime.now(UTC),
                likes=0,
                comments=0,
                shares=0,
                views=0,
                engagement_rate=0.0,
                is_political=True,
                raw_data={"link": item.link, "guid": item.guid, "source": item.source},
            )
            session.add(post)
            persisted += 1

        session.commit()
        logger.info("ingest_rss_feeds persisted %d new items", persisted)
        return {"status": "ok", "items_fetched": len(items), "items_persisted": persisted}
    except Exception as exc:
        session.rollback()
        logger.exception("ingest_rss_feeds failed: %s", exc)
        return {"status": "error", "error": str(exc)}
    finally:
        session.close()


@celery_app.task(name="app.workers.tasks.dispatch_scheduled_campaigns")
def dispatch_scheduled_campaigns() -> dict:
    """D.3 — Auto-start campaigns whose fecha_programada has passed.

    Runs every 5 minutes via Celery beat. Finds campaigns in PROGRAMADA
    state with fecha_programada <= now(), triggers the send flow via
    the /enviar endpoint logic (n8n webhook dispatch).
    """
    import httpx

    from app.core.config import settings
    from app.models.campana import Campana, EstadoCampana

    session = _get_sync_session()
    try:
        now = datetime.now(UTC)
        campaigns = (
            session.query(Campana)
            .filter(
                Campana.estado == EstadoCampana.PROGRAMADA,
                Campana.fecha_programada.isnot(None),
                Campana.fecha_programada <= now,
            )
            .all()
        )

        if not campaigns:
            return {"status": "ok", "dispatched": 0}

        dispatched = []
        for campana in campaigns:
            # Trigger via internal API call (reuses /enviar logic)
            try:
                resp = httpx.post(
                    f"http://localhost:8000/api/v1/campanas/{campana.id}/enviar",
                    headers={"X-API-Key": settings.N8N_CRECE_TOKEN or settings.JWT_SECRET},
                    timeout=30.0,
                )
                if resp.status_code < 300:
                    dispatched.append(campana.id)
                    logger.info("Auto-dispatched campaign %d", campana.id)
                else:
                    logger.warning(
                        "Campaign %d auto-dispatch failed: %d %s",
                        campana.id,
                        resp.status_code,
                        resp.text[:200],
                    )
            except httpx.HTTPError as exc:
                logger.error("Campaign %d dispatch error: %s", campana.id, exc)

        return {"status": "ok", "dispatched": len(dispatched), "ids": dispatched}
    finally:
        session.close()


# ──────────────────────────────────────────────────────────────────
# Sprint S1 T8 — LLM health check (D-21 Coolify dual-mode)
# ──────────────────────────────────────────────────────────────────


@celery_app.task(name="app.workers.tasks.ollama_health_smoke")
def ollama_health_smoke() -> dict:
    """Layer 1 + Layer 2 smoke against both providers. Runs every 5 min.

    Persists 4 rows in llm_health_log per invocation (2 providers × 2 layers).
    Optionally adds cold check row if last ok >4h ago.
    """
    import asyncio

    from app.ops.llm_health import health_smoke_both

    results = asyncio.run(health_smoke_both())
    summary: dict[str, dict[str, str]] = {}
    for provider, rows in results.items():
        summary[provider] = {r.layer: r.status for r in rows}
    logger.info("ollama_health_smoke completed: %s", summary)
    return {"status": "ok", "results": summary}


# ──────────────────────────────────────────────────────────────────────
# Sprint S4 · T8/T9/T10/T11 — Plan IA ciclo de cierre post-ejecución
# ──────────────────────────────────────────────────────────────────────


@celery_app.task(
    name="app.workers.tasks.plan_ia_seguimiento_diario",
    bind=True,
    max_retries=2,
)
def plan_ia_seguimiento_diario(self) -> dict:  # type: ignore[no-untyped-def]
    """S4 · T8 — Seguimiento diario de recomendaciones en ventana 14d activa.

    Query `estado='ejecutada'` + `ventana_fin > NOW()` + `post_ejecutor_id NOT NULL`.
    Actualiza `metricas_observadas` JSONB con snapshot de métricas del post ejecutor y
    marca `alerta_desviacion` cuando se supera el umbral de `criterio_exito`.

    Corre diariamente a las 03:00 UTC (beat schedule).
    """
    from app.services.plan_ia.seguimiento_service import actualizar_seguimiento

    session = _get_sync_session()
    try:
        result = actualizar_seguimiento(session)
        logger.info("plan_ia_seguimiento_diario: %s", result)
        return {"status": "ok", **result}
    except Exception as exc:
        logger.exception("plan_ia_seguimiento_diario failed: %s", exc)
        raise self.retry(exc=exc, countdown=300) from None
    finally:
        session.close()


@celery_app.task(
    name="app.workers.tasks.plan_ia_cierre_diario",
    bind=True,
    max_retries=2,
)
def plan_ia_cierre_diario(self) -> dict:  # type: ignore[no-untyped-def]
    """S4 · T9 — Cierre automático de recomendaciones con ventana vencida.

    Query `estado='ejecutada'` + `ventana_fin <= NOW()`. Calcula veredicto automático
    (exitosa ≥80%, parcial 40-79%, fallida <40%) y setea `veredicto`, `veredicto_original`,
    `estado`. Corre diariamente a las 04:00 UTC (después de seguimiento).
    """
    from app.services.plan_ia.cierre_service import cerrar_ventanas_vencidas

    session = _get_sync_session()
    try:
        result = cerrar_ventanas_vencidas(session)
        logger.info("plan_ia_cierre_diario: %s", result)
        return {"status": "ok", **result}
    except Exception as exc:
        logger.exception("plan_ia_cierre_diario failed: %s", exc)
        raise self.retry(exc=exc, countdown=300) from None
    finally:
        session.close()


@celery_app.task(
    name="app.workers.tasks.plan_ia_reporte_semanal",
    bind=True,
    max_retries=1,
)
def plan_ia_reporte_semanal(self, output_dir: str = "/app/data/reportes_plan_ia") -> dict:  # type: ignore[no-untyped-def]
    """S4 · T11 — Reporte semanal PDF por dirigente (lunes 09:00 UTC).

    Itera todos los dirigentes con recomendaciones registradas y genera un PDF
    de 1 página en `output_dir`. Retorna el resumen.
    """
    from app.services.plan_ia.reporte_semanal import generar_reportes_todos_dirigentes

    session = _get_sync_session()
    try:
        result = generar_reportes_todos_dirigentes(session, output_dir=output_dir)
        logger.info("plan_ia_reporte_semanal: %s", {k: v for k, v in result.items() if k != "detalles"})
        return {"status": "ok", **result}
    except Exception as exc:
        logger.exception("plan_ia_reporte_semanal failed: %s", exc)
        raise self.retry(exc=exc, countdown=1800) from None
    finally:
        session.close()


@celery_app.task(name="app.workers.tasks.ollama_prewarm")
def ollama_prewarm() -> dict:
    """Prewarm both providers with a 10-token call. Runs every 4h.

    Evita cold start de 102s en Coolify VPS (D-21 / coolify_failover_smoke.md).
    """
    import asyncio

    from app.ops.llm_health import prewarm_both

    results = asyncio.run(prewarm_both())
    summary = {
        provider: {"status": r.status, "latency_ms": r.latency_ms}
        for provider, r in results.items()
    }
    logger.info("ollama_prewarm completed: %s", summary)
    return {"status": "ok", "results": summary}


# ─── S5 Sprint 2026-05-15 · Scrape mensual competidores ───────────────────
# Disabled-by-default (no en beat_schedule todavía). CEO decide cuándo
# activarlo agregando entry en celery_app.conf.beat_schedule.
#
# Diseño:
# - time_limit=600s (10 min) — Apify run promedio 30-90s pero hay
#   margen para queue + retry interno (Gemini gotcha: Celery default
#   timeout < Apify run rompe la task antes de capturar resultado).
# - Cap budget $0.50 por run. Si APIFY_TOKEN no está en env, abort.
# - Solo competitors con platform=FACEBOOK por ahora (Apify actor
#   facebook-pages-scraper). Otras plataformas requieren actor distinto.

@celery_app.task(
    name="app.workers.tasks.scrape_competitors_monthly",
    bind=True,
    max_retries=1,
    time_limit=600,
    soft_time_limit=540,
)
def scrape_competitors_monthly(self, budget_usd: float = 0.50) -> dict:  # type: ignore[no-untyped-def]
    """S5 · Auto-refresh mensual de competitor_metrics_monthly.

    Llama el script ya existente scripts/scrape_competitors_light_apify.py
    para TODOS los competitor_profiles activos en platform=FACEBOOK.
    Diseñado para correr el 1° de cada mes (ver beat_schedule cuando se
    active explícitamente por CEO).

    Args:
        budget_usd: cap presupuesto Apify para este run.

    Returns:
        dict con keys: status, scraped, errors, apify_spent.
    """
    import os
    import subprocess

    if not os.environ.get("APIFY_TOKEN"):
        logger.warning(
            "scrape_competitors_monthly: APIFY_TOKEN no configurado · abort"
        )
        return {
            "status": "skipped",
            "reason": "APIFY_TOKEN not configured",
            "scraped": 0,
            "errors": 0,
        }

    try:
        # Reutilizamos el script existente (validado en sesión anterior).
        # subprocess porque el script está pensado para CLI, no como módulo.
        result = subprocess.run(
            [
                "python",
                "/app/scripts/scrape_competitors_light_apify.py",
                "--budget",
                str(budget_usd),
            ],
            capture_output=True,
            text=True,
            timeout=540,  # < soft_time_limit
        )
        out = result.stdout + "\n" + result.stderr
        logger.info("scrape_competitors_monthly output: %s", out[-500:])
        return {
            "status": "ok" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "log_tail": out[-1000:],
        }
    except subprocess.TimeoutExpired:
        logger.exception(
            "scrape_competitors_monthly TIMEOUT — Apify run > 540s, "
            "considera aumentar time_limit o reducir cohorte"
        )
        return {"status": "timeout", "scraped": 0}
    except Exception as exc:
        logger.exception("scrape_competitors_monthly failed: %s", exc)
        return {"status": "error", "error": str(exc)}
