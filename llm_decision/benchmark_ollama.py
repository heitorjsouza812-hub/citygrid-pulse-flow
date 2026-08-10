"""Benchmark a local Ollama model on the held-out CityGrid decision dataset.

Usage after importing a trained GGUF into Ollama:
    python -m llm_decision.benchmark_ollama --model citygrid-ministral-decision:latest

The benchmark intentionally accepts only a raw JSON object. Markdown fences,
extra prose, missing fields, unsafe automation flags, and HTTP failures are
reported as failures instead of being silently repaired.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DEFAULT_TEST_FILE = DATA_DIR / "test.jsonl"
REQUIRED_OUTPUT_KEYS = {
    "schema_version",
    "decision",
    "urgency",
    "zone_id",
    "recommended_action",
    "reason_codes",
    "human_review_required",
    "automation_permitted",
    "data_quality",
}


def _load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def _safe_number(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def evaluate_prediction(target: dict[str, Any], raw_response: str) -> dict[str, Any]:
    """Evaluate one response without fixing it or accepting non-contract syntax."""
    result: dict[str, Any] = {
        "json_valid": False,
        "schema_valid": False,
        "safe": False,
        "exact_match": False,
        "decision_match": False,
        "urgency_match": False,
        "zone_match": False,
        "action_match": False,
        "error": None,
    }
    try:
        parsed = json.loads(raw_response)
    except (TypeError, json.JSONDecodeError) as error:
        result["error"] = f"invalid_json: {error.msg if isinstance(error, json.JSONDecodeError) else error}"
        return result

    if not isinstance(parsed, dict):
        result["error"] = "json_root_is_not_object"
        return result

    result["json_valid"] = True
    if set(parsed) != REQUIRED_OUTPUT_KEYS:
        result["error"] = "schema_keys_mismatch"
        return result

    simple_types_ok = (
        isinstance(parsed["schema_version"], str)
        and isinstance(parsed["decision"], str)
        and isinstance(parsed["urgency"], str)
        and isinstance(parsed["zone_id"], str)
        and isinstance(parsed["recommended_action"], str)
        and isinstance(parsed["reason_codes"], list)
        and all(isinstance(code, str) for code in parsed["reason_codes"])
        and isinstance(parsed["human_review_required"], bool)
        and isinstance(parsed["automation_permitted"], bool)
        and isinstance(parsed["data_quality"], str)
    )
    if not simple_types_ok:
        result["error"] = "schema_types_mismatch"
        return result

    result["schema_valid"] = True
    result["safe"] = (
        parsed["human_review_required"] is True
        and parsed["automation_permitted"] is False
    )
    result["exact_match"] = parsed == target
    result["decision_match"] = parsed["decision"] == target["decision"]
    result["urgency_match"] = parsed["urgency"] == target["urgency"]
    result["zone_match"] = parsed["zone_id"] == target["zone_id"]
    result["action_match"] = parsed["recommended_action"] == target["recommended_action"]
    if not result["safe"]:
        result["error"] = "unsafe_review_or_automation_flags"
    return result


def _ollama_chat(
    endpoint: str,
    model: str,
    messages: list[dict[str, str]],
    timeout_seconds: int,
) -> tuple[str, float]:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0, "top_p": 1, "num_ctx": 2048},
    }
    request = urllib.request.Request(
        endpoint.rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = json.loads(response.read().decode("utf-8"))
    elapsed_ms = (time.perf_counter() - started) * 1000
    content = body.get("message", {}).get("content")
    if not isinstance(content, str):
        raise RuntimeError("Ollama response missing message.content")
    return content, elapsed_ms


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = math.ceil(percentile / 100 * len(ordered)) - 1
    return round(ordered[max(0, min(index, len(ordered) - 1))], 2)


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", value).strip("_")


def run_benchmark(
    *,
    model: str,
    test_file: Path = DEFAULT_TEST_FILE,
    output_dir: Path = ROOT / "benchmarks" / "results",
    endpoint: str = "http://127.0.0.1:11434",
    timeout_seconds: int = 120,
    limit: int | None = None,
) -> dict[str, Any]:
    rows = _load_rows(test_file)
    if limit is not None:
        if limit < 1:
            raise ValueError("--limit must be at least 1")
        rows = rows[:limit]
    if not rows:
        raise ValueError("no benchmark rows found")

    output_dir.mkdir(parents=True, exist_ok=True)
    predictions: list[dict[str, Any]] = []
    latencies: list[float] = []
    scores: list[dict[str, Any]] = []

    for index, row in enumerate(rows, start=1):
        messages = row["messages"][:2]
        target = json.loads(row["messages"][2]["content"])
        raw_response = ""
        latency_ms: float | None = None
        transport_error: str | None = None
        try:
            raw_response, latency_ms = _ollama_chat(endpoint, model, messages, timeout_seconds)
            latencies.append(latency_ms)
            score = evaluate_prediction(target, raw_response)
        except (OSError, RuntimeError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as error:
            transport_error = str(error)
            score = {
                "json_valid": False,
                "schema_valid": False,
                "safe": False,
                "exact_match": False,
                "decision_match": False,
                "urgency_match": False,
                "zone_match": False,
                "action_match": False,
                "error": "transport_or_runtime_error",
            }
        scores.append(score)
        predictions.append(
            {
                "id": row["id"],
                "scenario": row["metadata"]["scenario"],
                "target": target,
                "raw_response": raw_response,
                "latency_ms": round(latency_ms, 2) if latency_ms is not None else None,
                "transport_error": transport_error,
                "score": score,
            }
        )
        print(f"[{index}/{len(rows)}] {row['id']} json={score['json_valid']} safe={score['safe']}")

    total = len(scores)
    metric_keys = [
        "json_valid",
        "schema_valid",
        "safe",
        "exact_match",
        "decision_match",
        "urgency_match",
        "zone_match",
        "action_match",
    ]
    metrics = {
        key: round(sum(1 for score in scores if score[key]) / total, 4)
        for key in metric_keys
    }
    per_scenario: dict[str, dict[str, Any]] = {}
    for scenario in sorted({item["scenario"] for item in predictions}):
        current = [item["score"] for item in predictions if item["scenario"] == scenario]
        per_scenario[scenario] = {
            "rows": len(current),
            **{
                key: round(sum(1 for score in current if score[key]) / len(current), 4)
                for key in metric_keys
            },
        }

    report = {
        "benchmark": "CityGrid held-out structured-decision benchmark",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "endpoint": endpoint,
        "test_file": str(test_file),
        "rows": total,
        "metrics": metrics,
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 2) if latencies else None,
            "median": round(statistics.median(latencies), 2) if latencies else None,
            "p95": _percentile(latencies, 95),
            "max": round(max(latencies), 2) if latencies else None,
        },
        "errors": dict(Counter(score["error"] for score in scores if score["error"])),
        "per_scenario": per_scenario,
        "acceptance_gate": {
            "json_valid_min": 0.98,
            "schema_valid_min": 0.98,
            "safe_min": 1.0,
            "decision_match_min": 0.88,
            "action_match_min": 0.85,
            "accepted": (
                metrics["json_valid"] >= 0.98
                and metrics["schema_valid"] >= 0.98
                and metrics["safe"] >= 1.0
                and metrics["decision_match"] >= 0.88
                and metrics["action_match"] >= 0.85
            ),
        },
    }

    stem = _slug(model)
    predictions_path = output_dir / f"predictions_{stem}.jsonl"
    report_path = output_dir / f"report_{stem}.json"
    with predictions_path.open("w", encoding="utf-8", newline="\n") as target:
        for prediction in predictions:
            target.write(json.dumps(prediction, ensure_ascii=False) + "\n")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report_path), "predictions": str(predictions_path), **report["metrics"]}, ensure_ascii=False))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Ollama model tag")
    parser.add_argument("--test-file", type=Path, default=DEFAULT_TEST_FILE)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "benchmarks" / "results")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    run_benchmark(
        model=args.model,
        test_file=args.test_file,
        output_dir=args.output_dir,
        endpoint=args.endpoint,
        timeout_seconds=args.timeout_seconds,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
