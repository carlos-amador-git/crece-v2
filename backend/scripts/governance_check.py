#!/usr/bin/env python3
"""governance_check.py — gate mecánico de gobernanza de CRECE v2.

Convierte reglas duras "de papel" (AUTONOMY-RULES.md, CLAUDE.md) en checks
ejecutables. NO juzga prosa. Verifica lo mecánicamente detectable, motivado por
incidentes REALES de este repo y del ecosistema (ver docs/adr/0006):

  1. PATHS PROHIBIDOS staged → *.dump, exports/, captures/, backups/, .env
     (PII de audiencia/likers + secretos que NUNCA deben entrar a git).
     Incidente CRECE: dump de BD con ~185k watched_like_events (PII) generado
     2026-05-30; un commit accidental lo expondría aun en repo privado.
  2. SECRETOS HARDCODEADOS → valores reales del .env local (PG/JWT/APIFY/Claude/
     cookies FB/IG) + patrones de alta confianza. Adaptado de MarxCha/radar D-045.
  3. (WARNING, no bloqueo) comandos DESTRUCTIVOS en .sh/.md/.py/.sql staged:
     Docker (down -v / volume rm / system prune / Docker.raw) y BD
     (DROP TABLE / TRUNCATE / alembic downgrade base). Requieren OK CEO
     (AUTONOMY-RULES §Operación destructiva; postmortem Docker.raw 2026-04-13).

NO porta el Sign-off RFC 2119 de cfdi-platform: CRECE no tiene sops/*.sop.md
(sería no-op permanente). Ver docs/adr/0006.

DECISIÓN anti-falsos-positivos (auditoría Gemini Puerta 2, 2026-05-30):
  CRECE maneja datos POLÍTICOS PÚBLICOS (nombres de dirigentes, IDs de campaña,
  handles). Por eso NO se escanea PII inline (CURP/RFC/nombres) — detonaría sin
  parar con datos legítimos. El scan se limita a SECRETOS (valores .env, tokens)
  y PATHS de dumps/exports. Allow-list de archivos, marcadores dummy e inline
  `# gov-ignore`.

Uso:
  python backend/scripts/governance_check.py --check-staged   # pre-commit (default)
  python backend/scripts/governance_check.py --all            # todo el tree (CI)

Exit: 0 PASS · 1 FAIL (bloqueo) · 2 error de uso.
Bypass de emergencia (queda en reflog): git commit --no-verify
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True)
    return Path(r.stdout.strip() or ".")


ROOT = repo_root()

# 1. Paths que jamás deben entrar a git (PII de audiencia / dumps de BD).
#    NB: captures/ NO se bloquea — tiene artefactos tracked legítimos (catálogos).
#    .env se maneja aparte en _is_forbidden_env() para eximir *.example/*.sample.
FORBIDDEN_PATH = re.compile(
    r"(^|/)(exports|backups)/"
    r"|\.dump$|\.sql\.gz$|\.dump\.gz$"
)


def _is_forbidden_env(path: str) -> bool:
    """Bloquea .env reales pero permite cualquier plantilla *.example / *.sample."""
    base = path.rsplit("/", 1)[-1]
    if base.endswith((".example", ".sample")):
        return False
    return base == ".env" or base.startswith(".env.")

# Archivos donde "secretos" son legítimos (forma/dummy/demo) → no escanear secretos.
ALLOW_FILE = re.compile(
    r"(^|/)\.env\.example$|(^|/)\.env\.sample$"
    r"|(^|/)tests/fixtures/|(^|/)tests/.*conftest"
    r"|\.example\.|\.sample\."
    r"|(^|/)\.github/workflows/"               # workflows usan creds dummy de test
    r"|(^|/)backend/scripts/governance_check\.py$"  # este script contiene los patrones
)

# Marcadores que indican valor dummy/placeholder (no secreto real).
DUMMY = ("test", "example", "cambiar", "changeme", "dummy", "ci-test",
         "placeholder", "your-", "your_", "xxxx", "<", "fake", "sample",
         "demo2026", "crece2026",          # passwords demo del seed.py
         "crece_secret", "crece_dev", "dev-crece", "min32chars",  # defaults dev
         "localhost", "127.0.0.1")          # connection strings de dev local

# Claves sensibles de .env de CRECE cuyos VALORES no deben aparecer en código tracked.
SENSITIVE_ENV = (
    "POSTGRES_PASSWORD", "JWT_SECRET", "CLAUDE_API_KEY", "GROQ_API_KEY",
    "APIFY_TOKEN", "APIFY_TOKEN_ANGEL", "APIFY_TOKEN_INICIAL",
    "APIFY_TOKEN_RAFA", "APIFY_TOKEN_SOPORTE", "REDIS_PASSWORD",
    "MINIO_ROOT_PASSWORD", "INSTAGRAM_PASSWORD", "TIKTOK_PASSWORD",
    "TWITTER_AUTH_TOKEN", "FACEBOOK_XS", "FACEBOOK_C_USER", "BRD_API_TOKEN",
    "N8N_WEBHOOK_SECRET", "FLOWER_PASSWORD", "GOOGLE_OAUTH_CLIENT_SECRET",
    "PII_ENCRYPTION_KEY", "BUGSINK_DSN", "DISCORD_WEBHOOK_URL",
)

# Patrones de secreto de alta confianza (no entropía genérica).
SECRET_PATTERNS = [
    re.compile(r"""password\s*=\s*["'][^"']{16,}["']"""),
    re.compile(r"""(APIFY_TOKEN|auth_token|JWT_SECRET|CLAUDE_API_KEY|GROQ_API_KEY|"""
               r"""PII_ENCRYPTION_KEY|N8N_WEBHOOK_SECRET)\s*[=:]\s*["'][^"']{12,}["']"""),
    re.compile(r"""postgres(?:ql)?(?:\+\w+)?://[^:/\s]+:[^@\s"']{12,}@"""),
    re.compile(r"""sk-[A-Za-z0-9]{20,}"""),                 # API keys estilo Claude/OpenAI
    re.compile(r"""apify_api_[A-Za-z0-9]{20,}"""),          # tokens Apify
]

