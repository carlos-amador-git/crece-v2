"""Location inference for trend detection (Sprint 4 scaffold).

Given a social post or news article, infer which alcaldía CDMX it belongs to.

Pipeline:
    1. spaCy NER over `content` → extract GPE (geopolitical) and LOC (location) entities
    2. Match entities against INEGI catalog of places (alcaldías + colonias)
    3. Fallback: use the declared location in the seed account's bio
    4. Return alcaldia_id or None

Precision target (MVP): 60-70%. Posts with no match are labeled as "nacional".

NOTE: This is a scaffold. Real implementation needs:
    - INEGI MGN shapefile loaded into `alcaldias_cdmx` table (S4.1)
    - spaCy `es_core_news_md` model available
    - Seed accounts YAML loaded (S4.3)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LocationResult:
    alcaldia_id: int | None
    confidence: float  # 0.0 - 1.0
    method: str  # "ner_match" | "bio_fallback" | "none"
    evidence: list[str]


# Placeholder catalog. Real implementation loads from DB.
_ALCALDIAS_CDMX_PILOTO: dict[str, int] = {
    "cuauhtémoc": 1,
    "cuauhtemoc": 1,
    "benito juárez": 2,
    "benito juarez": 2,
    "miguel hidalgo": 3,
}

# Colonias de referencia por alcaldía (muy parcial, scaffold)
_COLONIAS_PILOTO: dict[str, int] = {
    "roma": 1,
    "condesa": 1,
    "juárez": 1,
    "centro histórico": 1,
    "del valle": 2,
    "narvarte": 2,
    "polanco": 3,
    "lomas de chapultepec": 3,
}


def infer_location(
    content: str,
    account_bio: str | None = None,
) -> LocationResult:
    """Try to infer which alcaldía a post belongs to."""
    if not content:
        return LocationResult(None, 0.0, "none", [])

    text = content.lower()
    evidence: list[str] = []

    # Pass 1: alcaldía names
    for key, aid in _ALCALDIAS_CDMX_PILOTO.items():
        if key in text:
            evidence.append(f"alcaldia:{key}")
            return LocationResult(aid, 0.9, "ner_match", evidence)

    # Pass 2: colonias
    for key, aid in _COLONIAS_PILOTO.items():
        if key in text:
            evidence.append(f"colonia:{key}")
            return LocationResult(aid, 0.75, "ner_match", evidence)

    # Pass 3: bio fallback (only for seed accounts)
    if account_bio:
        bio_lower = account_bio.lower()
        for key, aid in _ALCALDIAS_CDMX_PILOTO.items():
            if key in bio_lower:
                evidence.append(f"bio:{key}")
                return LocationResult(aid, 0.5, "bio_fallback", evidence)

    return LocationResult(None, 0.0, "none", [])


# TODO(S4): replace with actual spaCy + DB catalog
# async def infer_with_spacy(text: str, db: AsyncSession) -> LocationResult: ...
