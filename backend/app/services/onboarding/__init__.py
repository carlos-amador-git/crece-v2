"""Servicios del Onboarding Wizard (Sprint S5).

Módulos:
    profile_service       — §1.5 detección de perfil (4 opciones)
    accounts_service      — §2 input manual URLs · normalización de handles
    serp_service          — §3 SERP asistido opcional (Apify + Brightdata)
    validator_service     — §4 validación profiles + score de confianza
    oauth_service         — §6 OAuth stubs (Meta/TikTok/YouTube)
    competidores_service  — §7 seed competidores (D-22)
    promesas_service      — §8 seed promesas (D-17)
    activation_service    — §9 activación final + trigger Celery scrape_all_profiles
"""
from __future__ import annotations