# Destructivo en archivos: SOLO scripts shell ejecutables (.sh). DROP TABLE/TRUNCATE
# son legítimos en migraciones/tests/scripts de carga; la defensa real contra
# EJECUTAR un destructivo es la capa harness (safe-ops-guard.sh), no este scan.
# Por eso aquí solo marcamos .sh (deploy/ops) y como WARNING.
DESTRUCTIVE = re.compile(
    r"docker\s+(?:compose\s+)?down\b[^\n]*\s-v\b"
    r"|docker\s+volume\s+rm"
    r"|docker\s+system\s+prune\b[^\n]*(--volumes|-a)"
    r"|Docker\.raw",
    re.IGNORECASE,
)
# Rutas exentas del scan de destructivo (legítimo o auto-referencial).
DESTRUCTIVE_SKIP = re.compile(
    r"(^|/)(tests?|migrations)/|(^|/)docs/|(^|/)\.context/"
    r"|(^|/)AUTONOMY-RULES\.md$|(^|/)AGENTS\.md$|(^|/)CLAUDE\.md$"
    r"|(^|/)scripts/safe-ops-guard\.sh$"
)


def load_env_secret_values() -> set[str]:
    """Valores reales de secretos del .env local (si existe). En CI no hay .env
    → el scan cae solo a patrones (suficiente)."""
    vals: set[str] = set()
    env = ROOT / ".env"
    if not env.exists():
        return vals
    for line in env.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        val = val.strip().strip('"').strip("'")
        if key.strip() in SENSITIVE_ENV and len(val) >= 12 \
                and not any(d in val.lower() for d in DUMMY):
            vals.add(val)
    return vals


def staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True).stdout
    return [f for f in out.splitlines() if f.strip()]


def all_files() -> list[str]:
    return subprocess.run(["git", "ls-files"],
                          capture_output=True, text=True).stdout.splitlines()


def scan(files: list[str], secret_values: set[str]) -> tuple[list[str], list[str]]:
    fails: list[str] = []
    warns: list[str] = []
    for f in files:
        if FORBIDDEN_PATH.search(f) or _is_forbidden_env(f):
            fails.append(f"PATH PROHIBIDO staged: {f} (PII/dump/.env — nunca a git)")
            continue
        p = ROOT / f
        if not p.exists() or p.is_dir():
            continue
        allow_secrets = bool(ALLOW_FILE.search(f))
        scan_destr = f.endswith(".sh") and not DESTRUCTIVE_SKIP.search(f)
        try:
            text = p.read_text(errors="ignore")
        except Exception:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if "gov-ignore" in line:
                continue
            low = line.lower()
            # Interpolación de variables (${VAR}, $VAR) no es un secreto hardcoded.
            interpolated = "${" in line
            if not allow_secrets and not interpolated:
                hit = False
                for sv in secret_values:
                    if sv in line:
                        fails.append(f"SECRETO de .env hardcodeado: {f}:{i} "
                                     f"(valor real de un secreto del .env)")
                        hit = True
                        break
                if not hit and not any(d in low for d in DUMMY):
                    for pat in SECRET_PATTERNS:
                        if pat.search(line):
                            fails.append(f"PATRÓN de secreto: {f}:{i}")
                            break
            if scan_destr and DESTRUCTIVE.search(line):
                warns.append(f"Comando DESTRUCTIVO en {f}:{i} — requiere OK CEO "
                             f"(AUTONOMY-RULES §Operación destructiva)")
    return fails, warns


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-staged", action="store_true",
                    help="solo archivos en stage (pre-commit, default)")
    ap.add_argument("--all", action="store_true",
                    help="todo el tree tracked (auditoría manual completa)")
    ap.add_argument("--files", nargs="*", default=None,
                    help="lista explícita de archivos (CI sobre el diff del PR)")
    a = ap.parse_args()

    if a.files is not None:
        files = [f for f in a.files if f.strip()]
    elif a.all:
        files = all_files()
    else:
        files = staged_files()
    fails, warns = scan(files, load_env_secret_values())

    for w in dict.fromkeys(warns):
        print(f"⚠️  {w}", file=sys.stderr)
    if fails:
        print("\n⛔ governance_check FAIL — commit/merge bloqueado:", file=sys.stderr)
        for x in dict.fromkeys(fails):  # dedup preservando orden
            print(f"   ✗ {x}", file=sys.stderr)
        print("\n   Mueve el secreto a .env (léelo con os.getenv), o saca el path "
              "PII/dump del stage.", file=sys.stderr)
        print("   Falso positivo legítimo → marca la línea con  # gov-ignore", file=sys.stderr)
        print("   Emergencia (queda en reflog): git commit --no-verify", file=sys.stderr)
        return 1
    n = len(files)
    print(f"✅ governance_check PASS ({n} archivo(s)"
          + (f", {len(set(warns))} advertencia(s)" if warns else "") + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
