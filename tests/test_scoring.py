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
    assert metrics["localization"]["total"] == {
        "true_positives": 50,
        "false_positives": 0,
        "false_negatives": 0,
    }
    assert metrics["localization"]["per_image"]["F"] == {
        "true_positives": 0,
        "false_positives": 0,
        "false_negatives": 0,
    }
    assert metrics["localization"]["per_cell_type"]["neutrophil"] == {
        "true_positives": 34,
        "false_positives": 0,
        "false_negatives": 0,
    }
    assert metrics["localization"]["false_positive_grouping"] == (
        "assigned_type"
    )
    assert metrics["typing"]["accuracy"] == 1.0
    assert metrics["typing"]["correct"] == 50
    assert metrics["typing"]["incorrect"] == 0
    assert metrics["typing"]["confusion_matrix"]["total"] == 50
    assert metrics["typing"]["confusion_matrix"]["counts"]["neutrophil"][
        "neutrophil"
    ] == 34
    assert len(diagnostics["images"]) == 14


def test_wrong_type_preserves_localization_counts_and_updates_confusion_matrix(
    perfect_detections: dict,
    expected_reference: dict,
) -> None:
    correct_type = perfect_detections["images"][0]["detections"][0][
        "cell_type"
    ]
    perfect_detections["images"][0]["detections"][0][
        "cell_type"
    ] = "eosinophil"

    summary, metrics, _ = score_submission(
        perfect_detections,
        expected_reference,
    )

    assert summary["localization"]["true_positives"] == 50
    assert metrics["localization"]["total"] == {
        "true_positives": 50,
        "false_positives": 0,
        "false_negatives": 0,
    }
    assert metrics["typing"]["correct"] == 49
    assert metrics["typing"]["incorrect"] == 1
    assert metrics["typing"]["accuracy"] == pytest.approx(0.98)
    matrix = metrics["typing"]["confusion_matrix"]
    assert matrix["counts"][correct_type][correct_type] == 33
    assert matrix["counts"][correct_type]["eosinophil"] == 1
    assert matrix["correct_type_totals"][correct_type] == 34
    assert matrix["assigned_type_totals"]["eosinophil"] == 10


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
    assert metrics["localization"]["total"] == {
        "true_positives": 49,
        "false_positives": 1,
        "false_negatives": 1,
    }
    assert metrics["localization"]["per_image"]["A"][
        "false_negatives"
    ] == 1
    assert metrics["localization"]["per_image"]["B"][
        "false_positives"
    ] == 1
    assert metrics["typing"]["evaluated_cells"] == 49
    assert metrics["typing"]["correct"] == 49
    assert metrics["typing"]["accuracy"] == 1.0
    matrix = metrics["typing"]["confusion_matrix"]
    assert matrix["assigned_type_totals"]["basophil"] == 0
    assert matrix["total"] == 49
    assert metrics["localization"]["per_cell_type"]["basophil"][
        "false_positives"
    ] == 1
    diagnostics = score_submission(
        perfect_detections,
        expected_reference,
    )[2]
    assert diagnostics["images"][0]["markers"]["false_negatives"]
    assert diagnostics["images"][1]["markers"]["false_positives"] == [
        {
            "prediction_index": 2,
            "x": 0.5,
            "y": 0.5,
            "assigned_type": "basophil",
        }
    ]


def test_typing_accuracy_is_unavailable_without_localized_cells(
    perfect_detections: dict,
    expected_reference: dict,
) -> None:
    for image in perfect_detections["images"]:
        image["detections"] = []

    _, metrics, _ = score_submission(
        perfect_detections,
        expected_reference,
    )

    assert metrics["localization"]["total"] == {
        "true_positives": 0,
        "false_positives": 0,
        "false_negatives": 50,
    }
    assert metrics["typing"]["evaluated_cells"] == 0
    assert metrics["typing"]["accuracy"] is None
    assert metrics["typing"]["confusion_matrix"]["total"] == 0


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
