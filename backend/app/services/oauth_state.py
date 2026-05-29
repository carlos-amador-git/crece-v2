"""OAuth state firmado con HMAC (B-OAUTH-YT-STATE-1).

Reemplaza el state inseguro ``f"{token_urlsafe(24)}:{dirigente_id}"`` que un
atacante podía manipular para secuestrar un OAuth válido y asignarlo a otro
dirigente. El nuevo state firma payload con HMAC-SHA256 usando ``JWT_SECRET``.

Formato wire:
    ``<payload_b64>.<signature_b64>``

Payload contiene ``dirigente_id`` + ``nonce`` (32 random bytes) + ``ts`` (UNIX
seconds, para TTL futuro). Signature verifica con `hmac.compare_digest`.
"""
from __future__ import annotations

import base64
import hmac
import json
import secrets
from hashlib import sha256
from time import time

from app.core.config import settings


class OAuthStateError(ValueError):
    """State OAuth inválido (formato, firma, o expirado)."""


def _b64u_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64u_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding < 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("ascii"))


def _secret() -> bytes:
    return settings.JWT_SECRET.encode("utf-8")


def sign_state(dirigente_id: int) -> str:
    """Construye state firmado con HMAC-SHA256 sobre JWT_SECRET."""
    if dirigente_id <= 0:
        raise OAuthStateError("dirigente_id debe ser > 0")
    payload = {
        "did": dirigente_id,
        "n": secrets.token_urlsafe(24),
        "ts": int(time()),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = _b64u_encode(payload_bytes)
    signature = hmac.new(_secret(), payload_b64.encode("ascii"), sha256).digest()
    return f"{payload_b64}.{_b64u_encode(signature)}"


def verify_state(state: str, *, max_age_seconds: int = 600) -> int:
    """Valida firma + extrae dirigente_id. Raises OAuthStateError en cualquier falla.

    max_age_seconds: state expira después de N segundos (default 10 min).
    OAuth flow típico: usuario → consent → callback, < 5 min. 10 min holgado.
    """
    if not state or "." not in state:
        raise OAuthStateError("state malformado")
    try:
        payload_b64, signature_b64 = state.rsplit(".", 1)
    except ValueError as exc:
        raise OAuthStateError("state malformado") from exc

    expected_sig = hmac.new(_secret(), payload_b64.encode("ascii"), sha256).digest()
    try:
        provided_sig = _b64u_decode(signature_b64)
    except Exception as exc:
        raise OAuthStateError("signature inválida") from exc

    if not hmac.compare_digest(expected_sig, provided_sig):
        raise OAuthStateError("signature mismatch")

    try:
        payload_bytes = _b64u_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise OAuthStateError("payload inválido") from exc

    did = payload.get("did")
    ts = payload.get("ts")
    if not isinstance(did, int) or did <= 0:
        raise OAuthStateError("dirigente_id ausente o inválido en payload")
    if not isinstance(ts, int):
        raise OAuthStateError("timestamp ausente en payload")
    if int(time()) - ts > max_age_seconds:
        raise OAuthStateError(f"state expirado (>{max_age_seconds}s)")
    return did
