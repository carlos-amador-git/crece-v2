"""Cliente E2E de push de handoff RADAR→CRECE (Sprint 0 · PLAN-2026-06-11).

Simula el lado RADAR del contrato (referencia para su D-050): sube el bundle a
MinIO + POSTea el manifest + pollea el job. Corre desde HOST (boto3 + httpx/requests).

Uso:
  python scripts/e2e_push_handoff.py --slug felipe --dirigente-id 60 \
      --reactors /path/felipe-reactors-v2-20260612.json \
      --api-key $KEY [--api http://localhost:8002] [--minio localhost:9006]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path

import boto3
import requests


def _count_records(path: Path) -> int:
    data = json.loads(path.read_text())
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        for key in ("reactors", "posts", "comments"):
            if isinstance(data.get(key), list):
                return len(data[key])
        return len(data)
    raise ValueError(f"shape no reconocido: {path}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--dirigente-id", type=int, required=True)
    ap.add_argument("--reactors", type=Path, required=True)
    ap.add_argument("--api", default="http://localhost:8002")
    ap.add_argument("--minio", default="localhost:9006")
    ap.add_argument("--api-key", default=os.environ.get("CRECE_API_KEY", ""))
    ap.add_argument("--task-uuid", default=None, help="reusar uuid (test idempotencia)")
    ap.add_argument("--poll", type=int, default=600, help="segundos máx de polling")
    args = ap.parse_args()

    if not args.api_key:
        print("falta --api-key o CRECE_API_KEY")
        return 2

    task_uuid = args.task_uuid or uuid.uuid4().hex
    prefix = f"radar-handoffs/{args.slug}/{task_uuid}"

    # 1. Subir bundle a MinIO
    s3 = boto3.client(
        "s3",
        endpoint_url=f"http://{args.minio}",
        aws_access_key_id=os.environ.get("MINIO_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.environ.get("MINIO_SECRET_KEY", "minioadmin"),
    )
    bucket = os.environ.get("MINIO_BUCKET", "crece-v2")
    try:
        s3.head_bucket(Bucket=bucket)
    except Exception:
        s3.create_bucket(Bucket=bucket)
    s3.upload_file(str(args.reactors), bucket, f"{prefix}/reactors.json")
    print(f"[1/3] bundle subido → s3://{bucket}/{prefix}/reactors.json")

    # 2. POST manifest
    manifest = {
        "task_uuid": task_uuid,
        "schema_version": "d041-v1",
        "slug": args.slug,
        "dirigente_id": args.dirigente_id,
        "window": {"from": "2026-04-01T00:00:00Z", "to": "2026-06-12T00:00:00Z"},
        "files": [
            {
                "name": "reactors.json",
                "sha256": hashlib.sha256(args.reactors.read_bytes()).hexdigest(),
                "record_count": _count_records(args.reactors),
            }
        ],
        "minio_path": prefix,
    }
    r = requests.post(
        f"{args.api}/api/v1/ingest/radar-handoff",
        json=manifest,
        headers={"X-API-Key": args.api_key},
        timeout=30,
    )
    print(f"[2/3] POST manifest → {r.status_code}: {r.text[:300]}")
    if r.status_code != 202:
        return 1
    job_id = r.json()["id"]

    # 3. Poll
    t0 = time.time()
    while time.time() - t0 < args.poll:
        time.sleep(10)
        jr = requests.get(
            f"{args.api}/api/v1/ingest/jobs/{job_id}",
            headers={"X-API-Key": args.api_key},
            timeout=30,
        ).json()
        status = jr["status"]
        print(f"    job {job_id}: {status} ({int(time.time() - t0)}s)")
        if status in ("COMPLETED", "PARTIAL", "TAINTED", "FAILED"):
            print(f"[3/3] final: {status}")
            print(json.dumps(jr.get("counts"), indent=2, default=str))
            if jr.get("error"):
                print("error:", jr["error"])
            return 0 if status in ("COMPLETED", "PARTIAL") else 1
    print("timeout de polling")
    return 1


if __name__ == "__main__":
    sys.exit(main())
