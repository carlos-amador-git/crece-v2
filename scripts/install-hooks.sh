#!/usr/bin/env bash
#
# install-hooks.sh — activa los git hooks versionados de CRECE v2.
#
# Usa core.hooksPath (Git >= 2.9) → apunta a .githooks/ en el repo, de modo que
# los hooks viajen con el repositorio (no hay que copiarlos a .git/hooks/ por
# máquina). Ver docs/adr/0006.
#
# Hooks activados:
#   pre-commit    → governance_check (secretos/PII/destructivo) + anti-mock
#   post-commit   → graphify rebuild (preservado, antes solo en .git/hooks/)
#   post-checkout → graphify rebuild en branch switch (preservado)
#
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

git config core.hooksPath .githooks
chmod +x .githooks/* scripts/safe-ops-guard.sh 2>/dev/null || true

# Capa harness: registrar el hook PreToolUse(Bash) -> safe-ops-guard.sh en
# .claude/settings.json. NB: .claude/ está en .gitignore (config local por máquina),
# por eso el hook NO viaja en git y se (re)instala aquí, idempotente. Ver docs/adr/0006.
python3 - <<'PY'
import json, pathlib
p = pathlib.Path(".claude/settings.json")
p.parent.mkdir(exist_ok=True)
data = {}
if p.exists():
    try:
        data = json.loads(p.read_text() or "{}")
    except Exception:
        data = {}
hooks = data.setdefault("hooks", {}).setdefault("PreToolUse", [])
cmd = 'bash "$CLAUDE_PROJECT_DIR/scripts/safe-ops-guard.sh"'
already = any(
    h.get("matcher") == "Bash" and any(cmd in (x.get("command", "")) for x in h.get("hooks", []))
    for h in hooks if isinstance(h, dict)
)
if not already:
    hooks.append({"matcher": "Bash", "hooks": [{"type": "command", "command": cmd}]})
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print("   + hook harness (safe-ops-guard) registrado en .claude/settings.json")
else:
    print("   · hook harness ya presente en .claude/settings.json")
PY

echo "✅ Hooks activados: core.hooksPath -> .githooks + guard harness"
echo "   pre-commit    · governance_check + anti-mock"
echo "   post-commit   · graphify rebuild (ahora versionado)"
echo "   post-checkout · graphify rebuild en branch switch"
echo ""
echo "Probar el gate de gobernanza manualmente:"
echo "   python backend/scripts/governance_check.py --all          # todo el tree"
echo "   python backend/scripts/governance_check.py --check-staged  # solo stage"
echo ""
echo "Modo warn (no bloquea) durante el primer sprint:"
echo "   export CRECE_GUARD_MODE=warn      # afecta los guards de runtime"
echo ""
echo "Desactivar en un commit puntual (emergencia, queda en reflog):"
echo "   git commit --no-verify"
