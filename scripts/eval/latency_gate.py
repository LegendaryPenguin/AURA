from __future__ import annotations

import argparse
import base64
import io
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from statistics import median
from typing import Any


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((pct / 100.0) * (len(ordered) - 1)))
    return ordered[max(0, min(idx, len(ordered) - 1))]


def _load_image_b64(image_path: Path) -> str:
    raw = image_path.read_bytes()
    if image_path.suffix.lower() in {".jpg", ".jpeg"}:
        return base64.b64encode(raw).decode("ascii")
    try:
        from PIL import Image

        with Image.open(io.BytesIO(raw)) as img:
            out = io.BytesIO()
            img.convert("RGB").save(out, format="JPEG", quality=90)
            return base64.b64encode(out.getvalue()).decode("ascii")
    except Exception:
        return base64.b64encode(raw).decode("ascii")


def _post_analyze(endpoint: str, payload: dict[str, Any], timeout_s: float) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        url=f"{endpoint.rstrip('/')}/analyze",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp is not None else "{}"
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"error": body}
        return exc.code, parsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Run /analyze latency gate.")
    parser.add_argument("--endpoint", default="http://127.0.0.1:9443")
    parser.add_argument("--image", default="tests/fixtures/images/benchmark_object_01.ppm")
    parser.add_argument("--query", default="Identify the main object in this image.")
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--timeout-s", type=float, default=30.0)
    parser.add_argument("--p95-threshold-ms", type=float, default=2000.0)
    parser.add_argument("--output", default="artifacts/latency_gate.json")
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()

    image_b64 = _load_image_b64(Path(args.image))
    latencies_ms: list[float] = []
    errors: list[dict[str, Any]] = []
    cold_ms = 0.0

    total_runs = args.warmups + args.samples
    for i in range(total_runs):
        payload = {
            "request_id": f"latency-gate-{i}",
            "session_id": "latency-gate",
            "image_base64": image_b64,
            "query": args.query,
            "capture_ts_ms": int(time.time() * 1000),
        }
        start = time.perf_counter()
        status, body = _post_analyze(args.endpoint, payload, args.timeout_s)
        elapsed = (time.perf_counter() - start) * 1000.0
        if i == 0:
            cold_ms = elapsed
        if i >= args.warmups:
            latencies_ms.append(elapsed)
        if status != 200:
            errors.append({"status": status, "body": body, "sample": i})

    p50 = median(latencies_ms) if latencies_ms else 0.0
    p95 = _percentile(latencies_ms, 95.0)
    result = {
        "endpoint": args.endpoint,
        "image": args.image,
        "warmups": args.warmups,
        "samples": args.samples,
        "cold_ms": round(cold_ms, 2),
        "warm_p50_ms": round(p50, 2),
        "warm_p95_ms": round(p95, 2),
        "p95_threshold_ms": args.p95_threshold_ms,
        "error_count": len(errors),
        "errors": errors,
        "pass": p95 <= args.p95_threshold_ms and not errors,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))

    if args.enforce and not result["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
