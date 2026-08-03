from __future__ import annotations

import copy
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from brunner.contract import load_output_contract, validate_json
from brunner.errors import ContractError
from brunner.staging import stage_challenge

from monkeybench.definition import (
    DEFAULT_REVIEWER_EFFORT,
    DEFAULT_REVIEWER_MODEL,
    QUALITATIVE_ROOT,
    QUALITATIVE_REVIEW_EVIDENCE,
    build_definition,
    build_reviewed_definition,
)
from monkeybench.remote_agent import DEFAULT_CODEX_BASE_URL


ROOT = Path(__file__).resolve().parents[1]


def artifact_schema() -> dict:
    contract = load_output_contract(ROOT / "output-contract.json")
    return contract.data["artifacts"][0]["json_schema"]


def test_contract_and_definition_validate() -> None:
    definition = build_definition()
    definition.validate()
    contract = load_output_contract(
        definition.contract_path,
        expected_benchmark_id=definition.benchmark_id,
    )

    assert contract.benchmark_id == "monkey-wbc-localization"
    assert contract.work_unit_ids == ("classify-practice-images",)
    assert definition.display_title is None
    assert definition.evaluation.command[0] == sys.executable
    assert definition.challenge.materialize_command == (
        sys.executable,
        "-m",
        "monkeybench.materialize_challenge",
    )
    assert definition.challenge.materialize_timeout_seconds == 5 * 60
    assert definition.runtime.max_attempts == 10
    assert definition.runtime.max_activity_interval_seconds == 60 * 60
    assert definition.runtime.submission_poll_seconds == 2


def test_container_evaluator_uses_container_python(monkeypatch) -> None:
    monkeypatch.setenv(
        "MONKEYBENCH_EVALUATOR_IMAGE",
        "registry.example/monkeybench-evaluator:1.0.0",
    )

    definition = build_definition()

    assert definition.evaluation.image == (
        "registry.example/monkeybench-evaluator:1.0.0"
    )
    assert definition.evaluation.command == (
        "python",
        "-m",
        "monkeybench.evaluator",
    )


def test_reviewed_definition_uses_monkeybench_qualitative_review(
    monkeypatch,
) -> None:
    monkeypatch.setenv("MONKEYBENCH_REVIEWER_MODEL", "review-model")
    monkeypatch.setenv(
        "MONKEYBENCH_REVIEWER_EXECUTABLE",
        "/opt/reviewers/codex",
    )

    definition = build_reviewed_definition()
    definition.validate()

    assert definition.qualitative_review is None
    assert len(definition.assessments) == 1
    assessment = definition.assessments[0]
    assert assessment.assessment_id == "qualitative-review"
    assert assessment.root == QUALITATIVE_ROOT
    assert assessment.reviewer is not None
    assert assessment.reviewer.provider == "codex"
    assert assessment.reviewer.model == "review-model"
    assert assessment.reviewer.effort == "xhigh"
    assert assessment.reviewer.base_url == DEFAULT_CODEX_BASE_URL
    assert assessment.reviewer.environment_key == "AZURE_OPENAI_API_KEY"
    assert assessment.reviewer_executable == "/opt/reviewers/codex"
    assert assessment.required is True
    assert assessment.run_if_evaluation_failed is True
    assert assessment.trial_evidence_paths == QUALITATIVE_REVIEW_EVIDENCE
    assert "workspace" not in assessment.trial_evidence_paths
    assert "evaluation/results.json" in assessment.trial_evidence_paths
    assert "workspace/training/field-guide.json" in (
        assessment.trial_evidence_paths
    )
    assert "workspace/training/videos/README.md" in (
        assessment.trial_evidence_paths
    )
    assert assessment.portable_command_paths is True
    assert assessment.reports[0].path == (
        "evaluation/qualitative-review.html"
    )


def test_reviewed_definition_uses_default_reviewer(monkeypatch) -> None:
    monkeypatch.delenv("MONKEYBENCH_REVIEWER_MODEL", raising=False)
    monkeypatch.delenv("MONKEYBENCH_REVIEWER_EFFORT", raising=False)

    assessment = build_reviewed_definition().assessments[0]

    assert assessment.reviewer is not None
    assert assessment.reviewer.model == DEFAULT_REVIEWER_MODEL
    assert assessment.reviewer.effort == DEFAULT_REVIEWER_EFFORT


def test_artifact_schema_accepts_every_image_once(
    perfect_detections: dict,
) -> None:
    validate_json(
        perfect_detections,
        artifact_schema(),
        label="perfect detections",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("x", -0.01),
        ("y", 1.01),
        ("cell_type", "red_blood_cell"),
    ],
)
def test_artifact_schema_rejects_invalid_detection_values(
    perfect_detections: dict,
    field: str,
    value: object,
) -> None:
    perfect_detections["images"][0]["detections"][0][field] = value

    with pytest.raises(ContractError):
        validate_json(
            perfect_detections,
            artifact_schema(),
            label="invalid detections",
        )


def test_artifact_schema_rejects_duplicate_and_missing_image(
    perfect_detections: dict,
) -> None:
    invalid = copy.deepcopy(perfect_detections)
    invalid["images"][-1] = copy.deepcopy(invalid["images"][0])

    with pytest.raises(ContractError):
        validate_json(
            invalid,
            artifact_schema(),
            label="duplicate image",
        )


def test_staging_excludes_trusted_reference(tmp_path: Path) -> None:
    definition = build_definition()
    definition = replace(
        definition,
        challenge=replace(
            definition.challenge,
            materialize_command=(),
        ),
    )
    contract = load_output_contract(definition.contract_path)
    workspace = tmp_path / "workspace"

    stage_challenge(definition, contract, workspace)

    relative_files = {
        path.relative_to(workspace).as_posix()
        for path in workspace.rglob("*")
        if path.is_file()
    }
    assert "inputs/images/A.jpg" in relative_files
    assert "training/assets/neutrophil-guide.jpg" in relative_files
    assert "PROMPT.md" in relative_files
    assert not any("answer-images" in path for path in relative_files)
    assert not any("expected-cells" in path for path in relative_files)
    assert not any("source-subjects" in path for path in relative_files)
