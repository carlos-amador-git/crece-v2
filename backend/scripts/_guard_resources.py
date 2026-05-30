"""_guard_resources.py — guard de recursos para jobs pesados de CRECE.

Capa RUNTIME del enforcement de gobernanza (ver docs/adr/0006). Motivado por el
crash de RAM del 2026-05-27: `post_ingest_enrich.py` lanzado unattended de noche,
cada fila invoca `claude --print` (26 procesos MCP por llamada), sobre una Mac Mini
M4 (16 GB) ya saturada + captura de browser de RADAR concurrente → la máquina tronó.

Dos guardrails, ambos invocados al ARRANQUE de un script pesado:

  1. RAM disponible mínima. IMPORTANTE (auditoría Gemini Puerta 2): en macOS con
     Memoria Unificada, "free RAM" siempre marca bajo (el SO cachea todo). Medimos
     `psutil.virtual_memory().available` (memoria reclamable), NO `.free`, para no
     abortar jobs legítimos por falso positivo.

  2. Modo unattended. Correr un job pesado sin supervisión es lo que causó el crash.
     Por defecto se EXIGE un TTY (sesión interactiva). Para correr a propósito en
     background/cron, pasar --allow-unattended explícito.

Circuit breaker de iteraciones: helper opcional `iteration_guard()` para loops que
invocan LLMs (corta a un máximo configurable; jobs unattended en bucle queman
presupuesto además de RAM — auditoría Gemini).

Uso en un script:
    from _guard_resources import guard_heavy_job
    guard_heavy_job("post_ingest_enrich", allow_unattended=args.allow_unattended)

No bloquea por defecto en modo "warn" si se exporta CRECE_GUARD_MODE=warn.
"""
from __future__ import annotations

import os
import sys

# Umbral por defecto: Mac Mini M4 16 GB. 3500 MB libres deja margen para SO + lo que
# ya corre (Docker stacks, browser RADAR). Override: CRECE_GUARD_MIN_RAM_MB.
DEFAULT_MIN_RAM_MB = 3500


def _available_ram_mb() -> float | None:
    """RAM reclamable en MB. None si no se puede medir (no aborta en ese caso)."""
    try:
        import psutil
    except ImportError:
        return None
    # .available = memoria que el SO puede entregar sin swap agresivo (correcto en
    # macOS Unified Memory; .free daría falsos positivos constantes).
    return psutil.virtual_memory().available / (1024 * 1024)


def _mode() -> str:
    """'warn' (no aborta, solo avisa) o 'block' (aborta). Default block."""
    return os.environ.get("CRECE_GUARD_MODE", "block").strip().lower()


def guard_heavy_job(name: str, *, allow_unattended: bool = False,
                    min_ram_mb: int | None = None) -> None:
    """Verifica precondiciones antes de un job pesado. Aborta (exit 1) si falla y
    el modo es 'block'; en 'warn' solo imprime."""
    min_ram = min_ram_mb if min_ram_mb is not None else int(
        os.environ.get("CRECE_GUARD_MIN_RAM_MB", DEFAULT_MIN_RAM_MB))
    mode = _mode()
    problems: list[str] = []

    # 1. RAM disponible.
    avail = _available_ram_mb()
    if avail is None:
        print(f"[guard:{name}] psutil no disponible — salto el check de RAM "
              f"(pip install psutil para activarlo).", file=sys.stderr)
    elif avail < min_ram:
        problems.append(
            f"RAM disponible {avail:.0f} MB < mínimo {min_ram} MB. "
            f"Cierra stacks/browser o sube CRECE_GUARD_MIN_RAM_MB a conciencia.")

    # 2. Modo unattended.
    if not allow_unattended and not sys.stdin.isatty():
        problems.append(
            "ejecución NO interactiva (unattended) sin --allow-unattended. "
            "El crash RAM 2026-05-27 fue un job unattended. Corre attended o pasa "
            "--allow-unattended a conciencia (idealmente no concurrente con RADAR).")

    if not problems:
        if avail is not None:
            print(f"[guard:{name}] OK · RAM disponible {avail:.0f} MB · attended.",
                  file=sys.stderr)
        return

    header = f"[guard:{name}] precondiciones NO cumplidas:"
    for p in problems:
        header += f"\n  ✗ {p}"
    if mode == "warn":
        print(f"⚠️  {header}\n  (CRECE_GUARD_MODE=warn → continúo, pero quedas avisado)",
              file=sys.stderr)
        return
    print(f"⛔ {header}\n  Aborto (CRECE_GUARD_MODE=block). Override puntual: "
          f"CRECE_GUARD_MODE=warn.", file=sys.stderr)
    sys.exit(1)


def iteration_guard(count: int, *, name: str = "loop", max_iter: int | None = None) -> None:
    """Circuit breaker para loops que invocan LLMs. Aborta si count supera el máximo
    (default CRECE_GUARD_MAX_ITER o 5000). Evita bucles unattended que queman
    presupuesto + RAM."""
    cap = max_iter if max_iter is not None else int(
        os.environ.get("CRECE_GUARD_MAX_ITER", 5000))
    if count > cap:
        print(f"⛔ [guard:{name}] circuit breaker: {count} iteraciones > tope {cap}. "
              f"Aborto para evitar bucle/quema de presupuesto. Sube CRECE_GUARD_MAX_ITER "
              f"si es legítimo.", file=sys.stderr)
        sys.exit(1)
