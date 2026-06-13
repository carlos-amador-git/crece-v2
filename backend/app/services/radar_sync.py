from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.dirigente import Dirigente
from app.models.ingest_job import IngestJob, IngestJobStatus
from app.services.radar_ingest import _count_records

logger = logging.getLogger(__name__)


def get_s3_client():
    # settings.MINIO_ENDPOINT may include 'http://' or not. boto3 expects endpoint_url.
    endpoint = settings.MINIO_ENDPOINT
    if not endpoint.startswith("http"):
        endpoint = f"http://{endpoint}"
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        use_ssl=settings.MINIO_SECURE,
    )


async def get_dirigente_slug(db: AsyncSession, dirigente_id: int) -> str:
    """Obtiene el slug usado para los handoffs de este dirigente."""
    # 1. Buscar en historial de ingest_jobs
    result = await db.execute(
        select(IngestJob.slug)
        .where(IngestJob.dirigente_id == dirigente_id)
        .order_by(desc(IngestJob.created_at))
        .limit(1)
    )
    slug = result.scalar_one_or_none()
    if slug:
        return slug

    # 2. Hardcoded pilot map
    PILOT_MAP = {1: "pina", 3: "saymi", 5: "gaby", 8: "ballesteros", 60: "felipe"}
    if dirigente_id in PILOT_MAP:
        return PILOT_MAP[dirigente_id]

    # 3. Fallback: slugify first name
    dirigente = await db.get(Dirigente, dirigente_id)
    if not dirigente:
        raise ValueError(f"Dirigente {dirigente_id} no existe")

    name = dirigente.full_name.split()[0].lower()
    name = "".join(
        c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^a-z0-9]+", "-", name)


async def find_latest_bundle_info(slug: str) -> dict[str, Any] | None:
    """Busca en MinIO el prefix (task_uuid) más reciente bajo radar-handoffs/{slug}/."""
    s3 = get_s3_client()
    bucket = settings.MINIO_BUCKET
    prefix = f"radar-handoffs/{slug}/"

    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/")

    latest_uuid = None
    latest_ts = None

    for page in pages:
        for prefix_data in page.get("CommonPrefixes", []):
            tuid = prefix_data["Prefix"].rstrip("/").split("/")[-1]
            # Listar un objeto para obtener el LastModified como proxy del bundle
            res = s3.list_objects_v2(Bucket=bucket, Prefix=f"{prefix}{tuid}/", MaxKeys=1)
            if "Contents" in res:
                ts = res["Contents"][0]["LastModified"]
                if latest_ts is None or ts > latest_ts:
                    latest_ts = ts
                    latest_uuid = tuid

    if not latest_uuid:
        return None

    return {"task_uuid": latest_uuid, "timestamp": latest_ts}


async def discover_manifest(slug: str, task_uuid: str, dirigente_id: int) -> dict[str, Any]:
    """Crea un manifest a partir de los archivos reales en MinIO."""
    s3 = get_s3_client()
    bucket = settings.MINIO_BUCKET
    prefix = f"radar-handoffs/{slug}/{task_uuid}/"

    res = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    if "Contents" not in res:
        raise ValueError(f"Bundle {task_uuid} está vacío o no existe")

    files = []
    # Usamos una fecha genérica si no hay manifest.json real
    window = {"from": "2026-01-01T00:00:00Z", "to": datetime.now(UTC).isoformat()}

    for obj in res["Contents"]:
        key = obj["Key"]
        name = key.split("/")[-1]
        if not name or name == "manifest.json":
            continue

        # Para generar sha256 y contar registros, necesitamos el archivo.
        # Es costoso pero es el fallback si no hay manifest POSTed.
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            s3.download_fileobj(bucket, key, tmp)
            tmp_path = Path(tmp.name)
            try:
                sha256 = hashlib.sha256(tmp_path.read_bytes()).hexdigest()
                count = _count_records(tmp_path)
                files.append({"name": name, "sha256": sha256, "record_count": count})
            finally:
                os.unlink(tmp_path)

    return {
        "task_uuid": task_uuid,
        "schema_version": "d041-v1",
        "slug": slug,
        "dirigente_id": dirigente_id,
        "window": window,
        "files": files,
        "minio_path": f"radar-handoffs/{slug}/{task_uuid}",
    }
