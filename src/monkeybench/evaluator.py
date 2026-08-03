from __future__ import annotations

import json

from brunner.evaluator import (
    load_evaluation_input,
    write_evaluation_result,
)

from monkeybench.scoring import score_submission


def main() -> int:
    evaluation_input = load_evaluation_input()
    if evaluation_input.reference_root is None:
        raise RuntimeError(
            "monkeybench evaluation requires a trusted reference bundle"
        )

    observed = json.loads(
        evaluation_input.artifact("cell-detections").path.read_text()
    )
    expected = json.loads(
        (
            evaluation_input.reference_root / "expected-cells.json"
        ).read_text()
    )
    summary, metrics, diagnostics = score_submission(observed, expected)

    diagnostics_path = (
        evaluation_input.trial_root / "evaluation/diagnostics.json"
    )
    diagnostics_path.write_text(
        json.dumps(diagnostics, indent=2, sort_keys=True) + "\n"
    )
    write_evaluation_result(
        evaluation_input,
        status="complete",
        summary=summary,
        metrics=metrics,
        reports=[
            {
                "path": "evaluation/diagnostics.json",
                "media_type": "application/json",
                "title": "Per-image matching diagnostics",
            }
        ],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
