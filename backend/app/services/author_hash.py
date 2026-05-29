"""Normalización canónica de author_hash — pseudonimización LFPDPPP.

`social_comments.author_hash` y `watched_profiles.author_hash` deben ser SIEMPRE
un hash (pseudónimo), nunca PII en texto plano. Algunas rutas de ingest (RADAR FB
Playwright) guardaban el nombre crudo cuando no había un author_id estable.

`ensure_author_hash` es el guard defensivo: si el valor ya es hash, lo deja; si es
nombre/PII crudo, lo hashea con el esquema canónico sha256(platform:value:salt) —
el mismo de apify_fb_deep_saymi.py. Determinista: mismo nombre → mismo hash (en
cualquier tabla), preservando el join watched_profiles↔social_comments.
"""
from __future__ import annotations

import hashlib
import os
import re

COMMENT_AUTHOR_SALT = os.environ.get("COMMENT_AUTHOR_SALT", "crece-v2-lfpdppp-salt-2026")

# Un hash válido = solo hex, >=8 chars, sin espacios (alinea con el filtro SQL
# usado para detectar crudos: ~ space OR !~ '^[0-9a-f]{8,}').
_HASH_RE = re.compile(r"^[0-9a-f]{8,}$")


def is_hashed(value: str | None) -> bool:
    if not value:
        return False
    return bool(_HASH_RE.fullmatch(value.strip()))


def ensure_author_hash(
    value: str | None,
    platform: str = "FACEBOOK",
    salt: str = COMMENT_AUTHOR_SALT,
) -> str:
    """Devuelve un author_hash garantizado pseudonimizado (sin PII cruda)."""
    if not value:
        return ""
    v = value.strip()
    if is_hashed(v):
        return v
    return hashlib.sha256(f"{platform}:{v}:{salt}".encode("utf-8")).hexdigest()
