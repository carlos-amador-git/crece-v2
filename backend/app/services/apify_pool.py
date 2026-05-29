"""Apify account pool — rotación por budget disponible.

Cada cuenta Apify free tier da $5/mes. Mantener varias cuentas permite:
- Sumar $5 × N en budget total
- Tener trials independientes por actor (scrapestorm 120min × N)
- Resilencia: si una cuenta rate-limita un actor, otra responde

Uso:
    from app.services.apify_pool import pick_token
    token = pick_token(min_budget_usd=0.50)
    client = ApifyClient(token)

El picker:
1. Lee APIFY_ACCOUNTS=ANGEL,RAFA (orden preferencia)
2. Para cada cuenta consulta /v2/users/me/usage/monthly
3. Devuelve token con mayor budget disponible (≥ min_budget_usd)
4. Cachea usage 5 min in-memory para no martillar API

Configuración esperada en env:
    APIFY_TOKEN_<NAME>=<token>   # uno por cuenta
    APIFY_ACCOUNTS=<NAME1>,<NAME2>,...   # orden preferencia
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

import requests

log = logging.getLogger(__name__)

FREE_TIER_LIMIT_USD = 5.0
USAGE_API = "https://api.apify.com/v2/users/me/usage/monthly"
CACHE_TTL_SECONDS = 300

_cache: dict[str, tuple[float, float]] = {}  # name → (used_usd, fetched_at)
_exhausted: set[str] = set()  # marca temporal in-memory


@dataclass
class AccountStatus:
    name: str
    token: str
    used_usd: float
    available_usd: float


def _accounts_in_order() -> list[tuple[str, str]]:
    """Lee APIFY_ACCOUNTS y resuelve a (name, token) pairs."""
    order = [n.strip() for n in os.environ.get("APIFY_ACCOUNTS", "").split(",") if n.strip()]
    pairs: list[tuple[str, str]] = []
    for name in order:
        tok = os.environ.get(f"APIFY_TOKEN_{name}")
        if tok:
            pairs.append((name, tok))
        else:
            log.warning("APIFY_TOKEN_%s no encontrado en env", name)
    return pairs


def _fetch_usage(token: str) -> float:
    """Devuelve usage USD del ciclo actual via API."""
    r = requests.get(f"{USAGE_API}?token={token}", timeout=10)
    r.raise_for_status()
    data = r.json().get("data", {})
    services = data.get("monthlyServiceUsage", {})
    total = sum(
        float(v.get("amountAfterVolumeDiscountUsd") or 0.0)
        for v in services.values()
        if isinstance(v, dict)
    )
    return total


def get_status(name: str, token: str, use_cache: bool = True) -> AccountStatus:
    now = time.time()
    if use_cache and name in _cache:
        used, fetched_at = _cache[name]
        if (now - fetched_at) < CACHE_TTL_SECONDS:
            return AccountStatus(name, token, used, max(0.0, FREE_TIER_LIMIT_USD - used))
    try:
        used = _fetch_usage(token)
    except Exception as e:
        log.warning("Failed to fetch usage for %s: %s", name, e)
        used = FREE_TIER_LIMIT_USD  # asumir agotado si no responde
    _cache[name] = (used, now)
    return AccountStatus(name, token, used, max(0.0, FREE_TIER_LIMIT_USD - used))


def pick_token(min_budget_usd: float = 0.10, use_cache: bool = True) -> str:
    """Selecciona el token con más budget disponible (≥ min_budget_usd).

    Respeta el orden de APIFY_ACCOUNTS como tiebreaker.
    Raises RuntimeError si ninguna cuenta tiene budget suficiente.
    """
    pairs = _accounts_in_order()
    if not pairs:
        fallback = os.environ.get("APIFY_TOKEN")
        if fallback:
            log.warning("APIFY_ACCOUNTS no configurado, usando APIFY_TOKEN single-account")
            return fallback
        raise RuntimeError("No Apify accounts configured (APIFY_ACCOUNTS empty)")

    statuses = [
        get_status(name, token, use_cache=use_cache)
        for name, token in pairs
        if name not in _exhausted
    ]
    eligibles = [s for s in statuses if s.available_usd >= min_budget_usd]
    if not eligibles:
        details = ", ".join(f"{s.name}=${s.available_usd:.2f}" for s in statuses)
        raise RuntimeError(
            f"No Apify account has >= ${min_budget_usd:.2f} budget. Status: {details}"
        )
    eligibles.sort(key=lambda s: s.available_usd, reverse=True)
    chosen = eligibles[0]
    log.info(
        "Apify picked=%s · available=$%.2f · candidates=[%s]",
        chosen.name,
        chosen.available_usd,
        ", ".join(f"{s.name}=${s.available_usd:.2f}" for s in statuses),
    )
    return chosen.token


def mark_exhausted(token: str) -> None:
    """Marca temporal in-memory para que pick_token() no la reseleccione esta sesión."""
    for name, tok in _accounts_in_order():
        if tok == token:
            _exhausted.add(name)
            log.info("Apify account %s marked exhausted (in-memory)", name)
            return


def status_report() -> list[AccountStatus]:
    """Lista todas las cuentas con su status actual. Útil para logs/health."""
    return [get_status(name, token, use_cache=False) for name, token in _accounts_in_order()]


if __name__ == "__main__":
    import sys
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    for env_file in [PROJECT_ROOT / ".env", PROJECT_ROOT / "backend/.env.scraping-keys"]:
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.split("#")[0].strip())

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    print("Apify Account Pool · Status:")
    for s in status_report():
        bar = "█" * int(20 * s.used_usd / FREE_TIER_LIMIT_USD)
        bar += "·" * (20 - len(bar))
        print(f"  {s.name:8s} [{bar}] ${s.used_usd:>5.2f}/{FREE_TIER_LIMIT_USD:.0f} · disp=${s.available_usd:>5.2f}")
    print()
    try:
        tok = pick_token(min_budget_usd=0.50)
        print(f"pick_token(min=$0.50) → ...{tok[-8:]}")
    except RuntimeError as e:
        print(f"pick_token FAILED: {e}")
        sys.exit(1)
