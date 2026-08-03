from __future__ import annotations

import json

from brunner.evaluator import (
    load_evaluation_input,
    write_evaluation_result,
)

from monkeybench.evaluation_report import (
    render_detection_report,
    render_identification_report,
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
    image_paths = {
        image["image_id"]: (
            evaluation_input.workspace
            / "inputs/images"
            / f"{image['image_id']}.jpg"
        )
        for image in expected["images"]
    }
    detection_report_path = (
        evaluation_input.trial_root / "evaluation/detection-report.html"
    )
    detection_report_path.write_text(
        render_detection_report(
            summary,
            metrics,
            diagnostics,
            image_paths,
        )
    )
    identification_report_path = (
        evaluation_input.trial_root
        / "evaluation/identification-report.html"
    )
    identification_report_path.write_text(
        render_identification_report(summary, metrics)
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
            },
            {
                "path": "evaluation/detection-report.html",
                "media_type": "text/html",
                "title": "White blood cell detection",
                "primary": True,
            },
            {
                "path": "evaluation/identification-report.html",
                "media_type": "text/html",
                "title": "White blood cell identification",
            },
        ],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
