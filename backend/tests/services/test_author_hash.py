"""Tests de pseudonimización canónica de author_hash."""
from app.services.author_hash import ensure_author_hash, is_hashed


def test_hash_existente_no_se_toca():
    h = "a" * 64
    assert ensure_author_hash(h) == h
    assert is_hashed(h)


def test_nombre_crudo_se_hashea():
    out = ensure_author_hash("Tito Rosario", "FACEBOOK")
    assert is_hashed(out)
    assert " " not in out
    assert out != "Tito Rosario"


def test_determinista_mismo_nombre_mismo_hash():
    a = ensure_author_hash("Elena Smith", "FACEBOOK")
    b = ensure_author_hash("Elena Smith", "FACEBOOK")
    assert a == b


def test_id_numerico_corto_se_hashea():
    # "1595498" (7 dígitos) no es hash válido (<8) → se hashea
    assert is_hashed(ensure_author_hash("1595498", "FACEBOOK"))


def test_vacio():
    assert ensure_author_hash("") == ""
    assert not is_hashed("")
    assert not is_hashed("Tito Rosario")
