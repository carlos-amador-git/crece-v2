"""Matriz v3 mapper · runner Gemma → schema matriz v2.

Resuelve el gap de vocabulario detectado en triangulación 2026-04-18:
- Runner Gemma usa: tono ∈ {elogio, critica, pregunta, ataque, informativo,
  personal, autopromocion} · target ∈ {dirigente_post, gobierno, oposicion,
  ciudadania, institucion, otros}
- Matriz v2 usa: tono ∈ {critico, propositivo, celebratorio, informativo,
  solidario, ataque, personal} · target ∈ {gobierno, oposicion, ciudadania,
  medios, autopromocion, tema_especifico, dirigente}

El mapper traduce runner → v2 vocab para que `political_framework.get_political_score()`
encuentre el score correcto.

Decisiones CEO 2026-05-08 (DECISIONES-CEO-2026-05-08.md):
- Opción C: mapper intermedio (no toca producción ni schema BD)
- Ajustes Gemini integrados:
  - G1 (R5): pregunta → informativo default · → critico solo con hostility flag
  - G2 (R3): autopromocion runtime — detección antes de LLM (no aquí, en runner)
  - G3 (R7): mapping_version='v3.0.0' añadido al output
  - G4 (R2): emoji-breve → solo si target=dirigente
  - G5 (R8): counter mapper_fallback_rate

Versión: v3.0.1 · 2026-05-09 — passthrough vocab v2 directo del runner

v3.0.1 (2026-05-09):
- BD inspection mostró que el runner Gemma ya está populando social_comments con
  vocab v2 directo (celebratorio/propositivo/critico/solidario · autopromocion)
  mezclado con vocab runner antiguo (elogio/critica/...).
- Añadidos passthroughs para que el mapper sea idempotente cuando el input ya
  está en v2: celebratorio→celebratorio, critico→critico, etc.
- Añadido autopromocion → autopromocion en TARGET_MAPPING.
- Sin esto, 77/100 rows del ground truth caían a fallback `tema_especifico` y
  `personal` por estar en vocab v2 que el mapper no reconocía.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Literal

log = logging.getLogger("matriz_v3_mapper")

MAPPER_VERSION = "v3.0.1"

# ============================================================================
# TONO_MAPPING runner → v2
# ============================================================================
# Vocab v2: critico · propositivo · celebratorio · informativo · solidario · ataque · personal
# Vocab runner: elogio · critica · pregunta · ataque · informativo · personal · autopromocion
TONO_MAPPING_BASE: dict[str, str] = {
    # ── runner vocab (clásico) → v2 ──
    "elogio": "celebratorio",       # elogio runner ≈ celebratorio v2
    "critica": "critico",            # critica runner ≈ critico v2
    "ataque": "ataque",              # idénticos
    "informativo": "informativo",    # idénticos
    "personal": "personal",          # idénticos
    # ── passthrough v2 directo (v3.0.1: runner Gemma ya usa estos labels) ──
    "celebratorio": "celebratorio",
    "propositivo": "propositivo",
    "critico": "critico",
    "solidario": "solidario",
    # "pregunta" → handled dinámicamente con hostility flag (G1)
    # "autopromocion" → mapeado a celebratorio + flag (G2/G3)
}

# ============================================================================
# TARGET_MAPPING runner → v2
# ============================================================================
TARGET_MAPPING: dict[str, str] = {
    "dirigente_post": "dirigente",
    "gobierno": "gobierno",
    "oposicion": "oposicion",
    "ciudadania": "ciudadania",
    "institucion": "tema_especifico",  # institución ≈ tema (no hay match exacto)
    "otros": "tema_especifico",
    # ── passthrough v2 directo (v3.0.1: runner Gemma ya etiqueta autopromocion) ──
    "autopromocion": "autopromocion",
    "medios": "medios",
    "tema_especifico": "tema_especifico",
    "dirigente": "dirigente",
}

# ============================================================================
# Hostility detection (G1 — R5)
# ============================================================================
# Para tono=pregunta: si contiene tokens hostiles → critico, sino → informativo
HOSTILITY_TOKENS = re.compile(
    r"\b(?:por\s+qu[eé]|c[oó]mo\s+puede|hasta\s+cu[aá]ndo|"
    r"verg[uü]enza|miente|miente[ns]|robo|fraud|corrupt|"
    r"renuncia|c[aá]rcel|qu[eé]\s+esperan|para\s+qu[eé]|"
    r"a\s+qui[eé]n\s+enga[ñn]a|qu[eé]\s+vergüenza)\b",
    re.I,
)

# ============================================================================
# Emoji-breve detection (G4 — R2)
# ============================================================================
# Comments cortos con ≥2 emojis → afirmativo_breve (mapped to celebratorio en v2)
# Solo si target=dirigente
# Pictographic codepoints. Excluye variation selectors (FE0F) y zero-width joiners
# para que "❤️" (U+2764 U+FE0F) cuente como UN emoji, no dos.
EMOJI_RE = re.compile(
    r"[\U0001F300-\U0001F6FF\U0001F900-\U0001F9FF\U00002600-\U000027BF"
    r"\U0001FA00-\U0001FA6F\U0001F100-\U0001F1FF]"
)


@dataclass
class MapperResult:
    """Output del mapper con metadata para audit + debugging."""

    tono_v2: str
    target_v2: str
    mapping_version: str = MAPPER_VERSION
    flags: dict = field(default_factory=dict)
    fallback: bool = False  # True si tuvimos que aplicar default genérico


# Stats counter (G5 — R8)
class MapperStats:
    total = 0
    fallbacks = 0
    autopromo_runtime = 0
    pregunta_to_critico = 0
    pregunta_to_informativo = 0
    emoji_breve = 0

    @classmethod
    def fallback_rate(cls) -> float:
        return cls.fallbacks / cls.total if cls.total else 0.0

    @classmethod
    def reset(cls) -> None:
        cls.total = 0
        cls.fallbacks = 0
        cls.autopromo_runtime = 0
        cls.pregunta_to_critico = 0
        cls.pregunta_to_informativo = 0
        cls.emoji_breve = 0

    @classmethod
    def snapshot(cls) -> dict:
        return {
            "total": cls.total,
            "fallbacks": cls.fallbacks,
            "fallback_rate": cls.fallback_rate(),
            "autopromo_runtime": cls.autopromo_runtime,
            "pregunta_to_critico": cls.pregunta_to_critico,
            "pregunta_to_informativo": cls.pregunta_to_informativo,
            "emoji_breve": cls.emoji_breve,
        }


def map_runner_to_v2(
    tono_runner: str,
    target_runner: str,
    *,
    comment_text: str = "",
    is_self_authored: bool = False,
) -> MapperResult:
    """Traduce output del runner Gemma al vocab matriz v2.

    Args:
        tono_runner: tono crudo del runner (1 de 7 valores)
        target_runner: target crudo del runner (1 de 6 valores)
        comment_text: texto del comment (opcional, usado para emoji-breve detection)
        is_self_authored: True si author == handle_dirigente (R3 — G2)

    Returns:
        MapperResult con tono_v2, target_v2, flags, mapping_version
    """
    MapperStats.total += 1
    flags: dict = {}
    fallback = False

    # ── R3 (G2): autopromoción runtime ──────────────────────────────────
    # Si is_self_authored, override label antes de mapear
    if is_self_authored:
        MapperStats.autopromo_runtime += 1
        flags["autopromo_runtime"] = True
        return MapperResult(
            tono_v2="celebratorio",  # autopromoción ≈ celebratorio en v2
            target_v2="autopromocion",
            flags=flags,
        )

    # ── tono especial: autopromocion del runner ─────────────────────────
    if tono_runner == "autopromocion":
        flags["from_runner_autopromocion"] = True
        return MapperResult(
            tono_v2="celebratorio",
            target_v2="autopromocion",
            flags=flags,
        )

    # ── tono especial: pregunta (G1 — R5) ───────────────────────────────
    if tono_runner == "pregunta":
        if HOSTILITY_TOKENS.search(comment_text):
            tono_v2 = "critico"
            flags["pregunta_hostility_detected"] = True
            MapperStats.pregunta_to_critico += 1
        else:
            tono_v2 = "informativo"
            flags["pregunta_default"] = True
            MapperStats.pregunta_to_informativo += 1
        target_v2 = TARGET_MAPPING.get(target_runner, "tema_especifico")
        return MapperResult(tono_v2=tono_v2, target_v2=target_v2, flags=flags)

    # ── tono base mapping ──────────────────────────────────────────────
    tono_v2 = TONO_MAPPING_BASE.get(tono_runner)
    if tono_v2 is None:
        # Fallback: tono desconocido → personal (neutro)
        log.warning("Tono runner desconocido: %r — fallback a 'personal'", tono_runner)
        tono_v2 = "personal"
        fallback = True
        flags["tono_fallback_from"] = tono_runner

    # ── target mapping ─────────────────────────────────────────────────
    target_v2 = TARGET_MAPPING.get(target_runner)
    if target_v2 is None:
        log.warning("Target runner desconocido: %r — fallback a 'tema_especifico'", target_runner)
        target_v2 = "tema_especifico"
        fallback = True
        flags["target_fallback_from"] = target_runner

    # ── R2 (G4): emoji-breve solo si target=dirigente ──────────────────
    # Si comment es <30 chars + ≥2 emojis + target_v2='dirigente' + tono no-negativo,
    # promote a celebratorio (afirmativo_breve)
    if (
        comment_text
        and len(comment_text) < 30
        and target_v2 == "dirigente"
        and tono_v2 in ("personal", "informativo")
    ):
        emoji_count = len(EMOJI_RE.findall(comment_text))
        if emoji_count >= 2:
            tono_v2 = "celebratorio"
            flags["emoji_breve_promotion"] = True
            MapperStats.emoji_breve += 1

    if fallback:
        MapperStats.fallbacks += 1

    return MapperResult(tono_v2=tono_v2, target_v2=target_v2, flags=flags, fallback=fallback)


# ============================================================================
# Public API
# ============================================================================

def get_v2_label(
    tono_runner: str,
    target_runner: str,
    *,
    comment_text: str = "",
    is_self_authored: bool = False,
) -> tuple[str, str]:
    """Helper simple: retorna (tono_v2, target_v2) sin metadata."""
    res = map_runner_to_v2(
        tono_runner, target_runner,
        comment_text=comment_text, is_self_authored=is_self_authored,
    )
    return res.tono_v2, res.target_v2
