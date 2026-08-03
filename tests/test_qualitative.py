from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from brunner.contract import load_output_contract
from brunner.evaluation import evaluate_trial
from brunner.trial import TrialIdentity, create_trial
from jsonschema import Draft202012Validator

from monkeybench.definition import (
    QUALITATIVE_ROOT,
    build_reviewed_definition,
)


def valid_review() -> dict[str, Any]:
    metric_evidence = {
        "source": "deterministic_evaluation",
        "path": "evaluation/results.json",
        "finding": "The deterministic evaluator reported perfect results.",
    }
    transcript_evidence = {
        "source": "transcript",
        "path": "transcript/events.jsonl",
        "finding": "The agent inspected the supplied images directly.",
    }
    return {
        "schema_version": "1.0",
        "rubric_version": "1.0",
        "transcript_characterization": {
            "approach": "direct_visual_inspection",
            "summary": "The agent inspected and classified each image.",
            "training_material_use": "The field guide was consulted.",
            "image_inspection_strategy": "Each image was inspected directly.",
            "typing_strategy": "Morphology was compared with the field guide.",
            "notable_actions": ["Inspected all fourteen images."],
            "failures_or_retries": [],
            "evidence": [transcript_evidence],
        },
        "localization_characterization": {
            "performance": "perfect",
            "summary": "All reference cells were localized without extras.",
            "error_distribution": "No false positives or false negatives.",
            "evidence": [metric_evidence],
        },
        "typing_characterization": {
            "performance": "perfect",
            "summary": "Every localized cell was typed correctly.",
            "confusion_summary": "The confusion matrix is diagonal.",
            "marginal_summary": (
                "Assigned totals match the correct-type totals."
            ),
            "notable_confusions": [],
            "evidence": [metric_evidence],
        },
        "overall": {
            "bottom_line": (
                "Localization and typing were both perfect in this trial."
            ),
            "strengths": ["Complete localization", "Correct typing"],
            "weaknesses": [],
        },
        "review_limitations": [],
    }


def write_submission(trial: Path, detections: dict[str, Any]) -> None:
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


def write_reviewer(path: Path, review: dict[str, Any]) -> None:
    encoded = json.dumps(review)
    path.write_text(
        f"""#!{sys.executable}
import json
import sys
from pathlib import Path

assert Path("contract/RUBRIC.md").is_file()
assert Path("contract/reviewer-prompt.md").is_file()
assert Path("review-input.json").is_file()
arguments = sys.argv[1:]
output = Path(arguments[arguments.index("--output-last-message") + 1])
result = json.loads({encoded!r})
output.write_text(json.dumps(result))
print(json.dumps({{
    "type": "turn.completed",
    "structured_output": result,
    "usage": {{"input_tokens": 5, "output_tokens": 7, "total_tokens": 12}}
}}))
"""
    )
    path.chmod(0o755)


def test_qualitative_review_schema_accepts_compact_review() -> None:
    schema = json.loads(
        (QUALITATIVE_ROOT / "qualitative-review.schema.json").read_text()
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(valid_review())


def test_qualitative_renderer_writes_escaped_html(tmp_path: Path) -> None:
    trial = tmp_path / "trial"
    evaluation = trial / "evaluation"
    evaluation.mkdir(parents=True)
    review = valid_review()
    review["overall"]["bottom_line"] = "<script>alert('x')</script>"
    output = evaluation / "qualitative-review.json"
    output.write_text(json.dumps(review))
    environment = {
        **os.environ,
        "BRUNNER_ASSESSMENT_OUTPUT": str(output),
        "BRUNNER_TRIAL_ROOT": str(trial),
    }

    subprocess.run(
        [sys.executable, str(QUALITATIVE_ROOT / "render.py")],
        check=True,
        env=environment,
    )

    rendered = (evaluation / "qualitative-review.html").read_text()
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "Transcript characterization" in rendered
    assert "Localization performance" in rendered
    assert "Typing performance" in rendered


def test_reviewed_trial_runs_custom_qualitative_assessment(
    tmp_path: Path,
    monkeypatch,
    perfect_detections: dict[str, Any],
) -> None:
    reviewer = tmp_path / "reviewer"
    write_reviewer(reviewer, valid_review())
    monkeypatch.setenv("MONKEYBENCH_REVIEWER_MODEL", "review-model")
    monkeypatch.setenv("MONKEYBENCH_REVIEWER_EXECUTABLE", str(reviewer))
    definition = build_reviewed_definition()
    definition = replace(
        definition,
        challenge=replace(
            definition.challenge,
            materialize_command=(),
        ),
    )
    contract = load_output_contract(definition.contract_path)
    trial = create_trial(
        definition,
        contract,
        tmp_path / "tests",
        TrialIdentity(
            test_id="qualitative",
            provider="claude",
            model="candidate-model",
            effort="low",
        ),
    )
    write_submission(trial, perfect_detections)

    result = evaluate_trial(definition, contract, trial)

    assert result["status"] == "complete"
    assert result["assessment_status"] == "complete"
    assert result["required_assessments_complete"] is True
    assessment = result["assessments"][0]
    assert assessment["assessment_id"] == "qualitative-review"
    assert assessment["status"] == "complete"
    assert assessment["required"] is True
    assert assessment["usage"]["total_tokens"] == 12
    assert (trial / "evaluation/qualitative-review.json").is_file()
    assert (trial / "evaluation/qualitative-review.html").is_file()
    dossier = (
        trial / "evaluation/qualitative-review-input.json"
    ).read_text()
    assert "candidate-model" not in dossier
