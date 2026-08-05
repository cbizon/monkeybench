from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from monkeybench.analysis import (
    collect_analysis,
    discover_trial_roots,
    write_analysis,
)
from monkeybench.analysis_charts import (
    _paired_effort_values,
    _sort_detection_runs,
    _sort_typing_runs,
    generate_charts,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _make_trial(
    campaign_root: Path,
    test_id: str,
    *,
    include_per_type_typing: bool,
) -> Path:
    trial_root = campaign_root / "collected" / test_id
    _write_json(
        campaign_root / "campaign.json",
        {"campaign_id": "test-campaign"},
    )
    _write_json(
        trial_root / "status.json",
        {
            "test_id": test_id,
            "provider": "codex",
            "model": "gpt-test",
            "effort": "low",
            "status": "complete",
            "created_at": "2026-08-04T12:00:00+00:00",
            "completed_at": "2026-08-04T12:02:00+00:00",
            "attempts": [{"number": 1}],
        },
    )
    confusion = {
        "labels": ["neutrophil", "eosinophil"],
        "correct_type_totals": {"neutrophil": 2, "eosinophil": 1},
        "counts": {
            "neutrophil": {"neutrophil": 2, "eosinophil": 0},
            "eosinophil": {"neutrophil": 1, "eosinophil": 0},
        },
        "total": 3,
    }
    typing_metrics = {
        "accuracy": 2 / 3,
        "correct": 2,
        "evaluated_cells": 3,
        "incorrect": 1,
        "confusion_matrix": confusion,
    }
    if include_per_type_typing:
        typing_metrics["per_cell_type"] = {
            "neutrophil": {
                "accuracy": 1.0,
                "correct": 2,
                "evaluated_cells": 2,
                "incorrect": 0,
            },
            "eosinophil": {
                "accuracy": 0.0,
                "correct": 0,
                "evaluated_cells": 1,
                "incorrect": 1,
            },
        }
    _write_json(
        trial_root / "evaluation" / "results.json",
        {
            "summary": {
                "image_count": 2,
                "reference_count": 4,
                "prediction_count": 4,
                "localization": {
                    "true_positives": 3,
                    "false_positives": 1,
                    "false_negatives": 1,
                },
                "typing": {
                    "accuracy": 2 / 3,
                    "correct": 2,
                    "evaluated_cells": 3,
                    "incorrect": 1,
                },
            },
            "metrics": {
                "localization": {
                    "per_cell_type": {
                        "neutrophil": {
                            "true_positives": 2,
                            "false_negatives": 0,
                            "false_positives": 1,
                        },
                        "eosinophil": {
                            "true_positives": 1,
                            "false_negatives": 1,
                            "false_positives": 0,
                        },
                    }
                },
                "typing": typing_metrics,
            },
        },
    )
    _write_json(
        trial_root / "timing" / "accounting.json",
        {
            "summary": {
                "wall_seconds": 120.0,
                "agent_active_seconds": 100.0,
                "foreground_tool_seconds": 15.0,
                "external_wait_seconds": 0.0,
                "subscription_wait_seconds": 0.0,
                "runner_retry_wait_seconds": 0.0,
                "runner_overhead_seconds": 5.0,
                "unclassified_seconds": 0.0,
                "background_job_seconds": 0.0,
            }
        },
    )
    _write_json(
        trial_root / "usage" / "usage.json",
        {
            "logical_input_tokens": 1000,
            "uncached_input_tokens": 400,
            "cache_read_input_tokens": 600,
            "cache_write_input_tokens": None,
            "output_tokens": 200,
            "reasoning_output_tokens": 50,
            "total_tokens": 1200,
            "usage_record_count": 1,
        },
    )
    return trial_root


def test_collects_run_and_per_type_metrics(tmp_path: Path) -> None:
    campaign_root = tmp_path / "campaign"
    _make_trial(
        campaign_root,
        "codex-gpt-test-low-r01",
        include_per_type_typing=False,
    )

    analysis = collect_analysis([tmp_path])

    assert len(analysis["runs"]) == 1
    run = analysis["runs"][0]
    assert run["run_id"] == "test-campaign/codex-gpt-test-low-r01"
    assert run["detection_precision"] == pytest.approx(0.75)
    assert run["detection_recall"] == pytest.approx(0.75)
    assert run["detection_f1"] == pytest.approx(0.75)
    assert run["agent_active_seconds"] == 100.0
    assert run["inference_time_proxy_seconds"] == 100.0
    assert run["total_tokens"] == 1200

    by_type = {row["cell_type"]: row for row in analysis["cell_types"]}
    assert by_type["neutrophil"]["localization_recall"] == 1.0
    assert by_type["neutrophil"]["typing_accuracy"] == 1.0
    assert by_type["eosinophil"]["localization_recall"] == 0.5
    assert by_type["eosinophil"]["typing_accuracy"] == 0.0
    assert "false_positives" not in by_type["neutrophil"]

    confusion = {
        (row["correct_type"], row["assigned_type"]): row["count"]
        for row in analysis["confusion_matrix"]
    }
    assert confusion[("eosinophil", "neutrophil")] == 1
    assert confusion[("neutrophil", "neutrophil")] == 2


def test_discovers_only_top_level_collected_trials(tmp_path: Path) -> None:
    campaign_root = tmp_path / "campaign"
    trial_root = _make_trial(
        campaign_root,
        "codex-gpt-test-low-r01",
        include_per_type_typing=True,
    )
    nested_results = (
        trial_root
        / "assessments"
        / "review"
        / "evidence"
        / "trial"
        / "evaluation"
        / "results.json"
    )
    _write_json(nested_results, {"summary": {}})

    assert discover_trial_roots([tmp_path]) == [trial_root.resolve()]


def test_writes_tables_and_charts(tmp_path: Path) -> None:
    campaign_root = tmp_path / "campaign"
    _make_trial(
        campaign_root,
        "codex-gpt-test-low-r01",
        include_per_type_typing=True,
    )
    analysis = collect_analysis([tmp_path])
    output_dir = tmp_path / "analysis"
    write_analysis(output_dir, analysis, [tmp_path])

    with (output_dir / "runs.csv").open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1
    assert rows[0]["typing_accuracy"] == str(2 / 3)

    chart_dir = output_dir / "charts"
    chart_dir.mkdir()
    obsolete_chart = chart_dir / "runtime-vs-tokens.png"
    obsolete_chart.write_text("stale", encoding="utf-8")
    generate_charts(output_dir, chart_dir)
    expected = {
        "detection-counts",
        "typing-accuracy",
        "detection-vs-tokens",
        "detection-vs-time",
        "identification-vs-tokens",
        "identification-vs-time",
        "detection-effort-gap",
        "identification-effort-gap",
        "localization-recall-by-type",
        "typing-accuracy-by-type",
    }
    assert (chart_dir / "index.html").is_file()
    assert not obsolete_chart.exists()
    for name in expected:
        assert (chart_dir / f"{name}.png").stat().st_size > 0
        assert (chart_dir / f"{name}.svg").stat().st_size > 0


def test_chart_rankings_use_requested_performance_metrics() -> None:
    runs = [
        {
            "test_id": "second",
            "provider": "codex",
            "model": "model-b",
            "effort": "low",
            "true_positives": "9",
            "false_positives": "0",
            "false_negatives": "1",
            "typing_accuracy": "0.90",
            "typing_correct": "9",
        },
        {
            "test_id": "first",
            "provider": "codex",
            "model": "model-a",
            "effort": "low",
            "true_positives": "10",
            "false_positives": "2",
            "false_negatives": "0",
            "typing_accuracy": "0.80",
            "typing_correct": "8",
        },
    ]

    assert [run["test_id"] for run in _sort_detection_runs(runs)] == [
        "first",
        "second",
    ]
    assert [run["test_id"] for run in _sort_typing_runs(runs)] == [
        "second",
        "first",
    ]


def test_effort_pairs_are_campaign_scoped_and_sorted_by_gap() -> None:
    runs = [
        {
            "campaign_id": "full",
            "provider": "codex",
            "model": "model-a",
            "effort": "low",
            "detection_f1": "0.50",
        },
        {
            "campaign_id": "full",
            "provider": "codex",
            "model": "model-a",
            "effort": "xhigh",
            "detection_f1": "0.90",
        },
        {
            "campaign_id": "full",
            "provider": "codex",
            "model": "model-b",
            "effort": "low",
            "detection_f1": "0.80",
        },
        {
            "campaign_id": "full",
            "provider": "codex",
            "model": "model-b",
            "effort": "xhigh",
            "detection_f1": "0.95",
        },
        {
            "campaign_id": "canary",
            "provider": "codex",
            "model": "model-c",
            "effort": "low",
            "detection_f1": "0.10",
        },
        {
            "campaign_id": "full",
            "provider": "codex",
            "model": "model-c",
            "effort": "xhigh",
            "detection_f1": "1.00",
        },
    ]

    pairs = _paired_effort_values(runs, "detection_f1")

    assert [pair["model"] for pair in pairs] == ["model-a", "model-b"]
    assert pairs[0]["change"] == pytest.approx(0.40)
    assert pairs[1]["gap"] == pytest.approx(0.15)
