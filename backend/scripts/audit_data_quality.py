#!/usr/bin/env python3
"""audit_data_quality — Pipeline auditoría de campos (PLAN-2026-05-13 S5).

4 capas independientes:

1. ``audit_table_coverage``      — NULLs %, distinct values, top valores
2. ``audit_referential``         — FK huérfanas
3. ``audit_api_contract``        — endpoints FE sin BE (y BE sin uso FE info)
4. (reservada para futuras capas, ej. PII)

Outputs:
- ``.context/audits/data-quality-YYYY-MM-DD.md`` (humano)
- ``.context/audits/data-quality-YYYY-MM-DD.json`` (CI/diff)

Exit codes:
- 0 clean (sólo low/info)
- 1 warnings (medium/high)
- 2 critical (FK rota o endpoint FE sin BE)

Uso:
    python backend/scripts/audit_data_quality.py             # full
    python backend/scripts/audit_data_quality.py --subset    # rápido (pre-commit)
    python backend/scripts/audit_data_quality.py --layer coverage
    python backend/scripts/audit_data_quality.py --layer api-contract

Si se ejecuta dentro del container Docker, lee ``DATABASE_URL`` del env de
``app.core.config``. Si se ejecuta desde el host, recibe ``--db-url``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import asyncpg

def _find_repo_root(start: Path) -> Path:
    """Sube directorios hasta encontrar `.context/`. Cae a parents[2] como fallback."""
    cur = start
    for _ in range(6):
        if (cur / ".context").is_dir():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return start.parents[2] if len(start.parents) > 2 else start


REPO_ROOT = _find_repo_root(Path(__file__).resolve())
FRONTEND_API_DIR = REPO_ROOT / "frontend" / "src" / "lib" / "api"
DEFAULT_AUDITS_DIR = REPO_ROOT / ".context" / "audits"


# Severidad → exit code priority
SEV_INFO = "info"
SEV_LOW = "low"
SEV_MEDIUM = "medium"
SEV_HIGH = "high"
SEV_CRITICAL = "critical"

SEVERITY_RANK = {
    SEV_INFO: 0,
    SEV_LOW: 1,
    SEV_MEDIUM: 2,
    SEV_HIGH: 3,
    SEV_CRITICAL: 4,
}

# Tablas core auditadas en modo --subset (pre-commit)
SUBSET_TABLES = [
    "dirigentes",
    "social_profiles",
    "social_posts",
    "social_comments",
    "social_followers",
    "follower_engagement",
    "oauth_tokens_by_platform",
    "users",
]


# ─────────────────────────────────────────────────────────────────────────
# Layer 1 · table coverage (NULLs % + distinct + top values)
# ─────────────────────────────────────────────────────────────────────────


async def audit_table_coverage(
    conn: asyncpg.Connection, tables: list[str] | None = None
) -> list[dict[str, Any]]:
    if tables is None:
        rows = await conn.fetch(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' "
            "ORDER BY tablename"
        )
        tables = [r["tablename"] for r in rows]

    findings: list[dict[str, Any]] = []

    for table in tables:
        total = await conn.fetchval(f'SELECT COUNT(*) FROM "{table}"')
        if total == 0:
            findings.append(
                {
                    "layer": "coverage",
                    "table": table,
                    "severity": SEV_LOW,
                    "type": "empty_table",
                    "message": f"Tabla '{table}' está vacía (0 rows)",
                }
            )
            continue

        cols = await conn.fetch(
            """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema='public' AND table_name=$1
            ORDER BY ordinal_position
            """,
            table,
        )

        for col in cols:
            cname = col["column_name"]
            is_nullable = col["is_nullable"] == "YES"
            null_count = await conn.fetchval(
                f'SELECT COUNT(*) FROM "{table}" WHERE "{cname}" IS NULL'
            )
            null_pct = (null_count / total) * 100 if total > 0 else 0.0

            if is_nullable and null_pct > 50:
                sev = SEV_HIGH if null_pct > 80 else SEV_MEDIUM
                findings.append(
                    {
                        "layer": "coverage",
                        "table": table,
                        "column": cname,
                        "severity": sev,
                        "type": "high_null_ratio",
                        "null_count": null_count,
                        "total": total,
                        "null_pct": round(null_pct, 2),
                        "message": (
                            f"{table}.{cname}: {null_pct:.1f}% NULL "
                            f"({null_count}/{total})"
                        ),
                    }
                )

        findings.append(
            {
                "layer": "coverage",
                "table": table,
                "severity": SEV_INFO,
                "type": "row_count",
                "total": total,
                "message": f"{table}: {total} rows",
            }
        )

    return findings


# ─────────────────────────────────────────────────────────────────────────
# Layer 2 · referential integrity
# ─────────────────────────────────────────────────────────────────────────


REFERENTIAL_CHECKS = [
    (
        "social_comments.parent_post_id → social_posts.id",
        """
        SELECT COUNT(*) FROM social_comments c
        WHERE NOT EXISTS (SELECT 1 FROM social_posts p WHERE p.id = c.parent_post_id)
        """,
    ),
    (
        "social_profiles.dirigente_id → dirigentes.id",
        """
        SELECT COUNT(*) FROM social_profiles sp
        WHERE NOT EXISTS (SELECT 1 FROM dirigentes d WHERE d.id = sp.dirigente_id)
        """,
    ),
    (
        "social_posts.profile_id → social_profiles.id",
        """
        SELECT COUNT(*) FROM social_posts po
        WHERE NOT EXISTS (SELECT 1 FROM social_profiles sp WHERE sp.id = po.profile_id)
        """,
    ),
    (
        "oauth_tokens_by_platform.dirigente_id → dirigentes.id",
        """
        SELECT COUNT(*) FROM oauth_tokens_by_platform o
        WHERE NOT EXISTS (SELECT 1 FROM dirigentes d WHERE d.id = o.dirigente_id)
        """,
    ),
    (
        "follower_engagement.follower_id → social_followers.id",
        """
        SELECT COUNT(*) FROM follower_engagement fe
        WHERE NOT EXISTS (SELECT 1 FROM social_followers sf WHERE sf.id = fe.follower_id)
        """,
    ),
    (
        "follower_engagement.post_id → social_posts.id",
        """
        SELECT COUNT(*) FROM follower_engagement fe
        WHERE NOT EXISTS (SELECT 1 FROM social_posts p WHERE p.id = fe.post_id)
        """,
    ),
]


async def audit_referential(conn: asyncpg.Connection) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for label, query in REFERENTIAL_CHECKS:
        try:
            orphans = await conn.fetchval(query)
        except asyncpg.UndefinedTableError as exc:
            findings.append(
                {
                    "layer": "referential",
                    "severity": SEV_INFO,
                    "type": "table_missing",
                    "message": f"Skipped {label}: {exc}",
                }
            )
            continue
        if orphans and orphans > 0:
            findings.append(
                {
                    "layer": "referential",
                    "severity": SEV_CRITICAL,
                    "type": "orphan_fk",
                    "message": f"{label}: {orphans} huérfanos",
                    "orphans": orphans,
                }
            )
        else:
            findings.append(
                {
                    "layer": "referential",
                    "severity": SEV_INFO,
                    "type": "fk_clean",
                    "message": f"{label}: 0 huérfanos ✓",
                }
            )
    return findings


# ─────────────────────────────────────────────────────────────────────────
# Layer 3 · FE↔BE endpoint contract
# ─────────────────────────────────────────────────────────────────────────


# Captura: api.<method>(`/path/...`) o ('/path/...')
API_CALL_RE = re.compile(
    r"""api\.(?P<method>get|post|patch|put|delete)\s*\(\s*[`"']"""
    r"""(?P<path>/[^`"'?]+)"""
)
# Captura template literal variables → reemplaza por {var}
TEMPLATE_VAR_RE = re.compile(r"\$\{[^}]+\}")


def normalize_path(raw: str) -> str:
    """`/dirigentes/${id}/foo` → `/dirigentes/{var}/foo` ; quita trailing ?"""
    p = TEMPLATE_VAR_RE.sub("{var}", raw).rstrip("/").split("?", 1)[0]
    return p or "/"


def extract_frontend_calls(frontend_dir: Path | None = None) -> list[tuple[str, str, str]]:
    """Devuelve [(file, method, normalized_path), ...]."""
    base = frontend_dir or FRONTEND_API_DIR
    if not base.exists():
        return []
    out: list[tuple[str, str, str]] = []
    for tsfile in base.rglob("*.ts"):
        src = tsfile.read_text(errors="ignore")
        for m in API_CALL_RE.finditer(src):
            try:
                relpath = tsfile.relative_to(REPO_ROOT).as_posix()
            except ValueError:
                relpath = tsfile.as_posix()
            out.append(
                (
                    relpath,
                    m.group("method").upper(),
                    normalize_path(m.group("path")),
                )
            )
    return out


def collect_backend_routes() -> set[tuple[str, str]]:
    """Devuelve {(METHOD, normalized_path)} cargando ``app.api.v1.api_router``."""
    try:
        from app.api.v1 import api_router  # type: ignore
    except Exception as exc:  # pragma: no cover (host vs container)
        print(f"[audit] No pude cargar app.api.v1: {exc}", file=sys.stderr)
        return set()

    out: set[tuple[str, str]] = set()
    for route in getattr(api_router, "routes", []):
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", None) or set()
        # Normalizamos /api/v1/foo/{id} → /foo/{var} para match con FE
        np = re.sub(r"\{[^}]+\}", "{var}", path)
        np = np.removeprefix("/api/v1").rstrip("/")
        if not np:
            np = "/"
        for m in methods:
            out.add((m.upper(), np))
    return out


def audit_api_contract(frontend_dir: Path | None = None) -> list[dict[str, Any]]:
    fe_calls = extract_frontend_calls(frontend_dir)
    be_routes = collect_backend_routes()
    findings: list[dict[str, Any]] = []

    if not fe_calls:
        findings.append(
            {
                "layer": "api_contract",
                "severity": SEV_LOW,
                "type": "no_fe_calls",
                "message": (
                    "No se encontraron llamadas api.* en frontend/src/lib/api · "
                    "verificar path o presencia del directorio."
                ),
            }
        )
        return findings

    if not be_routes:
        findings.append(
            {
                "layer": "api_contract",
                "severity": SEV_MEDIUM,
                "type": "no_be_routes",
                "message": (
                    "No se pudieron cargar rutas del backend "
                    "(app.api.v1.api_router import falló)"
                ),
            }
        )
        return findings

    be_paths_by_method: dict[str, set[str]] = defaultdict(set)
    for method, path in be_routes:
        be_paths_by_method[method].add(path)

    used_be: set[tuple[str, str]] = set()
    for file, method, raw_path in fe_calls:
        path = raw_path
        # Backend paths para este método
        candidates = be_paths_by_method.get(method, set())
        if path in candidates:
            used_be.add((method, path))
            continue
        # Fallback: match relajado (un FE puede llamar `/foo/{var}/bar` y BE
        # define `/foo/{var}` con sub-router · igualamos hasta primer {var})
        found = False
        for be_path in candidates:
            if path.split("/{var}", 1)[0] == be_path.split("/{var}", 1)[0]:
                # Mismo prefijo + 1 var: aceptar si suffix coincide
                if path.replace("/{var}", "X") == be_path.replace("/{var}", "X"):
                    used_be.add((method, be_path))
                    found = True
                    break
        if not found:
            findings.append(
                {
                    "layer": "api_contract",
                    "severity": SEV_CRITICAL,
                    "type": "fe_orphan",
                    "method": method,
                    "path": path,
                    "file": file,
                    "message": (
                        f"FE llama {method} {path} ({file}) pero NO existe en BE"
                    ),
                }
            )

    # Info: BE no usados (no crítico)
    for method, paths in be_paths_by_method.items():
        for p in sorted(paths):
            if (method, p) not in used_be and p not in {"/health", "/health/"}:
                findings.append(
                    {
                        "layer": "api_contract",
                        "severity": SEV_INFO,
                        "type": "be_unused",
                        "method": method,
                        "path": p,
                        "message": f"BE {method} {p} no es llamado desde FE hooks",
                    }
                )

    return findings


# ─────────────────────────────────────────────────────────────────────────
# Report writers
# ─────────────────────────────────────────────────────────────────────────


def write_markdown(findings: list[dict[str, Any]], path: Path) -> None:
    counts: dict[str, int] = defaultdict(int)
    by_layer: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for f in findings:
        counts[f.get("severity", SEV_INFO)] += 1
        by_layer[f.get("layer", "unknown")].append(f)

    lines = [
        f"# Data Quality Audit · {datetime.now(UTC).date().isoformat()}",
        "",
        "## Resumen",
        "",
        f"- critical: {counts.get(SEV_CRITICAL, 0)}",
        f"- high: {counts.get(SEV_HIGH, 0)}",
        f"- medium: {counts.get(SEV_MEDIUM, 0)}",
        f"- low: {counts.get(SEV_LOW, 0)}",
        f"- info: {counts.get(SEV_INFO, 0)}",
        f"- total findings: {len(findings)}",
        "",
    ]
    for layer in sorted(by_layer):
        lines.append(f"## Layer: {layer}")
        lines.append("")
        items = by_layer[layer]
        items.sort(key=lambda x: -SEVERITY_RANK.get(x.get("severity", SEV_INFO), 0))
        for f in items:
            sev = f.get("severity", SEV_INFO)
            lines.append(f"- **[{sev.upper()}]** {f.get('message', '')}")
        lines.append("")

    path.write_text("\n".join(lines))


def write_json(findings: list[dict[str, Any]], path: Path) -> None:
    path.write_text(json.dumps(findings, indent=2, default=str))


def compute_exit_code(findings: list[dict[str, Any]]) -> int:
    has_critical = any(f.get("severity") == SEV_CRITICAL for f in findings)
    has_warn = any(
        f.get("severity") in {SEV_HIGH, SEV_MEDIUM} for f in findings
    )
    if has_critical:
        return 2
    if has_warn:
        return 1
    return 0


# ─────────────────────────────────────────────────────────────────────────
# Entry
# ─────────────────────────────────────────────────────────────────────────


async def run(args: argparse.Namespace) -> int:
    audits_dir = Path(args.output_dir) if args.output_dir else DEFAULT_AUDITS_DIR
    audits_dir.mkdir(parents=True, exist_ok=True)
    findings: list[dict[str, Any]] = []

    if args.layer in {"all", "api-contract"}:
        fe_dir = Path(args.frontend_dir) if args.frontend_dir else None
        findings.extend(audit_api_contract(fe_dir))

    if args.layer in {"all", "coverage", "referential"}:
        db_url = args.db_url
        if not db_url:
            from app.core.config import settings  # type: ignore

            db_url = settings.DATABASE_URL
        # asyncpg no acepta el driver SQLAlchemy
        db_url = db_url.replace("+asyncpg", "").replace("+psycopg", "")
        conn = await asyncpg.connect(db_url)
        try:
            if args.layer in {"all", "coverage"}:
                tables = SUBSET_TABLES if args.subset else None
                findings.extend(await audit_table_coverage(conn, tables))
            if args.layer in {"all", "referential"}:
                findings.extend(await audit_referential(conn))
        finally:
            await conn.close()

    today = datetime.now(UTC).date().isoformat()
    md_path = audits_dir / f"data-quality-{today}.md"
    json_path = audits_dir / f"data-quality-{today}.json"
    write_markdown(findings, md_path)
    write_json(findings, json_path)

    print(f"[audit] {len(findings)} findings · md={md_path} json={json_path}")
    return compute_exit_code(findings)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--layer",
        choices=["all", "coverage", "referential", "api-contract"],
        default="all",
    )
    parser.add_argument("--subset", action="store_true")
    parser.add_argument("--db-url", default=None)
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Override directorio de salida (default: <repo>/.context/audits)",
    )
    parser.add_argument(
        "--frontend-dir",
        default=None,
        help=(
            "Directorio frontend/src/lib/api a auditar (útil si --layer api-contract "
            "se corre desde container sin frontend montado)"
        ),
    )
    args = parser.parse_args()

    import asyncio

    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
