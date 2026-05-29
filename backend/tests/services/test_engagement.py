"""Tests del cálculo canónico de engagement_rate."""
from app.services.engagement import compute_engagement_rate


def test_views_based_tiktok():
    # (likes+comments)/views*100 — shares NO cuenta cuando hay views
    assert compute_engagement_rate(144, 1, 0, 4173, 20100) == round(145 / 4173 * 100, 4)


def test_followers_based_twitter():
    # sin views → (likes+comments+shares)/followers*100
    assert compute_engagement_rate(0, 0, 1, 0, 55854) == round(1 / 55854 * 100, 4)


def test_sin_interaccion_es_cero():
    assert compute_engagement_rate(0, 0, 0, 1000, 5000) == 0.0


def test_sin_denominador_es_cero():
    # con interacción pero sin views ni followers → no calculable
    assert compute_engagement_rate(10, 5, 2, 0, 0) == 0.0


def test_views_tiene_prioridad_sobre_followers():
    # si hay views, usa views aunque haya followers
    er = compute_engagement_rate(100, 0, 0, 1000, 50000)
    assert er == round(100 / 1000 * 100, 4)  # 10.0, no la fórmula de followers


def test_none_safe():
    assert compute_engagement_rate(None, None, None, None, None) == 0.0
