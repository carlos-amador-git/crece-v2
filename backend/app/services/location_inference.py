"""Location inference for trend detection (Sprint 4, S4.4a).

Given a social post, infer which CDMX alcaldía it belongs to.

Resolution strategy (ordered by confidence):
    1. Geo coordinates on the post → ST_Contains against `alcaldias_cdmx.geom`
    2. Alcaldía name mention in `content` → match against `alcaldias_cdmx.nombre`
    3. Colonia/landmark mention in `content` → static lookup (seeded)
    4. Bio fallback: same matching but on the account's bio (seed accounts only)

Returns `LocationResult` with `alcaldia_id`, `confidence`, `method`, and
`evidence` for auditability.

S4.4a replaces the original in-memory dict scaffold with a real DB catalog
lookup. S4.4b (future) will add spaCy NER over normalized text. S4.4a.5
adds `normalize_social_text()` preprocessor ahead of that pass.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


@dataclass
class LocationResult:
    alcaldia_id: int | None
    alcaldia_nombre: str | None = None
    confidence: float = 0.0
    method: str = "none"  # "geo_point" | "name_match" | "colonia_match" | "bio_fallback" | "none"
    evidence: list[str] = field(default_factory=list)


# Colonias / puntos de referencia → nombre canónico de la alcaldía.
# Este mapa es estático y pequeño por diseño: solo se usa como señal débil
# cuando no hay match directo del nombre de la alcaldía. Los valores deben
# coincidir con `alcaldias_cdmx.nombre` (case-insensitive).
_COLONIA_TO_ALCALDIA: dict[str, str] = {
    # Cuauhtémoc
    "roma": "Cuauhtémoc",
    "roma norte": "Cuauhtémoc",
    "roma sur": "Cuauhtémoc",
    "condesa": "Cuauhtémoc",
    "juárez": "Cuauhtémoc",
    "centro histórico": "Cuauhtémoc",
    "zócalo": "Cuauhtémoc",
    "doctores": "Cuauhtémoc",
    "santa maría la ribera": "Cuauhtémoc",
    # Benito Juárez
    "del valle": "Benito Juárez",
    "narvarte": "Benito Juárez",
    "nápoles": "Benito Juárez",
    "portales": "Benito Juárez",
    "mixcoac": "Benito Juárez",
    # Miguel Hidalgo
    "polanco": "Miguel Hidalgo",
    "lomas de chapultepec": "Miguel Hidalgo",
    "anzures": "Miguel Hidalgo",
    "tacuba": "Miguel Hidalgo",
    "escandón": "Miguel Hidalgo",
}


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def normalize_social_text(content: str) -> str:
    """S4.4a.5 — limpia texto social antes del NER / name matching.

    - strippea emojis y símbolos unicode no-letra/no-space
    - convierte `@handle` → ` ` (placeholder vacío)
    - expande `#hashtag` → ` hashtag ` (token separado)
    - colapsa whitespace
    - no lowercasea aquí para preservar NER downstream
    """
    if not content:
        return ""
    # Handles: @foo → " "
    t = re.sub(r"@\w+", " ", content)
    # Hashtags: #foo → " foo "
    t = re.sub(r"#(\w+)", r" \1 ", t)
    # URLs
    t = re.sub(r"https?://\S+", " ", t)
    # Keep only letters, numbers, spaces, and common punctuation.
    # `\p{L}` isn't supported in re stdlib; we approximate by filtering chars
    # whose unicode category starts with L (letter), N (number), or Z (space).
    out_chars: list[str] = []
    for ch in t:
        cat = unicodedata.category(ch)
        if cat[0] in ("L", "N", "Z") or ch in ".,;:¿?¡!()-":
            out_chars.append(ch)
        else:
            out_chars.append(" ")
    return re.sub(r"\s+", " ", "".join(out_chars)).strip()


# ── spaCy NER (lazy-loaded) ────────────────────────────────────────────
# BLOCKER: es_core_news_sm (or _md/_lg) is not installed in the Docker
# image. spaCy 3.8.14 is present but `python -m spacy download
# es_core_news_sm` must be added to the Dockerfile. Until then, the NER
# pass is a no-op that logs a one-time warning.

_spacy_nlp = None
_spacy_load_attempted = False


def _get_spacy_nlp():
    """Lazy-load the Spanish spaCy model. Returns None if unavailable."""
    global _spacy_nlp, _spacy_load_attempted
    if _spacy_load_attempted:
        return _spacy_nlp
    _spacy_load_attempted = True
    try:
        import spacy
        # Try models in order of preference
        for model_name in ("es_core_news_md", "es_core_news_sm", "es_core_news_lg"):
            try:
                _spacy_nlp = spacy.load(model_name, disable=["parser", "lemmatizer"])
                logger.info("spaCy NER loaded model: %s", model_name)
                return _spacy_nlp
            except OSError:
                continue
        logger.warning(
            "spaCy NER: no Spanish model found (es_core_news_sm/md/lg). "
            "Install via: python -m spacy download es_core_news_sm. "
            "NER pass will be skipped until model is available."
        )
    except ImportError:
        logger.warning("spaCy not installed — NER pass disabled")
    return None


async def _resolve_by_spacy_ner(
    db: AsyncSession, normalized_text: str
) -> tuple[int, str] | None:
    """Extract GPE/LOC entities via spaCy and match against alcaldias_cdmx."""
    nlp = _get_spacy_nlp()
    if nlp is None:
        return None

    doc = nlp(normalized_text)
    # Collect unique GPE/LOC entity texts
    location_entities: list[str] = []
    for ent in doc.ents:
        if ent.label_ in ("GPE", "LOC") and ent.text.strip():
            location_entities.append(ent.text.strip())

    if not location_entities:
        return None

    # Try matching each entity against alcaldias_cdmx
    result = await db.execute(
        text("SELECT id, nombre FROM alcaldias_cdmx ORDER BY length(nombre) DESC")
    )
    alcaldias = result.all()

    for entity in location_entities:
        folded_entity = _strip_accents(entity.lower())
        for aid, nombre in alcaldias:
            folded_name = _strip_accents(nombre.lower())
            if folded_entity == folded_name or folded_name in folded_entity:
                return (aid, nombre)

    return None


async def _resolve_by_point(
    db: AsyncSession, lat: float, lon: float
) -> tuple[int, str] | None:
    result = await db.execute(
        text(
            "SELECT id, nombre FROM alcaldias_cdmx "
            "WHERE ST_Contains(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)) "
            "LIMIT 1"
        ),
        {"lon": lon, "lat": lat},
    )
    row = result.first()
    return (row[0], row[1]) if row else None


async def _resolve_by_name(
    db: AsyncSession, normalized_text: str
) -> tuple[int, str] | None:
    """Tries to match an alcaldía name inside `normalized_text`.

    Uses accent-insensitive matching: we fold accents on both sides.
    """
    folded_text = _strip_accents(normalized_text.lower())
    result = await db.execute(
        text("SELECT id, nombre FROM alcaldias_cdmx ORDER BY length(nombre) DESC")
    )
    for aid, nombre in result.all():
        folded_name = _strip_accents(nombre.lower())
        if folded_name in folded_text:
            return (aid, nombre)
    return None


async def _resolve_by_colonia(
    db: AsyncSession, normalized_text: str
) -> tuple[int, str] | None:
    folded = _strip_accents(normalized_text.lower())
    # Longest colonia name first to avoid partial shadowing
    for colonia in sorted(_COLONIA_TO_ALCALDIA.keys(), key=len, reverse=True):
        if _strip_accents(colonia) in folded:
            alcaldia_nombre = _COLONIA_TO_ALCALDIA[colonia]
            result = await db.execute(
                text("SELECT id FROM alcaldias_cdmx WHERE nombre = :n"),
                {"n": alcaldia_nombre},
            )
            row = result.first()
            if row:
                return (row[0], alcaldia_nombre)
    return None


async def infer_location(
    db: AsyncSession,
    content: str,
    *,
    lat: float | None = None,
    lon: float | None = None,
    account_bio: str | None = None,
) -> LocationResult:
    """Resolve a post or article to one of the 16 CDMX alcaldías.

    Preference order (highest confidence first):
        - Exact geo coordinates on the post
        - Alcaldía name mentioned in normalized content
        - Colonia / landmark in normalized content
        - Alcaldía name in the account bio (seed accounts only)
    """
    evidence: list[str] = []

    # 1. Point-in-polygon (only if caller passed coords)
    if lat is not None and lon is not None:
        match = await _resolve_by_point(db, lat=lat, lon=lon)
        if match:
            aid, nombre = match
            evidence.append(f"geo_point:({lat:.4f},{lon:.4f})")
            return LocationResult(
                alcaldia_id=aid,
                alcaldia_nombre=nombre,
                confidence=1.0,
                method="geo_point",
                evidence=evidence,
            )

    normalized = normalize_social_text(content or "")

    # 2. Alcaldía name in content
    if normalized:
        match = await _resolve_by_name(db, normalized)
        if match:
            aid, nombre = match
            evidence.append(f"name:{nombre}")
            return LocationResult(
                alcaldia_id=aid,
                alcaldia_nombre=nombre,
                confidence=0.9,
                method="name_match",
                evidence=evidence,
            )

        # 3. Colonia / landmark
        match = await _resolve_by_colonia(db, normalized)
        if match:
            aid, nombre = match
            evidence.append(f"colonia→{nombre}")
            return LocationResult(
                alcaldia_id=aid,
                alcaldia_nombre=nombre,
                confidence=0.75,
                method="colonia_match",
                evidence=evidence,
            )

    # 3b. spaCy NER — extract GPE/LOC entities from normalized text,
    #     match against alcaldias table. Confidence between colonia (0.75)
    #     and name_match (0.9) since NER can be noisy.
    if normalized:
        ner_match = await _resolve_by_spacy_ner(db, normalized)
        if ner_match:
            aid, nombre = ner_match
            evidence.append(f"spacy_ner:{nombre}")
            return LocationResult(
                alcaldia_id=aid,
                alcaldia_nombre=nombre,
                confidence=0.8,
                method="spacy_ner",
                evidence=evidence,
            )

    # 4. Bio fallback (seed accounts only)
    if account_bio:
        bio_normalized = normalize_social_text(account_bio)
        match = await _resolve_by_name(db, bio_normalized)
        if match:
            aid, nombre = match
            evidence.append(f"bio:{nombre}")
            return LocationResult(
                alcaldia_id=aid,
                alcaldia_nombre=nombre,
                confidence=0.5,
                method="bio_fallback",
                evidence=evidence,
            )

    return LocationResult(alcaldia_id=None)
