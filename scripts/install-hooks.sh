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
chmod +x .githooks/* 2>/dev/null || true

echo "✅ Hooks activados: core.hooksPath -> .githooks"
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
