from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_FIELDS = (
    "run_id",
    "campaign_id",
    "test_id",
    "provider",
    "model",
    "effort",
    "status",
    "created_at",
    "completed_at",
    "attempt_count",
    "image_count",
    "reference_count",
    "prediction_count",
    "true_positives",
    "false_positives",
    "false_negatives",
    "detection_precision",
    "detection_recall",
    "detection_f1",
    "typing_evaluated_cells",
    "typing_correct",
    "typing_incorrect",
    "typing_accuracy",
    "wall_seconds",
    "agent_active_seconds",
    "inference_time_proxy_seconds",
    "foreground_tool_seconds",
    "external_wait_seconds",
    "subscription_wait_seconds",
    "runner_retry_wait_seconds",
    "runner_overhead_seconds",
    "unclassified_seconds",
    "background_job_seconds",
    "logical_input_tokens",
    "uncached_input_tokens",
    "cache_read_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
    "usage_record_count",
    "trial_path",
)

CELL_TYPE_FIELDS = (
    "run_id",
    "campaign_id",
    "test_id",
    "provider",
    "model",
    "effort",
    "cell_type",
    "true_positives",
    "false_negatives",
    "reference_cells",
    "localization_recall",
    "typing_evaluated_cells",
    "typing_correct",
    "typing_incorrect",
    "typing_accuracy",
)

CONFUSION_FIELDS = (
    "run_id",
    "campaign_id",
    "test_id",
    "provider",
    "model",
    "effort",
    "correct_type",
    "assigned_type",
    "count",
)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return value


def _ratio(numerator: int | float, denominator: int | float) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


def _detection_f1(
    precision: float | None,
    recall: float | None,
) -> float | None:
    if precision is None or recall is None or precision + recall == 0:
        return None
    return 2 * precision * recall / (precision + recall)


def _campaign_id(trial_root: Path) -> str:
    campaign_root = trial_root.parent.parent
    campaign_path = campaign_root / "campaign.json"
    if campaign_path.is_file():
        campaign = _load_json(campaign_path)
        value = campaign.get("campaign_id")
        if isinstance(value, str) and value:
            return value
    return campaign_root.name


def discover_trial_roots(inputs: Sequence[Path]) -> list[Path]:
    roots: set[Path] = set()
    for input_path in inputs:
        path = input_path.expanduser()
        if (path / "evaluation" / "results.json").is_file():
            roots.add(path.resolve())
            continue
        if not path.exists():
            raise FileNotFoundError(path)
        for results_path in path.glob("**/collected/*/evaluation/results.json"):
            trial_root = results_path.parent.parent
            if trial_root.parent.name == "collected":
                roots.add(trial_root.resolve())
    return sorted(roots)


