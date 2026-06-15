"""Cliente E2E de push de handoff RADAR→CRECE (Sprint 0 · PLAN-2026-06-11).

Simula el lado RADAR del contrato (referencia para su D-050): sube el bundle a
MinIO + POSTea el manifest + pollea el job. Corre desde HOST (boto3 + requests).

Dos modos:
  A) reactors-only (legacy):
     python scripts/e2e_push_handoff.py --slug felipe --dirigente-id 60 \
         --reactors /path/felipe-reactors-v2-20260612.json --api-key $KEY

  B) bundle completo per-plataforma (followers→posts→comments→reactors):
     python scripts/e2e_push_handoff.py --slug saymi --dirigente-id 3 \
         --bundle-dir /path/crece_perplatform_.../saymi-.../ \
         --followers /path/saymi-followers-20260612.json \
         --reactors  /path/saymi-reactors-v2-20260612.json --api-key $KEY

El worker corre cada archivo presente en orden SOP. record_count se calcula con
la MISMA _count_records del servicio (validación self-consistente).
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

# Nombres canónicos que el worker sabe ingerir (espejo de schemas.ingest.KNOWN_BUNDLE_FILES).
KNOWN = {
    "x_posts.json", "yt_posts.json", "tt_posts.json", "fb_posts.json", "ig_posts.json",
    "fb_comments.json", "ig_comments.json", "reactors.json", "followers.json",
}


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


def collect_files(args) -> dict[str, Path]:
    """nombre_canónico → ruta local. Bundle-dir primero, luego overrides de raíz."""
    files: dict[str, Path] = {}
    if args.bundle_dir:
        bd = Path(args.bundle_dir)
        for f in sorted(bd.iterdir()):
            if f.name in KNOWN and f.is_file():
                files[f.name] = f
    # followers/reactors de raíz sobrescriben (son los frescos)
    if args.followers:
        files["followers.json"] = Path(args.followers)
    if args.reactors:
        files["reactors.json"] = Path(args.reactors)
    return files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--dirigente-id", type=int, required=True)
    ap.add_argument("--bundle-dir", default=None, help="subdir per-plataforma (posts+comments)")
    ap.add_argument("--followers", default=None, help="followers.json fresco (raíz)")
    ap.add_argument("--reactors", default=None, help="reactors-v2.json (raíz) → reactors.json")
    ap.add_argument("--api", default="http://localhost:8002")
    ap.add_argument("--minio", default="localhost:9006")
    ap.add_argument("--api-key", default=os.environ.get("CRECE_API_KEY", ""))
    ap.add_argument("--task-uuid", default=None, help="reusar uuid (test idempotencia)")
    ap.add_argument("--poll", type=int, default=900)
    ap.add_argument("--upload-only", action="store_true",
                    help="sube el bundle a MinIO + manifest.json y SALE (sin POST). "
                         "Para que el botón 'Sincronizar' lo descubra e ingiera.")
    args = ap.parse_args()

    if not args.api_key:
        print("falta --api-key o CRECE_API_KEY")
        return 2

    files = collect_files(args)
    if not files:
        print("sin archivos: pasa --bundle-dir y/o --followers/--reactors")
        return 2
    print(f"archivos a empujar ({len(files)}): {sorted(files)}")

    task_uuid = args.task_uuid or uuid.uuid4().hex
    prefix = f"radar-handoffs/{args.slug}/{task_uuid}"

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

    manifest_files = []
    for name, path in files.items():
        s3.upload_file(str(path), bucket, f"{prefix}/{name}")
        manifest_files.append({
            "name": name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "record_count": _count_records(path),
        })
    print(f"[1/3] {len(manifest_files)} archivos → s3://{bucket}/{prefix}/")

    manifest = {
        "task_uuid": task_uuid,
        "schema_version": "d041-v1",
        "slug": args.slug,
        "dirigente_id": args.dirigente_id,
        "window": {"from": "2026-04-01T00:00:00Z", "to": "2026-06-13T00:00:00Z"},
        "files": manifest_files,
        "minio_path": prefix,
    }
    # manifest.json al prefix (discover_manifest del endpoint sync lo usa/valida)
    s3.put_object(Bucket=bucket, Key=f"{prefix}/manifest.json", Body=json.dumps(manifest).encode())

    if args.upload_only:
        print(f"[upload-only] bundle + manifest en s3://{bucket}/{prefix}/ — NO ingerido.")
        print(f"  → el botón 'Sincronizar con RADAR' del dirigente {args.dirigente_id} lo descubrirá.")
        return 0

    r = requests.post(
        f"{args.api}/api/v1/ingest/radar-handoff",
        json=manifest, headers={"X-API-Key": args.api_key}, timeout=30,
    )
    print(f"[2/3] POST manifest → {r.status_code}: {r.text[:300]}")
    if r.status_code != 202:
        return 1
    job_id = r.json()["id"]

    t0 = time.time()
    while time.time() - t0 < args.poll:
        time.sleep(10)
        jr = requests.get(
            f"{args.api}/api/v1/ingest/jobs/{job_id}",
            headers={"X-API-Key": args.api_key}, timeout=30,
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
