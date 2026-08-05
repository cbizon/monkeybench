from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

from brunner import (
    AssessmentDefinition,
    AssessmentReport,
    BenchmarkDefinition,
    ChallengeDefinition,
    EvaluationDefinition,
    ProviderSettings,
    ReferenceDefinition,
    RuntimeDefaults,
)

from monkeybench.remote_agent import (
    DEFAULT_CODEX_BASE_URL,
    DEFAULT_CODEX_ENVIRONMENT_KEY,
    DEFAULT_CODEX_PROVIDER_ID,
    DEFAULT_CODEX_PROVIDER_NAME,
)


ROOT = Path(__file__).resolve().parents[2]
QUALITATIVE_ROOT = ROOT / "qualitative"
DEFAULT_REVIEWER_MODEL = "gpt-5.6-sol"
DEFAULT_REVIEWER_EFFORT = "xhigh"
QUALITATIVE_REVIEW_EVIDENCE = (
    "workspace/PROMPT.md",
    "workspace/inputs/subjects.json",
    "workspace/training/README.md",
    "workspace/training/field-guide.json",
    "workspace/training/tutorial.json",
    "workspace/training/videos/README.md",
    "workspace/submission",
    "evaluation/results.json",
    "evaluation/diagnostics.json",
    "transcript",
    "timing",
    "usage",
    "status.json",
)


def build_definition() -> BenchmarkDefinition:
    evaluator_image = os.environ.get("MONKEYBENCH_EVALUATOR_IMAGE")
    evaluator_command = (
        ("python", "-m", "monkeybench.evaluator")
        if evaluator_image
        else (sys.executable, "-m", "monkeybench.evaluator")
    )
    return BenchmarkDefinition(
        benchmark_id="monkey-wbc-localization",
        version="1.0.0",
        root=ROOT,
        contract_path=ROOT / "output-contract.json",
        challenge=ChallengeDefinition(
            root=ROOT / "challenge",
            forbidden_names=(
                "answer-images",
                "expected-cells.json",
                "source-subjects.json",
            ),
            materialize_command=(
                sys.executable,
                "-m",
                "monkeybench.materialize_challenge",
            ),
            materialize_timeout_seconds=5 * 60,
        ),
        evaluation=EvaluationDefinition(
            command=evaluator_command,
            timeout_seconds=15 * 60,
            image=evaluator_image,
        ),
        reference=ReferenceDefinition(
            root=ROOT / "reference",
            validate_command=(
                sys.executable,
                "-m",
                "monkeybench.reference_validation",
            ),
        ),
        runtime=RuntimeDefaults(
            timeout_seconds=12 * 60 * 60,
            finalization_seconds=10 * 60,
            retry_initial_seconds=15,
            retry_max_seconds=5 * 60,
            max_attempts=10,
            max_activity_interval_seconds=60 * 60,
            submission_poll_seconds=2,
        ),
    )


def build_reviewed_definition() -> BenchmarkDefinition:
    reviewer_model = os.environ.get(
        "MONKEYBENCH_REVIEWER_MODEL",
        DEFAULT_REVIEWER_MODEL,
    )
    reviewer_executable = os.environ.get(
        "MONKEYBENCH_REVIEWER_EXECUTABLE"
    )
    reviewer_effort = os.environ.get(
        "MONKEYBENCH_REVIEWER_EFFORT",
        DEFAULT_REVIEWER_EFFORT,
    )
    qualitative_assessment = AssessmentDefinition(
        assessment_id="qualitative-review",
        root=QUALITATIVE_ROOT,
        prompt_path="reviewer-prompt.md",
        rubric_paths=("RUBRIC.md",),
        output_schema_path="qualitative-review.schema.json",
        input_path="evaluation/qualitative-review-input.json",
        output_path="evaluation/qualitative-review.json",
        reviewer=ProviderSettings(
            provider="codex",
            model=reviewer_model,
            effort=reviewer_effort,
            provider_id=os.environ.get(
                "MONKEYBENCH_CODEX_PROVIDER_ID",
                DEFAULT_CODEX_PROVIDER_ID,
            ),
            provider_name=os.environ.get(
                "MONKEYBENCH_CODEX_PROVIDER_NAME",
                DEFAULT_CODEX_PROVIDER_NAME,
            ),
            base_url=os.environ.get(
                "MONKEYBENCH_CODEX_BASE_URL",
                DEFAULT_CODEX_BASE_URL,
            ),
            environment_key=os.environ.get(
                "MONKEYBENCH_CODEX_ENVIRONMENT_KEY",
                DEFAULT_CODEX_ENVIRONMENT_KEY,
            ),
        ),
        reviewer_executable=reviewer_executable,
        render_command=(
            sys.executable,
            str(QUALITATIVE_ROOT / "render.py"),
        ),
        portable_command_paths=True,
        trial_evidence_paths=QUALITATIVE_REVIEW_EVIDENCE,
        reports=(
            AssessmentReport(
                path="evaluation/qualitative-review.html",
                media_type="text/html",
                title="Monkeybench qualitative review",
                primary=True,
            ),
        ),
        required=True,
        run_if_evaluation_failed=True,
        timeout_seconds=60 * 60,
        max_attempts=3,
    )
    return replace(
        build_definition(),
        assessments=(qualitative_assessment,),
    )
