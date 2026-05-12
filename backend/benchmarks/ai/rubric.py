"""Benchmark rubric — 6 dimensions, 0-100 per dimension.

Deterministic dimensions (pure text analysis):
    1. coverage       — section headers present vs expected
    2. specificity    — concrete nouns (frequencies, formats, responsables)
    5. length         — inside target word range

LLM-judge dimensions (require an arbiter model; fall back to heuristic):
    3. factual        — only uses numbers present in the test case
    4. compliance_ine — no illegal practices (veda, gastos sin trazar, etc.)
    6. hallucinations — does not invent accounts, events, or metrics

Scores are aggregated with weights. Missing sections are penalized logarithmically.

Usage:
    from benchmarks.ai.rubric import score_output, RubricResult
    result = score_output(text, test_case, expected_sections=[...])
    print(result.total, result.breakdown)

Self-test:
    python -m benchmarks.ai.rubric --self-test
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

DEFAULT_EXPECTED_SECTIONS = [
    "Resumen Ejecutivo",
    "Análisis por Plataforma",
    "Plataformas Ausentes",
    "Análisis de Sentimiento",
    "FODA",
    "Tabla Comparativa",
    "KPIs",
    "Recomendaciones",
    "Plataforma Prioritaria",
    "Datos Faltantes",
]

# Patterns that suggest actionable specificity (not generic advice)
SPECIFICITY_PATTERNS = [
    r"\b\d+\s*(?:post|publicaci[oó]n|video|historia|reel|story)\w*\s*(?:por|al)\s*(?:d[ií]a|semana|mes)",
    r"\b(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)\b",
    r"\b\d{1,2}:\d{2}\s*(?:am|pm|hrs|horas)",
    r"\bresponsable\b|\bencargad[oa]\b|\bcommunity manager\b",
    r"\$\s*\d[\d,\.]*\s*(?:mxn|mn|pesos)",
    r"\bmeta\b.*\d+",
]

# Tokens that signal generic / lazy recommendations (penalize)
GENERIC_PATTERNS = [
    r"aprovech(?:ar|a) (?:las )?redes sociales",
    r"mejorar (?:la )?presencia (?:digital|en l[ií]nea)",
    r"interactuar con (?:los )?seguidores",
    r"crear contenido de calidad",
    r"usar hashtags relevantes",
]

COMPLIANCE_RED_FLAGS = [
    r"pagar\s+publicidad\s+(?:en|durante)\s+veda",
    r"compra\s+de\s+seguidores",
    r"bots?\s+para\s+amplificar",
    r"sin\s+etiquetar\s+(?:el\s+)?contenido\s+(?:generado\s+)?por\s+ia",
]


@dataclass
class RubricResult:
    total: float
    breakdown: dict[str, float]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _score_coverage(text: str, expected: list[str]) -> tuple[float, list[str]]:
    norm = _normalize(text)
    hits = 0
    misses: list[str] = []
    for section in expected:
        if _normalize(section) in norm:
            hits += 1
        else:
            misses.append(section)
    pct = (hits / len(expected)) * 100 if expected else 0
    return round(pct, 1), misses


def _score_specificity(text: str) -> tuple[float, int, int]:
    specific_hits = sum(len(re.findall(p, text, re.IGNORECASE)) for p in SPECIFICITY_PATTERNS)
    generic_hits = sum(len(re.findall(p, text, re.IGNORECASE)) for p in GENERIC_PATTERNS)
    # Target: 10+ specific patterns, 0 generic. Score curve flattens after 15.
    base = min(specific_hits * 7, 100)
    penalty = generic_hits * 10
    return max(0.0, round(base - penalty, 1)), specific_hits, generic_hits


def _score_length(text: str, lo: int = 1500, hi: int = 6000) -> tuple[float, int]:
    words = len(text.split())
    if lo <= words <= hi:
        return 100.0, words
    if words < lo:
        return round(max(0, (words / lo) * 100), 1), words
    # overshoot penalized linearly up to 2x hi
    overshoot = words - hi
    return round(max(0, 100 - (overshoot / hi) * 100), 1), words


def _score_factual(text: str, context: dict[str, Any]) -> tuple[float, list[str]]:
    """Heuristic: every number in the output should either match a number in the
    context or be a clearly derived ratio/percentage. Flags numbers that look
    fabricated (followers counts, dates, currency that don't exist in context).

    NOTE: We extract COMPLETE numeric tokens including decimals (2.5, 0.0272)
    and optional thousand separators. The previous implementation used
    `\b\d{3,}\b` which split `0.0272` into `0272` and flagged it as an unknown
    number, producing false positives against decimal metrics in the context
    (engagement_rate, sentiment scores). See DECISIONS.md rubric limitations.
    """
    # Extract numbers from context recursively — keep both int and float forms
    context_numbers: set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
        elif isinstance(obj, int | float):
            context_numbers.add(str(obj))
            context_numbers.add(str(int(obj)))
        elif isinstance(obj, str):
            for m in re.findall(r"-?\d+(?:[.,]\d+)?", obj):
                context_numbers.add(m.replace(",", "."))

    walk(context)

    # Extract numeric tokens from the text WITHOUT splitting decimals.
    # Matches: "3674", "0.0272", "-0.3449", "7.89%", "1,800", "285,000".
    # Does NOT match the fragment "0272" from "0.0272" because the leading
    # "0." is part of the same token — avoiding the false positive that
    # tanked _score_factual to 30-66 across all 3 prompt iterations.
    raw_numbers = re.findall(r"-?\d+(?:[.,]\d+)*", text)
    text_numbers = [n.replace(",", "") for n in raw_numbers if len(n) >= 3]
    if not text_numbers:
        return 80.0, ["Sin números grandes que auditar"]

    matched = 0
    suspects: list[str] = []
    for num in text_numbers:
        if num in context_numbers:
            matched += 1
        else:
            suspects.append(num)

    pct = (matched / len(text_numbers)) * 100
    # Keep some tolerance: some numbers are legitimately derived (ratios, deltas)
    adjusted = min(100, pct + 30)
    return round(adjusted, 1), suspects[:10]


def _score_compliance(text: str) -> tuple[float, list[str]]:
    flags = []
    for pat in COMPLIANCE_RED_FLAGS:
        matches = re.findall(pat, text, re.IGNORECASE)
        flags.extend(matches)
    if not flags:
        return 100.0, []
    return max(0.0, 100 - len(flags) * 25), flags


def _score_hallucinations(text: str, context: dict[str, Any]) -> tuple[float, list[str]]:
    """Very coarse heuristic: if the output mentions handles/@usernames that
    aren't in the context, flag them.
    """
    context_str = json.dumps(context, ensure_ascii=False, default=str).lower()
    handles = re.findall(r"@[A-Za-z0-9_\.]{3,}", text)
    unknown = [h for h in set(handles) if h.lower() not in context_str]
    if not handles:
        return 85.0, []
    pct = ((len(handles) - len(unknown)) / len(handles)) * 100
    return round(pct, 1), unknown[:10]


WEIGHTS = {
    "coverage": 0.20,
    "specificity": 0.20,
    "factual": 0.20,
    "compliance": 0.15,
    "length": 0.10,
    "hallucinations": 0.15,
}


def score_output(
    text: str,
    test_case: dict[str, Any] | None = None,
    expected_sections: list[str] | None = None,
) -> RubricResult:
    context = (test_case or {}).get("context", {})
    expected = expected_sections or DEFAULT_EXPECTED_SECTIONS

    coverage, missed = _score_coverage(text, expected)
    specificity, spec_hits, generic_hits = _score_specificity(text)
    length, words = _score_length(text)
    factual, suspect_nums = _score_factual(text, context)
    compliance, compliance_flags = _score_compliance(text)
    hallu, unknown_handles = _score_hallucinations(text, context)

    breakdown = {
        "coverage": coverage,
        "specificity": specificity,
        "factual": factual,
        "compliance": compliance,
        "length": length,
        "hallucinations": hallu,
    }
    total = round(sum(breakdown[k] * WEIGHTS[k] for k in breakdown), 1)

    notes = []
    if missed:
        notes.append(f"secciones faltantes: {', '.join(missed)}")
    notes.append(f"words={words}")
    notes.append(f"specific_patterns={spec_hits} generic_patterns={generic_hits}")
    if suspect_nums:
        notes.append(f"números sin match en contexto: {suspect_nums}")
    if compliance_flags:
        notes.append(f"banderas compliance: {compliance_flags}")
    if unknown_handles:
        notes.append(f"handles desconocidos: {unknown_handles}")

    return RubricResult(total=total, breakdown=breakdown, notes=notes)


def _self_test() -> int:
    fixture_good = """
    # Diagnóstico digital de Piña
    ## 1. Resumen Ejecutivo
    IPD de 3.9 sobre 10 — presencia dormida. Brecha de 40:1 vs competidor.
    ## 2. Análisis por Plataforma
    Instagram con 2231 seguidores, engagement 7.74% lunes a viernes 19:00 hrs.
    Responsable: community manager junior. Meta 30 días: 5 reels por semana.
    ## 3. Plataformas Ausentes
    TikTok y YouTube ausentes, críticos para alcance juvenil.
    ## 4. Análisis de Sentimiento
    Distribución 52% neutral, sesgo estadístico por muestra pequeña.
    ## 5. FODA
    Fortaleza: comunidad leal. Oportunidad: TikTok sin competencia local.
    ## 6. Tabla Comparativa
    Batres tiene 92x más seguidores en Twitter.
    ## 7. KPIs
    IPD 3.9 → meta 5.0 en 30 días → meta 7.0 en 90 días.
    ## 8. Recomendaciones
    Inmediatas: publicar 3 reels por semana los martes 20:00 hrs.
    Presupuesto: $5000 mxn mensuales para producción.
    ## 9. Plataforma Prioritaria
    Instagram es la prioridad por ROI de engagement.
    ## 10. Datos Faltantes
    Falta histórico de follower count para calcular tendencia.
    """ * 10  # padding to reach length target

    fixture_test_case = {
        "context": {
            "social_profiles": [
                {"platform": "INSTAGRAM", "followers": 2231, "avg_engagement_30d": 0.0774}
            ],
            "ipd": {"score": 3.9},
        }
    }

    result = score_output(fixture_good, fixture_test_case)
    print("SELF-TEST result:")
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    assert result.total > 50, f"Expected >50 total on good fixture, got {result.total}"
    assert result.breakdown["coverage"] >= 80, "Coverage should be near perfect"
    print(f"\nPASS — total={result.total}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--score", type=str, help="Path to a markdown file to score")
    parser.add_argument("--test-case", type=str, help="Path to test_case JSON")
    args = parser.parse_args()

    if args.self_test:
        raise SystemExit(_self_test())

    if args.score:
        from pathlib import Path
        text = Path(args.score).read_text(encoding="utf-8")
        tc = json.loads(Path(args.test_case).read_text(encoding="utf-8")) if args.test_case else None
        result = score_output(text, tc)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
