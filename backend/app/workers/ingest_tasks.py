from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from app.workers.celery_app import celery_app
from app.workers.tasks import _get_sync_session

logger = logging.getLogger(__name__)

# Backend root dentro del container/host (scripts/ vive aquí — viaja en la imagen).
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent

_LOCK_TTL = 60 * 60  # 1h — cubre el ingest más largo observado

# Tablas cuyo delta medimos antes/después (reporte falsificable, SOP "medir, no inferir").
_DELTA_SQL = {
    "social_posts": (
        "SELECT count(*) FROM social_posts p JOIN social_profiles sp ON sp.id=p.profile_id "
        "WHERE sp.dirigente_id=:d"
    ),
    "social_comments": (
        "SELECT count(*) FROM social_comments c JOIN social_posts p ON p.id=c.parent_post_id "
        "JOIN social_profiles sp ON sp.id=p.profile_id WHERE sp.dirigente_id=:d"
    ),
    "watched_like_events": (
        "SELECT count(*) FROM watched_like_events w JOIN social_posts p ON p.id=w.post_id "
        "JOIN social_profiles sp ON sp.id=p.profile_id WHERE sp.dirigente_id=:d"
    ),
}


def _db_counts(session, dirigente_id: int) -> dict[str, int]:
    from sqlalchemy import text

    return {
        tabla: session.execute(text(sql), {"d": dirigente_id}).scalar() or 0
        for tabla, sql in _DELTA_SQL.items()
    }


def _profile_id(session, dirigente_id: int, platform: str) -> int | None:
    from sqlalchemy import text

    return session.execute(
        text("SELECT id FROM social_profiles WHERE dirigente_id=:d AND platform=:p LIMIT 1"),
        {"d": dirigente_id, "p": platform},
    ).scalar()


def _download_bundle(minio_path: str, file_names: list[str], workdir: Path) -> None:
    """Descarga los archivos del bundle desde MinIO (S3-compatible, boto3)."""
    import boto3

    from app.core.config import settings

    client = boto3.client(
        "s3",
        endpoint_url=("https://" if settings.MINIO_SECURE else "http://") + settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
    )
    prefix = minio_path.rstrip("/")
    for name in file_names:
        client.download_file(settings.MINIO_BUCKET, f"{prefix}/{name}", str(workdir / name))


def _run_adapter(args: list[str], extra_env: dict[str, str] | None = None) -> None:
    """Corre un adapter del SOP como subprocess (mismo código probado, cero refactor)."""
    from app.core.config import settings

    env = os.environ.copy()
    # ANEXAR al PYTHONPATH del container (no sobreescribir — la imagen worker
    # resuelve site-packages vía PYTHONPATH=/app/.local/...; pisarlo = ModuleNotFoundError)
    env["PYTHONPATH"] = str(_BACKEND_ROOT) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    env["DATABASE_URL_RAW"] = settings.DATABASE_URL_SYNC
    if extra_env:
        env.update(extra_env)
    cmd = [sys.executable, *args]
    result = subprocess.run(
        cmd, cwd=_BACKEND_ROOT, env=env, capture_output=True, text=True, timeout=1800
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"adapter {' '.join(args[:2])} rc={result.returncode}: {result.stderr[-800:]}"
        )
    logger.info("adapter ok: %s", " ".join(args[:2]))


def _run_sop_chain(session, workdir: Path, dirigente_id: int, present: set[str]) -> list[str]:
    """Cadena de adapters en orden SOP. Solo corre pasos cuyo archivo está en el bundle.

    Orden CRÍTICO (SOP §2): followers ANTES que posts (ER se computa con followers).
    Devuelve lista de pasos ejecutados.
    """
    steps: list[str] = []
    d = str(dirigente_id)

    if "followers.json" in present:
        _run_adapter(
            [
                "scripts/ingest_radar_followers.py",
                "--dirigente-id", d,
                "--followers", str(workdir / "followers.json"),
                "--commit",
            ]
        )
        steps.append("followers")

    for fname, plat in (
        ("x_posts.json", "TWITTER"),
        ("yt_posts.json", "YOUTUBE"),
        ("tt_posts.json", "TIKTOK"),
        ("fb_posts.json", "FACEBOOK"),
    ):
        if fname in present:
            _run_adapter(
                [
                    "scripts/ingest_radar_yt_x_posts.py",
                    "--json", str(workdir / fname),
                    "--platform", plat,
                    "--dirigente-id", d,
                    "--commit",
                ]
            )
            steps.append(f"posts:{plat}")

    if "ig_posts.json" in present:
        ig_pid = _profile_id(session, dirigente_id, "INSTAGRAM")
        if ig_pid is None:
            raise RuntimeError("bundle trae ig_posts.json pero el dirigente no tiene perfil IG")
        args = [
            "scripts/ingest_radar_ig.py",
            "--dirigente-id", d,
            "--profile-id", str(ig_pid),
            "--posts", str(workdir / "ig_posts.json"),
            "--commit",
        ]
        if "ig_comments.json" in present:
            args[-1:-1] = ["--comments", str(workdir / "ig_comments.json")]
        _run_adapter(args)
        steps.append("ig")

    if "fb_comments.json" in present:
        fb_pid = _profile_id(session, dirigente_id, "FACEBOOK")
        if fb_pid is None:
            raise RuntimeError("bundle trae fb_comments.json pero el dirigente no tiene perfil FB")
        _run_adapter(
            [
                "scripts/ingest_radar_comments_payload.py",
                "--dirigente-id", d,
                "--profile-id", str(fb_pid),
                "--comments", str(workdir / "fb_comments.json"),
                "--commit",
            ]
        )
        steps.append("comments:FB")

    if "reactors.json" in present:
        for plat in ("FACEBOOK", "INSTAGRAM"):
            _run_adapter(
                [
                    "scripts/ingest_radar_reactors_v2.py",
                    "--json", str(workdir / "reactors.json"),
                    "--commit",
                ],
                extra_env={"DIRIGENTE_ID": d, "PLATFORM": plat},
            )
            steps.append(f"reactors:{plat}")

    return steps


