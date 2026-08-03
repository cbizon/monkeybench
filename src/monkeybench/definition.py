from __future__ import annotations

import os
import sys
from dataclasses import replace
from pathlib import Path

from brunner import (
    BenchmarkDefinition,
    ChallengeDefinition,
    EvaluationDefinition,
    ProviderSettings,
    QualitativeReviewDefinition,
    ReferenceDefinition,
    RuntimeDefaults,
)


ROOT = Path(__file__).resolve().parents[2]
QUALITATIVE_REVIEW_EVIDENCE = (
    "workspace/PROMPT.md",
    "workspace/inputs/subjects.json",
    "workspace/submission",
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
            timeout_seconds=4 * 60 * 60,
            finalization_seconds=10 * 60,
            retry_initial_seconds=15,
            retry_max_seconds=5 * 60,
            max_attempts=10,
            max_activity_interval_seconds=60 * 60,
            submission_poll_seconds=2,
        ),
    )


def build_reviewed_definition() -> BenchmarkDefinition:
    reviewer_model = os.environ.get("MONKEYBENCH_REVIEWER_MODEL")
    if not reviewer_model:
        raise RuntimeError(
            "MONKEYBENCH_REVIEWER_MODEL is required for the reviewed "
            "benchmark definition"
        )
    reviewer_executable = os.environ.get(
        "MONKEYBENCH_REVIEWER_EXECUTABLE"
    )
    return replace(
        build_definition(),
        qualitative_review=QualitativeReviewDefinition(
            reviewer=ProviderSettings(
                provider="codex",
                model=reviewer_model,
                effort="high",
            ),
            reviewer_executable=reviewer_executable,
            required=False,
            run_if_evaluation_failed=True,
            trial_evidence_paths=QUALITATIVE_REVIEW_EVIDENCE,
            timeout_seconds=60 * 60,
            max_attempts=3,
        ),
    )