def _typing_by_type(
    typing_metrics: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    per_cell_type = typing_metrics.get("per_cell_type")
    if isinstance(per_cell_type, dict):
        return per_cell_type

    confusion = typing_metrics.get("confusion_matrix", {})
    counts = confusion.get("counts", {})
    correct_totals = confusion.get("correct_type_totals", {})
    labels = confusion.get("labels", [])
    cell_types = set(labels) | set(correct_totals) | set(counts)
    derived: dict[str, dict[str, Any]] = {}
    for cell_type in sorted(cell_types):
        evaluated = int(correct_totals.get(cell_type, 0))
        correct = int(counts.get(cell_type, {}).get(cell_type, 0))
        derived[cell_type] = {
            "evaluated_cells": evaluated,
            "correct": correct,
            "incorrect": evaluated - correct,
            "accuracy": _ratio(correct, evaluated),
        }
    return derived


def normalize_trial(
    trial_root: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    results = _load_json(trial_root / "evaluation" / "results.json")
    status = _load_json(trial_root / "status.json")
    timing = _load_json(trial_root / "timing" / "accounting.json")
    usage = _load_json(trial_root / "usage" / "usage.json")

    campaign_id = _campaign_id(trial_root)
    test_id = str(status.get("test_id") or trial_root.name)
    run_id = f"{campaign_id}/{test_id}"
    identity = {
        "run_id": run_id,
        "campaign_id": campaign_id,
        "test_id": test_id,
        "provider": status.get("provider"),
        "model": status.get("model"),
        "effort": status.get("effort"),
    }

    summary = results.get("summary", {})
    localization_summary = summary.get("localization", {})
    typing_summary = summary.get("typing", {})
    metrics = results.get("metrics", {})
    localization_metrics = metrics.get("localization", {})
    typing_metrics = metrics.get("typing", {})
    timing_summary = timing.get("summary", timing)

    true_positives = int(localization_summary.get("true_positives", 0))
    false_positives = int(localization_summary.get("false_positives", 0))
    false_negatives = int(localization_summary.get("false_negatives", 0))
    precision = _ratio(true_positives, true_positives + false_positives)
    recall = _ratio(true_positives, true_positives + false_negatives)

    run_row = {
        **identity,
        "status": status.get("status"),
        "created_at": status.get("created_at"),
        "completed_at": status.get("completed_at"),
        "attempt_count": len(status.get("attempts", [])),
        "image_count": summary.get("image_count"),
        "reference_count": summary.get("reference_count"),
        "prediction_count": summary.get("prediction_count"),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "detection_precision": precision,
        "detection_recall": recall,
        "detection_f1": _detection_f1(precision, recall),
        "typing_evaluated_cells": typing_summary.get("evaluated_cells"),
        "typing_correct": typing_summary.get("correct"),
        "typing_incorrect": typing_summary.get("incorrect"),
        "typing_accuracy": typing_summary.get("accuracy"),
        "wall_seconds": timing_summary.get("wall_seconds"),
        "agent_active_seconds": timing_summary.get("agent_active_seconds"),
        "inference_time_proxy_seconds": timing_summary.get(
            "agent_active_seconds"
        ),
        "foreground_tool_seconds": timing_summary.get("foreground_tool_seconds"),
        "external_wait_seconds": timing_summary.get("external_wait_seconds"),
        "subscription_wait_seconds": timing_summary.get(
            "subscription_wait_seconds"
        ),
        "runner_retry_wait_seconds": timing_summary.get(
            "runner_retry_wait_seconds"
        ),
        "runner_overhead_seconds": timing_summary.get("runner_overhead_seconds"),
        "unclassified_seconds": timing_summary.get("unclassified_seconds"),
        "background_job_seconds": timing_summary.get("background_job_seconds"),
        "logical_input_tokens": usage.get("logical_input_tokens"),
        "uncached_input_tokens": usage.get("uncached_input_tokens"),
        "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
        "cache_write_input_tokens": usage.get("cache_write_input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "reasoning_output_tokens": usage.get("reasoning_output_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "usage_record_count": usage.get("usage_record_count"),
        "trial_path": str(trial_root),
    }

    localization_by_type = localization_metrics.get("per_cell_type", {})
    typing_by_type = _typing_by_type(typing_metrics)
    cell_types = sorted(set(localization_by_type) | set(typing_by_type))
    cell_rows = []
    for cell_type in cell_types:
        localization = localization_by_type.get(cell_type, {})
        typing = typing_by_type.get(cell_type, {})
        cell_true_positives = int(localization.get("true_positives", 0))
        cell_false_negatives = int(localization.get("false_negatives", 0))
        reference_cells = cell_true_positives + cell_false_negatives
        cell_rows.append(
            {
                **identity,
                "cell_type": cell_type,
                "true_positives": cell_true_positives,
                "false_negatives": cell_false_negatives,
                "reference_cells": reference_cells,
                "localization_recall": _ratio(
                    cell_true_positives,
                    reference_cells,
                ),
                "typing_evaluated_cells": typing.get("evaluated_cells"),
                "typing_correct": typing.get("correct"),
                "typing_incorrect": typing.get("incorrect"),
                "typing_accuracy": typing.get("accuracy"),
            }
        )

    confusion = typing_metrics.get("confusion_matrix", {})
    counts = confusion.get("counts", {})
    labels = list(confusion.get("labels", []))
    all_types = sorted(
        set(labels)
        | set(counts)
        | {
            assigned_type
            for assigned_counts in counts.values()
            for assigned_type in assigned_counts
        }
    )
    confusion_rows = [
        {
            **identity,
            "correct_type": correct_type,
            "assigned_type": assigned_type,
            "count": int(counts.get(correct_type, {}).get(assigned_type, 0)),
        }
        for correct_type in all_types
        for assigned_type in all_types
    ]
    return run_row, cell_rows, confusion_rows


def collect_analysis(
    inputs: Sequence[Path],
) -> dict[str, list[dict[str, Any]]]:
    trial_roots = discover_trial_roots(inputs)
    runs: list[dict[str, Any]] = []
    cell_types: list[dict[str, Any]] = []
    confusion_matrix: list[dict[str, Any]] = []
    for trial_root in trial_roots:
        run_row, cell_rows, confusion_rows = normalize_trial(trial_root)
        runs.append(run_row)
        cell_types.extend(cell_rows)
        confusion_matrix.extend(confusion_rows)

    sort_key = lambda row: (
        str(row["campaign_id"]),
        str(row["provider"]),
        str(row["model"]),
        str(row["effort"]),
        str(row["test_id"]),
    )
    runs.sort(key=sort_key)
    cell_types.sort(key=lambda row: (*sort_key(row), str(row["cell_type"])))
    confusion_matrix.sort(
        key=lambda row: (
            *sort_key(row),
            str(row["correct_type"]),
            str(row["assigned_type"]),
        )
    )
    return {
        "runs": runs,
        "cell_types": cell_types,
        "confusion_matrix": confusion_matrix,
    }


def _write_csv(
    path: Path,
    fieldnames: Iterable[str],
    rows: Iterable[dict[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_analysis(
    output_dir: Path,
    analysis: dict[str, list[dict[str, Any]]],
    inputs: Sequence[Path],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "runs.csv", RUN_FIELDS, analysis["runs"])
    _write_csv(
        output_dir / "cell_types.csv",
        CELL_TYPE_FIELDS,
        analysis["cell_types"],
    )
    _write_csv(
        output_dir / "confusion_matrix.csv",
        CONFUSION_FIELDS,
        analysis["confusion_matrix"],
    )
    payload = {
        "schema_version": "1.0",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "inputs": [str(path.expanduser().resolve()) for path in inputs],
        **analysis,
    }
    with (output_dir / "analysis.json").open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect Monkeybench metrics across Brunner campaign runs."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        default=[Path("campaign-runs")],
        help="Campaign roots, trial roots, or directories containing campaigns.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis-output"),
        help="Directory for normalized CSV and JSON outputs.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    analysis = collect_analysis(args.inputs)
    if not analysis["runs"]:
        raise SystemExit("No collected Monkeybench evaluation results found.")
    write_analysis(args.output_dir, analysis, args.inputs)
    print(
        f"Collected {len(analysis['runs'])} runs into "
        f"{args.output_dir.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
