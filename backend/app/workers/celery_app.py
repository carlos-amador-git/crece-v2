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
    },
    beat_schedule={
        "scrape-all-profiles-daily": {
            "task": "app.workers.tasks.scrape_all_profiles",
            "schedule": 86400.0,  # 24 hours
        },
    },
)

celery_app.autodiscover_tasks(["app.workers"])
