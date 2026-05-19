"""Benchmark Gemma3:12b Layer 2 classification via Ollama.

Standalone: no DB writes. Reads sample comments from JSON, sends each through
Ollama /api/generate with build_comment_prompt, measures:
- Wall-time total + per-query latency p50/p95
- TTFT (time-to-first-token) via stream=true
- JSON validity rate
- Tono/target distribution
- Errors

Usage:
  # Sequential (baseline):
  python backend/scripts/benchmark_gemma_layer2.py --samples samples.json --label baseline

  # Concurrent (explota OLLAMA_NUM_PARALLEL):
  python backend/scripts/benchmark_gemma_layer2.py --samples samples.json --label concurrency4 --concurrency 4

Writes report to /tmp/gemma_benchmark_<label>_<ts>.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.nlp.political_llm_prompt import build_comment_prompt, parse_response

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:12b")


async def classify_one(client: httpx.AsyncClient, sample: dict) -> dict:
    """Single classification via streaming /api/generate. Captures TTFT."""
    prompt = build_comment_prompt(
        texto=sample["texto"],
        plataforma=sample.get("plataforma", "instagram"),
        dirigente_nombre=sample.get("dirigente_nombre", "dirigente"),
        rol_politico=sample.get("rol_politico", "oposicion"),
    )
    body = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        "format": "json",
        "options": {"temperature": 0.1, "num_predict": 200},
    }
    t_start = time.perf_counter()
    ttft = None
    chunks: list[str] = []
    try:
        async with client.stream("POST", f"{OLLAMA_URL}/api/generate", json=body, timeout=180.0) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if not line:
                    continue
                if ttft is None:
                    ttft = time.perf_counter() - t_start
                try:
                    part = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "response" in part:
                    chunks.append(part["response"])
                if part.get("done"):
                    break
        raw = "".join(chunks)
        elapsed = time.perf_counter() - t_start
        parsed = parse_response(raw)
        return {
            "id": sample.get("id"),
            "elapsed_s": round(elapsed, 3),
            "ttft_s": round(ttft, 3) if ttft else None,
            "raw_len": len(raw),
            "parsed_ok": parsed is not None,
            "tono": parsed.get("tono") if parsed else None,
            "target": parsed.get("target") if parsed else None,
            "raw_snippet": raw[:200] if parsed is None else None,
        }
    except Exception as e:
        return {
            "id": sample.get("id"),
            "elapsed_s": round(time.perf_counter() - t_start, 3),
            "ttft_s": round(ttft, 3) if ttft else None,
            "parsed_ok": False,
            "error": str(e),
        }


async def run_sequential(samples: list[dict]) -> list[dict]:
    results: list[dict] = []
    async with httpx.AsyncClient() as client:
        for i, s in enumerate(samples, 1):
            res = await classify_one(client, s)
            results.append(res)
            print(
                f"  [{i:3d}/{len(samples)}] {res['elapsed_s']:5.1f}s "
                f"ttft={res.get('ttft_s')} ok={res['parsed_ok']} "
                f"tono={res.get('tono')} target={res.get('target')}",
                flush=True,
            )
    return results


async def run_concurrent(samples: list[dict], concurrency: int) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)
    results: list[dict | None] = [None] * len(samples)
    counter = {"done": 0}

    async with httpx.AsyncClient() as client:
        async def worker(idx: int, s: dict) -> None:
            async with sem:
                res = await classify_one(client, s)
                results[idx] = res
                counter["done"] += 1
                print(
                    f"  [{counter['done']:3d}/{len(samples)}] "
                    f"(slot→{idx:3d}) {res['elapsed_s']:5.1f}s "
                    f"ttft={res.get('ttft_s')} ok={res['parsed_ok']}",
                    flush=True,
                )

        await asyncio.gather(*(worker(i, s) for i, s in enumerate(samples)))
    return [r for r in results if r is not None]


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = min(int(len(s) * p), len(s) - 1)
    return s[k]


async def amain() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", required=True, help="path to JSON file with sample comments")
    ap.add_argument("--label", default="baseline")
    ap.add_argument("--concurrency", type=int, default=1, help="1 = sequential, >1 = asyncio.gather")
    args = ap.parse_args()

    samples = json.loads(Path(args.samples).read_text())
    print(
        f"[{args.label}] n={len(samples)} model={OLLAMA_MODEL} url={OLLAMA_URL} "
        f"concurrency={args.concurrency}",
        flush=True,
    )
    print(
        f"  env: NUM_PARALLEL={os.getenv('OLLAMA_NUM_PARALLEL')} "
        f"KEEP_ALIVE={os.getenv('OLLAMA_KEEP_ALIVE')} "
        f"FLASH_ATTENTION={os.getenv('OLLAMA_FLASH_ATTENTION')}",
        flush=True,
    )

    async with httpx.AsyncClient(timeout=60.0) as warm_client:
        try:
            r = await warm_client.post(
                f"{OLLAMA_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": "ok", "stream": False, "options": {"num_predict": 1}},
            )
            print(f"  warmup status={r.status_code}", flush=True)
        except Exception as e:
            print(f"  warmup FAILED: {e}", flush=True)

    t_start = time.perf_counter()
    if args.concurrency > 1:
        results = await run_concurrent(samples, args.concurrency)
    else:
        results = await run_sequential(samples)
    t_total = time.perf_counter() - t_start

    ok = sum(1 for r in results if r.get("parsed_ok"))
    latencies = [r["elapsed_s"] for r in results]
    ttfts = [r["ttft_s"] for r in results if r.get("ttft_s") is not None]

    report = {
        "label": args.label,
        "model": OLLAMA_MODEL,
        "url": OLLAMA_URL,
        "concurrency": args.concurrency,
        "env": {
            "OLLAMA_NUM_PARALLEL": os.getenv("OLLAMA_NUM_PARALLEL"),
            "OLLAMA_KEEP_ALIVE": os.getenv("OLLAMA_KEEP_ALIVE"),
            "OLLAMA_FLASH_ATTENTION": os.getenv("OLLAMA_FLASH_ATTENTION"),
        },
        "n": len(samples),
        "wall_time_s": round(t_total, 2),
        "throughput_qps": round(len(samples) / t_total, 3),
        "latency_p50_s": round(percentile(latencies, 0.50), 3),
        "latency_p95_s": round(percentile(latencies, 0.95), 3),
        "ttft_p50_s": round(percentile(ttfts, 0.50), 3) if ttfts else None,
        "ttft_p95_s": round(percentile(ttfts, 0.95), 3) if ttfts else None,
        "json_valid_pct": round(100 * ok / len(samples), 1),
        "errors": [r for r in results if not r.get("parsed_ok")][:5],
        "results": results,
    }

    out = Path(f"/tmp/gemma_benchmark_{args.label}_{int(time.time())}.json")
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print("\n=== SUMMARY ===")
    print(f"  label:        {args.label}  concurrency={args.concurrency}")
    print(f"  wall_time:    {report['wall_time_s']}s  ({report['throughput_qps']} qps)")
    print(f"  latency:      p50={report['latency_p50_s']}s  p95={report['latency_p95_s']}s")
    print(f"  ttft:         p50={report['ttft_p50_s']}s  p95={report['ttft_p95_s']}s")
    print(f"  json_valid:   {report['json_valid_pct']}%  ({ok}/{len(samples)})")
    print(f"  report:       {out}")


if __name__ == "__main__":
    asyncio.run(amain())
