"""Benchmark runner — sends the same prompt to multiple providers.

Providers:
    - ollama  : local Gemma via OLLAMA_BASE_URL
    - claude  : Anthropic Claude via CLAUDE_API_KEY
    - gemini  : via CLI wrapper (`gemini analyze` in PATH) — optional
    - offline : fixture output, used for smoke tests in CI

Outputs are written to:
    benchmarks/ai/outputs/{YYYY-MM-DD}/iter_{NN}_{provider}.md

Usage:
    python -m benchmarks.ai.runner \
        --prompt prompts/diagnostico_v1.md \
        --test-case test_cases/alejandro_pina_diagnostico.json \
        --providers ollama,claude \
        --iteration 1

    # Smoke test without network:
    python -m benchmarks.ai.runner --prompt prompts/diagnostico_v1.md \
        --test-case test_cases/alejandro_pina_diagnostico.json \
        --providers offline --iteration 0
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).parent
OUT_ROOT = BASE / "outputs"


def _render_prompt(prompt_template: str, test_case: dict[str, Any]) -> str:
    """If the test case carries a precomputed rendered_prompt (from
    build_test_cases.py running the real _build_prompt() against the DB),
    use it directly. Otherwise fall through to template substitution with
    {{context_json}} / {{territory_context}} / {{extra}} placeholders.

    Defensive: ignore strings that look like unfilled placeholders (e.g.
    'PLACEHOLDER', empty, or shorter than 100 chars — real prompts are ~2KB+).
    """
    rp = test_case.get("rendered_prompt")
    if isinstance(rp, str) and len(rp) > 200 and "PLACEHOLDER" not in rp.upper():
        return rp

    ctx = test_case.get("context", {})
    context_json = json.dumps(ctx, indent=2, ensure_ascii=False, default=str)

    dirigente = ctx.get("dirigente", {})
    estado = dirigente.get("estado", "")
    municipio = dirigente.get("municipio", "")
    territory = ""
    if estado or municipio:
        where = municipio or estado
        territory = (
            f"\n## CONTEXTO TERRITORIAL:\nEl dirigente opera en {where}. "
            f"Considera temas locales al hacer recomendaciones.\n"
        )

    return (
        prompt_template
        .replace("{{context_json}}", context_json)
        .replace("{{territory_context}}", territory)
        .replace("{{extra}}", "")
    )


async def _call_ollama(prompt: str) -> str:
    import httpx
    base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.environ.get("OLLAMA_MODEL", "gemma3:12b")
    async with httpx.AsyncClient(timeout=600.0) as client:
        resp = await client.post(
            f"{base_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        resp.raise_for_status()
        return resp.json().get("response", "")


async def _call_claude(prompt: str) -> str:
    import anthropic
    api_key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("CLAUDE_API_KEY / ANTHROPIC_API_KEY no configurada")
    client = anthropic.Anthropic(api_key=api_key)
    model = os.environ.get("CLAUDE_MODEL", "claude-opus-4-6")
    message = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


async def _call_gemini(prompt: str) -> str:
    """Calls `gemini analyze` CLI if available."""
    proc = await asyncio.create_subprocess_exec(
        "gemini", "analyze",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(prompt.encode("utf-8"))
    if proc.returncode != 0:
        raise RuntimeError(f"gemini CLI falló: {stderr.decode()}")
    return stdout.decode("utf-8")


async def _call_offline(prompt: str) -> str:
    """Stub provider for CI/smoke tests."""
    return (
        "# DIAGNÓSTICO (fixture offline)\n\n"
        "## 1. Resumen Ejecutivo\nLorem ipsum IPD 3.9 brecha 40:1.\n\n"
        "## 2. Análisis por Plataforma\nInstagram 2231 seguidores engagement 7.74%.\n\n"
        + "\n".join(f"## {i}. Sección {i}\nTexto dummy." for i in range(3, 11))
        + "\n\nResponsable: community manager. Lunes 20:00 hrs. Meta 30 días: 5 reels/semana. $5000 mxn."
    )


PROVIDERS = {
    "ollama": _call_ollama,
    "claude": _call_claude,
    "gemini": _call_gemini,
    "offline": _call_offline,
}


async def run(
    prompt_path: Path,
    test_case_path: Path,
    providers: list[str],
    iteration: int,
    out_dir: Path | None = None,
) -> dict[str, Path]:
    prompt_template = prompt_path.read_text(encoding="utf-8")
    test_case = json.loads(test_case_path.read_text(encoding="utf-8"))
    prompt = _render_prompt(prompt_template, test_case)

    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir = out_dir or (OUT_ROOT / date_str)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Persist the exact prompt used
    (out_dir / f"iter_{iteration:02d}_prompt.md").write_text(prompt, encoding="utf-8")

    results: dict[str, Path] = {}
    tasks = []
    for p in providers:
        if p not in PROVIDERS:
            print(f"[warn] provider desconocido: {p}")
            continue
        tasks.append((p, asyncio.create_task(PROVIDERS[p](prompt))))

    for provider, task in tasks:
        try:
            text = await task
            path = out_dir / f"iter_{iteration:02d}_{provider}.md"
            path.write_text(text, encoding="utf-8")
            results[provider] = path
            print(f"[ok] {provider} → {path.relative_to(BASE)}")
        except Exception as e:
            err_path = out_dir / f"iter_{iteration:02d}_{provider}.error.txt"
            err_path.write_text(f"{type(e).__name__}: {e}", encoding="utf-8")
            print(f"[error] {provider} → {err_path.name}")

    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--test-case", required=True, type=Path)
    parser.add_argument("--providers", default="offline",
                        help="comma-separated: ollama,claude,gemini,offline")
    parser.add_argument("--iteration", type=int, default=0)
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    providers = [p.strip() for p in args.providers.split(",") if p.strip()]
    asyncio.run(run(
        prompt_path=args.prompt,
        test_case_path=args.test_case,
        providers=providers,
        iteration=args.iteration,
        out_dir=args.out_dir,
    ))


if __name__ == "__main__":
    main()
