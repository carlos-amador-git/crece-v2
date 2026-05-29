"""Unit tests for HMAC OAuth state (B-OAUTH-YT-STATE-1)."""
from __future__ import annotations

import time

import pytest

from app.services.oauth_state import OAuthStateError, sign_state, verify_state


def test_roundtrip_returns_dirigente_id() -> None:
    state = sign_state(42)
    assert verify_state(state) == 42


def test_two_signs_produce_different_states() -> None:
    """nonce + ts deben hacer cada state único aunque el dirigente_id sea igual."""
    a = sign_state(7)
    b = sign_state(7)
    assert a != b
    assert verify_state(a) == verify_state(b) == 7


def test_tampered_payload_rejected() -> None:
    state = sign_state(10)
    payload_b64, sig_b64 = state.rsplit(".", 1)
    # Mismo length, dato distinto
    tampered = payload_b64[:-1] + ("A" if payload_b64[-1] != "A" else "B") + "." + sig_b64
    with pytest.raises(OAuthStateError, match="signature mismatch|payload inválido"):
        verify_state(tampered)


def test_tampered_signature_rejected() -> None:
    state = sign_state(10)
    payload_b64, sig_b64 = state.rsplit(".", 1)
    tampered = payload_b64 + "." + sig_b64[:-1] + ("A" if sig_b64[-1] != "A" else "B")
    with pytest.raises(OAuthStateError, match="signature mismatch|signature inválida"):
        verify_state(tampered)


def test_no_dot_rejected() -> None:
    with pytest.raises(OAuthStateError, match="malformado"):
        verify_state("nodothere")


def test_empty_rejected() -> None:
    with pytest.raises(OAuthStateError, match="malformado"):
        verify_state("")


def test_expired_state_rejected() -> None:
    state = sign_state(99)
    with pytest.raises(OAuthStateError, match="expirado"):
        verify_state(state, max_age_seconds=-1)


def test_negative_dirigente_id_rejected() -> None:
    with pytest.raises(OAuthStateError, match="> 0"):
        sign_state(-1)


def test_zero_dirigente_id_rejected() -> None:
    with pytest.raises(OAuthStateError, match="> 0"):
        sign_state(0)


def test_old_format_rejected() -> None:
    """El format viejo "<random>:<id>" ya no es aceptado."""
    with pytest.raises(OAuthStateError, match="malformado"):
        verify_state("randomtoken:42")
