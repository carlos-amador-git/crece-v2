#!/usr/bin/env python3
"""T0.6 — Coolify Ollama latency benchmark (gemma3:12b real inference)."""
from __future__ import annotations

import json
import statistics
import time
import urllib.request
from pathlib import Path

ENDPOINT = "http://163.245.208.96:11434"
MODEL = "gemma3:12b"
OUT = Path(__file__).parent.parent / "output" / "coolify_latencies.json"
OUT.parent.mkdir(parents=True, exist_ok=True)

PROMPT = (
    "Clasifica en una palabra el tono de este comentario político: "
    "\"Corruptazo el hdp\". Responde SOLO con una palabra."
)


def call(prompt: str, *, num_predict: int = 30, timeout: int = 120) -> tuple[float, str, dict | None]:
    """Return (elapsed_seconds, response_text, raw_json_or_None)."""
    body = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.0, "num_predict": num_predict, "seed": 42},
    }).encode()
    req = urllib.request.Request(
        f"{ENDPOINT}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode())
        elapsed = time.perf_counter() - t0
        return elapsed, raw.get("response", "").strip(), raw
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return elapsed, f"ERR:{exc}", None


def main() -> None:
    print("=== Ping /api/tags ===")
    pings = []
    for i in range(5):
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(f"{ENDPOINT}/api/tags", timeout=10) as r:
                r.read()
            dt = time.perf_counter() - t0
            pings.append(dt)
            print(f"  ping_{i+1}={dt*1000:.1f}ms")
        except Exception as e:
            print(f"  ping_{i+1}=ERR:{e}")

    print("\n=== Warm-up inference (1 call) ===")
    warm_t, warm_resp, _ = call(PROMPT, num_predict=10, timeout=180)
    print(f"  warmup={warm_t:.2f}s  resp=\"{warm_resp[:60]}\"")

    print("\n=== Inference benchmark (10 calls) ===")
    runs = []
    for i in range(10):
        et, resp, raw = call(PROMPT, num_predict=30, timeout=300)
        eval_count = raw.get("eval_count") if raw else None
        eval_dur_ns = raw.get("eval_duration") if raw else None
        tps = None
        if eval_count and eval_dur_ns:
            tps = eval_count / (eval_dur_ns / 1e9)
        runs.append({
            "iter": i + 1,
            "elapsed_s": et,
            "response": resp[:80],
            "eval_count": eval_count,
            "tokens_per_s": tps,
        })
        print(f"  run_{i+1}={et:.2f}s  tok/s={tps:.1f}" if tps else f"  run_{i+1}={et:.2f}s")

    times = [r["elapsed_s"] for r in runs if not r["response"].startswith("ERR")]
    tps_vals = [r["tokens_per_s"] for r in runs if r["tokens_per_s"]]
    stats = {
        "model": MODEL,
        "endpoint": ENDPOINT,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ping_ms": {
            "min": min(p * 1000 for p in pings) if pings else None,
            "median": statistics.median(p * 1000 for p in pings) if pings else None,
            "max": max(p * 1000 for p in pings) if pings else None,
        },
        "warmup_s": warm_t,
        "inference_s": {
            "n": len(times),
            "min": min(times) if times else None,
            "p50": statistics.median(times) if times else None,
            "p95": sorted(times)[int(0.95 * len(times)) - 1] if len(times) >= 2 else None,
            "max": max(times) if times else None,
            "mean": statistics.mean(times) if times else None,
        },
        "tokens_per_s": {
            "p50": statistics.median(tps_vals) if tps_vals else None,
            "mean": statistics.mean(tps_vals) if tps_vals else None,
        },
        "runs": runs,
    }
    OUT.write_text(json.dumps(stats, indent=2, ensure_ascii=False))
    print(f"\n=== Stats ===")
    print(f"Ping p50: {stats['ping_ms']['median']:.1f}ms")
    print(f"Inference: min={stats['inference_s']['min']:.2f}s  p50={stats['inference_s']['p50']:.2f}s  p95={stats['inference_s']['p95']}s")
    print(f"Tokens/s p50: {stats['tokens_per_s']['p50']:.1f}" if stats['tokens_per_s']['p50'] else "Tokens/s: N/A")
    print(f"Saved: {OUT}")


if __name__ == "__main__":
    main()
