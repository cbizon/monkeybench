from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from brunner.contract import load_output_contract
from brunner.evaluation import evaluate_trial
from brunner.trial import TrialIdentity, create_trial

from monkeybench.definition import build_definition
from monkeybench.evaluator import main as evaluator_main


def definition_without_materializer():
    definition = build_definition()
    return replace(
        definition,
        challenge=replace(
            definition.challenge,
            materialize_command=(),
        ),
    )


def write_submission(
    trial: Path,
    detections: dict,
) -> None:
    submission = trial / "workspace/submission"
    submission.mkdir()
    (submission / "cell-detections.json").write_text(
        json.dumps(detections, indent=2) + "\n"
    )
    (submission / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "detections": "cell-detections.json",
            }
        )
        + "\n"
    )
    (submission / "run-status.json").write_text(
        json.dumps(
            {
                "status": "complete",
                "submission_manifest": "submission/manifest.json",
                "completed_units": ["classify-practice-images"],
                "limitations": [],
            }
        )
        + "\n"
    )


def test_perfect_trial_evaluates_end_to_end(
    tmp_path: Path,
    monkeypatch,
    perfect_detections: dict,
) -> None:
    monkeypatch.delenv("MONKEYBENCH_EVALUATOR_IMAGE", raising=False)
    definition = definition_without_materializer()
    contract = load_output_contract(definition.contract_path)
    trial = create_trial(
        definition,
        contract,
        tmp_path / "tests",
        TrialIdentity(
            test_id="perfect",
            provider="codex",
            model="test-model",
            effort=None,
        ),
    )
    write_submission(trial, perfect_detections)

    result = evaluate_trial(definition, contract, trial)

    assert result["status"] == "complete"
    assert result["evaluator_return_code"] == 0
    assert result["summary"]["typing"]["correct"] == 50
    assert result["metrics"]["localization"]["total"] == {
        "true_positives": 50,
        "false_positives": 0,
        "false_negatives": 0,
    }
    assert result["metrics"]["typing"]["accuracy"] == 1.0
    assert (
        result["submission"]["artifacts"][0]["artifact_id"]
        == "cell-detections"
    )
    assert (trial / "evaluation/diagnostics.json").is_file()
    report = trial / "evaluation/detection-typing-report.html"
    assert report.is_file()
    report_text = report.read_text()
    assert "Confusion matrix" in report_text
    assert "True positives" in report_text
    assert (trial / "evaluation/run-report.html").is_file()


def test_evaluator_main_uses_brunner_environment(
    tmp_path: Path,
    monkeypatch,
    perfect_detections: dict,
) -> None:
    monkeypatch.delenv("MONKEYBENCH_EVALUATOR_IMAGE", raising=False)
    definition = definition_without_materializer()
    contract = load_output_contract(definition.contract_path)
    trial = create_trial(
        definition,
        contract,
        tmp_path / "tests",
        TrialIdentity(
            test_id="direct-evaluator",
            provider="codex",
            model="test-model",
            effort=None,
        ),
    )
    write_submission(trial, perfect_detections)
    results_path = trial / "evaluation/direct-results.json"
    environment = {
        "BRUNNER_TRIAL_ROOT": trial,
        "BRUNNER_WORKSPACE": trial / "workspace",
        "BRUNNER_OUTPUT_CONTRACT": definition.contract_path,
        "BRUNNER_CONTRACT_SHA256": contract.sha256,
        "BRUNNER_EVALUATION_RESULTS": results_path,
        "BRUNNER_REFERENCE_ROOT": definition.reference.root,
        "BRUNNER_REFERENCE_MANIFEST": (
            definition.reference.root
            / definition.reference.manifest_path
        ),
    }
    for name, path in environment.items():
        monkeypatch.setenv(name, str(path))

    assert evaluator_main() == 0

    result = json.loads(results_path.read_text())
    assert result["status"] == "complete"
    assert result["metrics"]["typing"]["accuracy"] == 1.0
    assert result["metrics"]["localization"]["total"][
        "true_positives"
    ] == 50
