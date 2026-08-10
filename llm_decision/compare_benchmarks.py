"""Compare baseline and tuned CityGrid Ollama benchmark reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


METRICS = (
    "json_valid",
    "schema_valid",
    "safe",
    "exact_match",
    "decision_match",
    "urgency_match",
    "zone_match",
    "action_match",
)


def read_report(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if "metrics" not in report or "model" not in report:
        raise ValueError(f"not a CityGrid benchmark report: {path}")
    return report


def compare(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    baseline_metrics = baseline["metrics"]
    candidate_metrics = candidate["metrics"]
    deltas = {
        metric: round(float(candidate_metrics[metric]) - float(baseline_metrics[metric]), 4)
        for metric in METRICS
    }
    return {
        "baseline_model": baseline["model"],
        "candidate_model": candidate["model"],
        "rows": {"baseline": baseline["rows"], "candidate": candidate["rows"]},
        "baseline_metrics": {metric: baseline_metrics[metric] for metric in METRICS},
        "candidate_metrics": {metric: candidate_metrics[metric] for metric in METRICS},
        "delta_candidate_minus_baseline": deltas,
        "candidate_acceptance_gate": candidate.get("acceptance_gate", {}),
        "fair_comparison": baseline["rows"] == candidate["rows"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = compare(read_report(args.baseline), read_report(args.candidate))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
