from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# Versiones de shape de export RADAR que esta versión de CRECE sabe ingerir.
# Si RADAR manda otra → rechazo limpio ANTES de tocar BD (contrato PLAN-2026-06-11).
SUPPORTED_SCHEMA_VERSIONS = {"d041-v1"}

# Archivos válidos en un bundle per-plataforma (contrato canónico D-041 / SOP).
KNOWN_BUNDLE_FILES = {
    "x_posts.json",
    "yt_posts.json",
    "tt_posts.json",
    "fb_posts.json",
    "ig_posts.json",
    "fb_comments.json",
    "ig_comments.json",
    "reactors.json",
    "followers.json",
}


class ManifestFile(BaseModel):
    name: str
    sha256: str = Field(min_length=64, max_length=64)
    record_count: int = Field(ge=0)

    @field_validator("name")
    @classmethod
    def name_known(cls, v: str) -> str:
        if v not in KNOWN_BUNDLE_FILES:
            raise ValueError(f"archivo desconocido en bundle: {v}")
        return v


class ManifestWindow(BaseModel):
    from_: datetime = Field(alias="from")
    to: datetime

    model_config = {"populate_by_name": True}


class RadarManifest(BaseModel):
    """Manifest del handoff RADAR→CRECE (PLAN-2026-06-11 §3)."""

    task_uuid: str = Field(min_length=8, max_length=64)
    schema_version: str
    slug: str = Field(min_length=1, max_length=100)
    dirigente_id: int = Field(gt=0)
    window: ManifestWindow
    files: list[ManifestFile] = Field(min_length=1)
    minio_path: str = Field(min_length=1)

    # Heads-up RADAR 2026-06-12: una red capturada con depth=posts_only NO trae
    # comments/reactors en el export — el gate de cobertura NO debe leerlo como gap.
    # Opcional: {"FACEBOOK": "full", "INSTAGRAM": "posts_only", ...}
    capture_depth: dict[str, str] | None = None

    @field_validator("schema_version")
    @classmethod
    def version_supported(cls, v: str) -> str:
        if v not in SUPPORTED_SCHEMA_VERSIONS:
            raise ValueError(
                f"schema_version '{v}' no soportada; soportadas: {sorted(SUPPORTED_SCHEMA_VERSIONS)}"
            )
        return v


class IngestJobResponse(BaseModel):
    id: int
    task_uuid: str
    status: str
    slug: str
    dirigente_id: int
    counts: dict | None = None
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}


class WatermarkResponse(BaseModel):
    """Último timestamp ingerido por plataforma — RADAR exporta solo lo posterior."""

    dirigente_id: int
    posts: dict[str, datetime | None]
    comments: dict[str, datetime | None]
