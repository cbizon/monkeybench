from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

from brunner import (
    ArtifactPolicy,
    AssessmentDefinition,
    AssessmentReport,
    BenchmarkDefinition,
    ChallengeDefinition,
    EvaluationDefinition,
    ProviderSettings,
    ReferenceDefinition,
    RuntimeDefaults,
)

from monkeybench.campaign_matrix import (
    DEFAULT_CODEX_BASE_URL,
    DEFAULT_CODEX_ENVIRONMENT_KEY,
    DEFAULT_CODEX_PROVIDER_ID,
    DEFAULT_CODEX_PROVIDER_NAME,
)
from monkeybench.images import evaluator_image


ROOT = Path(
    os.environ.get(
        "MONKEYBENCH_ROOT",
        Path(__file__).resolve().parents[2],
    )
).resolve()
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
                "python",
                "-m",
                "monkeybench.materialize_challenge",
            ),
            materialize_timeout_seconds=5 * 60,
        ),
        evaluation=EvaluationDefinition(
            command=("python", "-m", "monkeybench.evaluator"),
            timeout_seconds=15 * 60,
            image=evaluator_image(),
            primary_report="evaluation/detection-report.html",
            cpu_request="500m",
            cpu_limit="2",
            memory_request="512Mi",
            memory_limit="2Gi",
            ephemeral_storage_request="256Mi",
            ephemeral_storage_limit="1Gi",
        ),
        reference=ReferenceDefinition(
            root=ROOT / "reference",
            validate_command=(
                "python",
                "-m",
                "monkeybench.reference_validation",
            ),
        ),
        artifacts=ArtifactPolicy(
            collect_evaluated_artifacts=True,
            max_collection_bytes=512 * 1024 * 1024,
            max_diagnostic_collection_bytes=128 * 1024 * 1024,
        ),
        runtime=RuntimeDefaults(
            timeout_seconds=12 * 60 * 60,
            finalization_seconds=10 * 60,
            retry_initial_seconds=15,
            retry_max_seconds=5 * 60,
            provider_exit_grace_seconds=60,
            backend_shutdown_grace_seconds=2 * 60,
            max_attempts=10,
            max_activity_interval_seconds=60 * 60,
            submission_poll_seconds=2,
        ),
    )


def build_reviewed_definition() -> BenchmarkDefinition:
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
            model=DEFAULT_REVIEWER_MODEL,
            effort=DEFAULT_REVIEWER_EFFORT,
            provider_id=DEFAULT_CODEX_PROVIDER_ID,
            provider_name=DEFAULT_CODEX_PROVIDER_NAME,
            base_url=DEFAULT_CODEX_BASE_URL,
            environment_key=DEFAULT_CODEX_ENVIRONMENT_KEY,
        ),
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
