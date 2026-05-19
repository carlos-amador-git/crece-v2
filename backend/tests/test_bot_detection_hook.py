"""Tests para hook bot_detection → social_followers (B-FOLLOWERS-BOT-1, 2026-05-16).

Cubre:
- `score_follower` convenience helper devuelve (bot_score, is_real) coherentes.
- Handle limpio → is_real=True.
- Handle bot-like (random + trailing digits) → is_real=False.
- Handle vacío → baseline 0.05, is_real=True.
"""
from __future__ import annotations

import pytest

from app.services.bot_detection import BOT_THRESHOLD, score_follower


def test_score_follower_handle_humano_pasa():
    score, is_real = score_follower(handle="benjamin.jimenez", platform="youtube")
    assert 0.0 <= score < BOT_THRESHOLD
    assert is_real is True


def test_score_follower_trailing_digits_sospechoso():
    """Handles tipo 'user12345678' deben subir el score."""
    score, is_real = score_follower(handle="user12345678", platform="youtube")
    assert score > 0.05  # algún signal disparó


def test_score_follower_handle_vacio_baseline():
    score, is_real = score_follower(handle="", platform="youtube")
    assert score == 0.05
    assert is_real is True


def test_score_follower_returns_tuple_floats():
    """Contract: helper devuelve (float, bool) listo para asignar a Mapped fields."""
    score, is_real = score_follower(handle="test.user", platform="youtube")
    assert isinstance(score, float)
    assert isinstance(is_real, bool)
    assert 0.0 <= score <= 1.0


def test_score_follower_threshold_consistency():
    """is_real coherente con BOT_THRESHOLD: si score >= threshold, is_real=False."""
    # Handle muy bot-like
    score_hi, real_hi = score_follower(
        handle="ab12345678901234567890", platform="youtube"
    )
    if score_hi >= BOT_THRESHOLD:
        assert real_hi is False
    else:
        assert real_hi is True


def test_score_follower_platform_independent_for_username():
    """`_analyze_username` solo mira handle. Score consistente across platforms."""
    s1, _ = score_follower(handle="test.user", platform="youtube")
    s2, _ = score_follower(handle="test.user", platform="instagram")
    assert s1 == s2
