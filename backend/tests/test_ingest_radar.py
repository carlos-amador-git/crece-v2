"""Tests del contrato de handoff RADAR→CRECE (PLAN-2026-06-11).

Unitarios puros: validación de manifest (Pydantic) y de bundle (sha256 +
record_count). El E2E con DB/Celery corre aparte con stack arriba.
"""

from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from app.schemas.ingest import RadarManifest
from app.services.radar_ingest import _count_records, validate_bundle


def _manifest_dict(**overrides) -> dict:
    base = {
        "task_uuid": "a" * 32,
        "schema_version": "d041-v1",
        "slug": "saymi",
        "dirigente_id": 3,
        "window": {"from": "2026-06-01T00:00:00Z", "to": "2026-06-11T00:00:00Z"},
        "files": [
            {"name": "fb_posts.json", "sha256": "b" * 64, "record_count": 10},
        ],
        "minio_path": "radar-handoffs/saymi/abc123/",
    }
    base.update(overrides)
    return base


class TestRadarManifest:
    def test_valido(self):
        m = RadarManifest(**_manifest_dict())
        assert m.task_uuid == "a" * 32
        assert m.files[0].record_count == 10

    def test_schema_version_no_soportada(self):
        with pytest.raises(ValidationError, match="no soportada"):
            RadarManifest(**_manifest_dict(schema_version="d041-v99"))

    def test_archivo_desconocido(self):
        with pytest.raises(ValidationError, match="desconocido"):
            RadarManifest(
                **_manifest_dict(
                    files=[{"name": "evil.json", "sha256": "b" * 64, "record_count": 1}]
                )
            )

    def test_files_vacio(self):
        with pytest.raises(ValidationError):
            RadarManifest(**_manifest_dict(files=[]))

    def test_record_count_negativo(self):
        with pytest.raises(ValidationError):
            RadarManifest(
                **_manifest_dict(
                    files=[{"name": "fb_posts.json", "sha256": "b" * 64, "record_count": -1}]
                )
            )


class TestCountRecords:
    def test_lista_plana(self, tmp_path):
        f = tmp_path / "ig_posts.json"
        f.write_text(json.dumps([{"a": 1}, {"a": 2}]))
        assert _count_records(f) == 2

    def test_envelope_reactors(self, tmp_path):
        f = tmp_path / "reactors.json"
        f.write_text(json.dumps({"export_meta": {}, "reactors": [1, 2, 3]}))
        assert _count_records(f) == 3

    def test_followers_dict(self, tmp_path):
        f = tmp_path / "followers.json"
        f.write_text(json.dumps({"FACEBOOK": 1000, "INSTAGRAM": 500}))
        assert _count_records(f) == 2


class TestValidateBundle:
    def _write(self, tmp_path, name: str, data) -> dict:
        f = tmp_path / name
        f.write_text(json.dumps(data))
        return {
            "name": name,
            "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
            "record_count": len(data),
        }

    def test_bundle_limpio(self, tmp_path):
        mf = self._write(tmp_path, "fb_posts.json", [{"p": 1}, {"p": 2}])
        assert validate_bundle(tmp_path, [mf]) == []

    def test_archivo_faltante(self, tmp_path):
        problems = validate_bundle(
            tmp_path, [{"name": "fb_posts.json", "sha256": "b" * 64, "record_count": 1}]
        )
        assert problems == ["fb_posts.json: falta en bundle"]

    def test_sha256_no_cuadra(self, tmp_path):
        mf = self._write(tmp_path, "fb_posts.json", [{"p": 1}])
        mf["sha256"] = "0" * 64
        problems = validate_bundle(tmp_path, [mf])
        assert problems == ["fb_posts.json: sha256 no cuadra"]

    def test_record_count_miente(self, tmp_path):
        mf = self._write(tmp_path, "fb_posts.json", [{"p": 1}, {"p": 2}])
        mf["record_count"] = 99  # manifest miente → Tainted
        problems = validate_bundle(tmp_path, [mf])
        assert "record_count manifest=99 real=2" in problems[0]