def _enqueue_local_nlp(session, dirigente_id: int) -> int:
    """Fase 1 NLP local: encola analyze_sentiment para posts del dirigente sin score.

    Reusa la task Celery existente (pysentimiento local, $0 tokens). Idempotente:
    solo posts con sentiment_score IS NULL.
    """
    from sqlalchemy import text

    from app.workers.tasks import analyze_sentiment

    rows = session.execute(
        text(
            "SELECT p.id FROM social_posts p JOIN social_profiles sp ON sp.id=p.profile_id "
            "WHERE sp.dirigente_id=:d AND p.sentiment_score IS NULL"
        ),
        {"d": dirigente_id},
    ).scalars().all()
    for post_id in rows:
        analyze_sentiment.delay(post_id)
    return len(rows)


@celery_app.task(
    bind=True,
    name="app.workers.ingest_tasks.process_radar_handoff",
    max_retries=2,
)
def process_radar_handoff(self, job_id: int) -> dict:  # type: ignore[no-untyped-def]
    """Procesa un handoff RADAR (PLAN-2026-06-11 · cadena Fase 1).

    MinIO → validación (Tainted gate) → adapters SOP → gate cobertura → NLP local.
    Lock Redis por dirigente: nunca 2 bundles del mismo dirigente a la vez.
    """
    import redis as redis_lib

    from app.core.config import settings
    from app.models.ingest_job import IngestJob, IngestJobStatus
    from app.services.radar_ingest import coverage_gaps_sync, validate_bundle

    session = _get_sync_session()
    job = session.get(IngestJob, job_id)
    if job is None:
        return {"error": f"job {job_id} no existe"}

    redis_client = redis_lib.Redis.from_url(settings.REDIS_URL)
    lock = redis_client.lock(f"radar-ingest:dirigente:{job.dirigente_id}", timeout=_LOCK_TTL)
    if not lock.acquire(blocking=False):
        # Otro bundle del mismo dirigente en curso → backpressure, reintento con backoff.
        session.close()
        raise self.retry(countdown=120 * (self.request.retries + 1))

    try:
        job.status = IngestJobStatus.RUNNING
        job.attempts += 1
        session.commit()

        manifest = job.manifest
        file_names = [f["name"] for f in manifest["files"]]

        with tempfile.TemporaryDirectory(prefix=f"radar-{job.task_uuid}-") as tmp:
            workdir = Path(tmp)
            _download_bundle(manifest["minio_path"], file_names, workdir)

            problems = validate_bundle(workdir, manifest["files"])
            if problems:
                job.status = IngestJobStatus.TAINTED
                job.error = "; ".join(problems)[:2000]
                job.finished_at = datetime.now(UTC)
                session.commit()
                logger.warning("job %d TAINTED: %s", job_id, job.error)
                return {"job_id": job_id, "status": "TAINTED", "problems": problems}

            before = _db_counts(session, job.dirigente_id)
            steps = _run_sop_chain(session, workdir, job.dirigente_id, set(file_names))
            after = _db_counts(session, job.dirigente_id)

        # Contrato D-041: red en depth=posts_only NO trae reactors a propósito —
        # excluirla del gate de cobertura (no es hueco, es configuración RADAR).
        depth = manifest.get("capture_depth") or {}
        posts_only = {p for p, d in depth.items() if d == "posts_only"}
        gaps = [
            g for g in coverage_gaps_sync(session, job.dirigente_id)
            if g["platform"] not in posts_only
        ]
        nlp_queued = _enqueue_local_nlp(session, job.dirigente_id)

        job.counts = {
            "steps": steps,
            "db_delta": {t: after[t] - before[t] for t in after},
            "db_after": after,
            "coverage_gaps": gaps,
            "nlp_local_queued": nlp_queued,
        }
        job.status = IngestJobStatus.PARTIAL if gaps else IngestJobStatus.COMPLETED
        job.finished_at = datetime.now(UTC)
        session.commit()
        logger.info("job %d %s: %s", job_id, job.status.value, job.counts["db_delta"])
        return {"job_id": job_id, "status": job.status.value, "counts": job.counts}

    except Exception as exc:
        session.rollback()
        job = session.get(IngestJob, job_id)
        if job is not None:
            job.status = IngestJobStatus.FAILED
            job.error = str(exc)[:2000]
            job.finished_at = datetime.now(UTC)
            session.commit()
        logger.error("job %d FAILED: %s", job_id, exc)
        raise
    finally:
        try:
            lock.release()
        except Exception:  # lock expiró por TTL — inofensivo
            pass
        session.close()
