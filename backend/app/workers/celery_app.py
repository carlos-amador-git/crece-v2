from __future__ import annotations

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_process_init

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
    # autodiscover solo barre app.workers.tasks — módulos extra van explícitos
    imports=("app.workers.ingest_tasks",),
    task_routes={
        # Handoff RADAR→CRECE (PLAN-2026-06-11) → cola data (ingest, no NLP)
        "app.workers.ingest_tasks.process_radar_handoff": {"queue": "data"},
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
        # S4 T8/T9/T11 · Plan IA cierre de ciclo → cola ai
        "app.workers.tasks.plan_ia_seguimiento_diario": {"queue": "ai"},
        "app.workers.tasks.plan_ia_cierre_diario": {"queue": "ai"},
        "app.workers.tasks.plan_ia_reporte_semanal": {"queue": "ai"},
        # S5 T0 · Plan IA generate bajo demanda (resuelve DIFERIDO-06) → cola ai
        "app.workers.tasks.plan_ia_generate_async": {"queue": "ai"},
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
        # LFPDPPP retention: cleanup social_comments >180d daily at 3 AM MX
        "cleanup-old-comments-daily": {
            "task": "app.workers.retention_tasks.cleanup_old_comments",
            "schedule": 86400.0,
        },
        # NOTE: ollama-health-smoke-5min + ollama-prewarm-4h removed — they
        # deliberately loaded the ~8GB gemma3:12b model on a schedule and were
        # the primary OOM trigger on the shared VPS. Restore when Ollama runs
        # on its own host (see OLLAMA_ENABLED).
        # S4 T8 · Plan IA seguimiento diario — 03:00 UTC
        "plan-ia-seguimiento-diario": {
            "task": "app.workers.tasks.plan_ia_seguimiento_diario",
            "schedule": crontab(hour=3, minute=0),
        },
        # S4 T9 · Plan IA cierre automático diario — 04:00 UTC
        "plan-ia-cierre-diario": {
            "task": "app.workers.tasks.plan_ia_cierre_diario",
            "schedule": crontab(hour=4, minute=0),
        },
        # S4 T11 · Plan IA reporte semanal — lunes 09:00 UTC
        "plan-ia-reporte-semanal": {
            "task": "app.workers.tasks.plan_ia_reporte_semanal",
            "schedule": crontab(hour=9, minute=0, day_of_week=1),
        },
        # D-BEAT-SNAPSHOT-WEEKLY-2026-05-25 · destrabra B07 delta_followers
        # Lunes 02:00 America/Mexico_City (timezone configurada en este module).
        "snapshot-all-profiles-weekly": {
            "task": "app.workers.tasks.snapshot_all_profiles",
            "schedule": crontab(hour=2, minute=0, day_of_week=1),
        },
    },
)

celery_app.autodiscover_tasks(["app.workers"])


@worker_process_init.connect
def _init_orm_event_listeners(**_kwargs) -> None:
    """Registra los event listeners de SQLAlchemy en cada proceso worker.

    Los scrapers insertan/actualizan posts vía ORM dentro del worker Celery, NO
    en el proceso uvicorn (que registra los listeners en su lifespan). Sin esto,
    engagement_rate no se calcularía en la ruta de ingest automática, y las ops
    destructivas en tasks (delete/update de modelos auditados) no se registrarían
    en audit_log (gap LFPDPPP art. 32). En contexto Celery el audit queda con
    user_id=NULL ("operación de sistema") — comportamiento esperado y seguro.
    """
    from app.core.audit_listeners import init_audit_listeners
    from app.core.engagement_listeners import init_engagement_listeners

    init_engagement_listeners()
    init_audit_listeners()
