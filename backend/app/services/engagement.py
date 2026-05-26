"""Cálculo canónico de engagement_rate — ÚNICA fuente de verdad.

Toda ruta que persista un post (scrapers ORM vía event listener, scripts de
ingest SQL, backfill) debe usar esta función. No duplicar la fórmula.

Fórmula (consistente con bot_detection.py y los valores históricos verificados):
    - con views (TikTok/YT/Reels):  (likes + comments) / views * 100
    - sin views (X/FB):             (likes + comments + shares) / followers * 100

Notas:
    - Sin interacción (likes+comments+shares == 0) → 0.0 (correcto, no es "sin dato").
    - Sin denominador (views==0 y followers==0) → 0.0 (no calculable).
    - followers es aproximado (followers actuales, no followers_at_post_time, que
      no persistimos históricamente). Misma limitación que el resto del código.
"""
from __future__ import annotations


def compute_engagement_rate(
    likes: int | None,
    comments: int | None,
    shares: int | None,
    views: int | None,
    followers: int | None,
) -> float:
    likes = likes or 0
    comments = comments or 0
    shares = shares or 0
    views = views or 0
    followers = followers or 0

    if (likes + comments + shares) == 0:
        return 0.0
    if views > 0:
        return round((likes + comments) / views * 100.0, 4)
    if followers > 0:
        return round((likes + comments + shares) / followers * 100.0, 4)
    return 0.0
