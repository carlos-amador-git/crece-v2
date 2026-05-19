"""Add media_urls jsonb to social_posts

Permite renderizar thumbnails de imágenes/videos en PostCard frontend.
Array de URLs: media_urls[0] usado como miniatura principal.

Revision ID: spm_media1
Revises: rec_platdest1
Create Date: 2026-05-12

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "spm_media1"
down_revision = "rec_platdest1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "social_posts",
        sa.Column(
            "media_urls",
            JSONB,
            nullable=True,
            comment="Array de URLs de media (imágenes/videos) del post. media_urls[0] usado como thumbnail.",
        ),
    )
    # Backfill desde raw_data si tiene campos comunes de scrapers (Instagram/Facebook/X).
    # Cubre claves: display_url, image, image_url, thumbnail, media (lista), media_url.
    op.execute(
        """
        UPDATE social_posts
        SET media_urls = (
          CASE
            WHEN jsonb_typeof(raw_data->'media_urls') = 'array' THEN raw_data->'media_urls'
            WHEN jsonb_typeof(raw_data->'media') = 'array' THEN raw_data->'media'
            WHEN raw_data->>'display_url' IS NOT NULL THEN jsonb_build_array(raw_data->>'display_url')
            WHEN raw_data->>'image_url' IS NOT NULL THEN jsonb_build_array(raw_data->>'image_url')
            WHEN raw_data->>'image' IS NOT NULL THEN jsonb_build_array(raw_data->>'image')
            WHEN raw_data->>'thumbnail' IS NOT NULL THEN jsonb_build_array(raw_data->>'thumbnail')
            WHEN raw_data->>'media_url' IS NOT NULL THEN jsonb_build_array(raw_data->>'media_url')
            ELSE NULL
          END
        )
        WHERE raw_data IS NOT NULL
          AND media_urls IS NULL;
        """
    )


def downgrade() -> None:
    op.drop_column("social_posts", "media_urls")
