from __future__ import annotations

import pytest

from monkeybench.scoring import score_submission


def test_perfect_submission_scores_one(
    perfect_detections: dict,
    expected_reference: dict,
) -> None:
    summary, metrics, diagnostics = score_submission(
        perfect_detections,
        expected_reference,
    )

    assert summary["prediction_count"] == 50
    assert summary["reference_count"] == 50
    assert summary["localized_count"] == 50
    assert summary["correctly_typed_count"] == 50
    assert metrics["overall_score"] == 1.0
    assert metrics["localization_f1"] == 1.0
    assert metrics["type_accuracy_on_localized_cells"] == 1.0
    assert metrics["no_wbc_image_accuracy"] == 1.0
    assert metrics["mean_localization_error_px"] == pytest.approx(0.0)
    assert len(diagnostics["images"]) == 14


def test_wrong_type_preserves_localization_score(
    perfect_detections: dict,
    expected_reference: dict,
) -> None:
    perfect_detections["images"][0]["detections"][0][
        "cell_type"
    ] = "eosinophil"

    summary, metrics, _ = score_submission(
        perfect_detections,
        expected_reference,
    )

    assert summary["localized_count"] == 50
    assert summary["correctly_typed_count"] == 49
    assert metrics["localization_f1"] == 1.0
    assert metrics["typed_f1"] == pytest.approx(0.98)
    assert metrics["type_accuracy_on_localized_cells"] == pytest.approx(0.98)


def test_missed_and_spurious_cells_are_separate_errors(
    perfect_detections: dict,
    expected_reference: dict,
) -> None:
    perfect_detections["images"][0]["detections"].pop()
    perfect_detections["images"][1]["detections"].append(
        {"x": 0.5, "y": 0.5, "cell_type": "basophil"}
    )

    summary, metrics, _ = score_submission(
        perfect_detections,
        expected_reference,
    )

    assert summary["prediction_count"] == 50
    assert summary["localized_count"] == 49
    assert summary["correctly_typed_count"] == 49
    assert metrics["localization_precision"] == pytest.approx(0.98)
    assert metrics["localization_recall"] == pytest.approx(0.98)
    assert metrics["typed_f1"] == pytest.approx(0.98)
    assert metrics["per_class"]["basophil"]["prediction_count"] == 1
    assert metrics["per_class"]["basophil"]["reference_count"] == 0


def test_score_rejects_duplicate_image_ids(
    perfect_detections: dict,
    expected_reference: dict,
) -> None:
    perfect_detections["images"][-1]["image_id"] = "A"

    with pytest.raises(ValueError, match="duplicate image ID"):
        score_submission(perfect_detections, expected_reference)


def test_score_rejects_non_finite_coordinates(
    perfect_detections: dict,
    expected_reference: dict,
) -> None:
    perfect_detections["images"][0]["detections"][0]["x"] = float("nan")

    with pytest.raises(ValueError, match="invalid x coordinate"):
        score_submission(perfect_detections, expected_reference)
