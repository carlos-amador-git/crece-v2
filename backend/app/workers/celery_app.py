from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "crece_v2",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="America/Mexico_City",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    task_routes={
        "app.workers.tasks.scrape_profile": {"queue": "scraping"},
        "app.workers.tasks.analyze_sentiment": {"queue": "nlp"},
        "app.workers.tasks.generate_plan": {"queue": "ai"},
        "app.workers.tasks.sync_electoral_data": {"queue": "data"},
        # S4.5 trends detector → cola propia para aislar latencia
        "app.workers.tasks.detect_trends": {"queue": "trends"},
        # S4.6a Ollama batch labeling → cola dedicada con concurrency=2
        # (el worker debe lanzarse con `-Q trends_labeling --concurrency 2`)
        "app.workers.tasks.label_trend_cluster": {"queue": "trends_labeling"},
        # S4.7 RSS ingest → comparte cola data
        "app.workers.tasks.ingest_rss_feeds": {"queue": "data"},
        # S5.3b onboarding chain → cola scraping (usa scrape_profile + nlp)
        "app.workers.tasks.onboard_dirigente_chain": {"queue": "scraping"},
    },
    beat_schedule={
        "scrape-all-profiles-daily": {
            "task": "app.workers.tasks.scrape_all_profiles",
            "schedule": 86400.0,  # 24 hours
        },
        # S4.5 trends detector corre cada hora
        "detect-trends-hourly": {
            "task": "app.workers.tasks.detect_trends",
            "schedule": 3600.0,
        },
        # S4.7 RSS ingest cada 3 horas
        "ingest-rss-feeds-every-3h": {
            "task": "app.workers.tasks.ingest_rss_feeds",
            "schedule": 10800.0,
        },
        # D.3 campaign scheduler — check every 5 min for scheduled campaigns
        "dispatch-scheduled-campaigns": {
            "task": "app.workers.tasks.dispatch_scheduled_campaigns",
            "schedule": 300.0,
        },
    },
)

celery_app.autodiscover_tasks(["app.workers"])
