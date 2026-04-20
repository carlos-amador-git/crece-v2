"""Diagnóstico Tier 2 Diferenciadores Defensibles (Sprint S3 · MASTER §3.2).

8 killer features que separan CRECE v2 de Brandwatch/Meltwater/Sprout Social.

    - B11 cross_partisan_service   — Cross-Partisan Validation Score
    - B12 cib_detector_service     — CIB Detector multinivel (ITESO/DFRLab)
    - B13 filtro_realidad_service  — ER orgánico sin CIB
    - B14 topic_drift_service      — Caption vs comments divergencia
    - B15 rage_click_service       — Outrage engagement detection
    - B16 promesas_service         — Rastreador Promesas Campaña
    - B17 veda_compliance_service  — Veda INE heurístico
    - B18 violencia_politica_service — Hate speech / VPG / amenazas

Contract:
    async def compute(db, dirigente_id, org_id=None, **kwargs) -> dict

Return shape (como tier1 pero ``bloque_version: "tier2-v1"``).
"""
from __future__ import annotations

from app.services.diagnostico_tier2 import (
    cib_detector_service,
    cross_partisan_service,
    filtro_realidad_service,
    promesas_service,
    rage_click_service,
    topic_drift_service,
    veda_compliance_service,
    violencia_politica_service,
)

__all__ = [
    "cib_detector_service",
    "cross_partisan_service",
    "filtro_realidad_service",
    "promesas_service",
    "rage_click_service",
    "topic_drift_service",
    "veda_compliance_service",
    "violencia_politica_service",
]
