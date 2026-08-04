from __future__ import annotations

import math
from typing import Any

from monkeybench.matching import match_points


CELL_TYPES = (
    "neutrophil",
    "lymphocyte",
    "monocyte",
    "eosinophil",
    "basophil",
)


def _index_images(
    value: dict[str, Any],
    *,
    detections_key: str,
) -> dict[str, dict[str, Any]]:
    images = value.get("images")
    if not isinstance(images, list):
        raise ValueError("images must be a list")
    indexed = {}
    for image in images:
        image_id = str(image["image_id"])
        if image_id in indexed:
            raise ValueError(f"duplicate image ID: {image_id}")
        if detections_key not in image:
            raise ValueError(
                f"image {image_id} has no {detections_key!r} field"
            )
        points = image[detections_key]
        if not isinstance(points, list):
            raise ValueError(
                f"image {image_id} {detections_key!r} must be a list"
            )
        for point in points:
            for coordinate in ("x", "y"):
                value = float(point[coordinate])
                if not math.isfinite(value) or not 0 <= value <= 1:
                    raise ValueError(
                        f"image {image_id} has invalid {coordinate} "
                        f"coordinate: {value}"
                    )
            if point["cell_type"] not in CELL_TYPES:
                raise ValueError(
                    f"image {image_id} has unknown cell type: "
                    f"{point['cell_type']}"
                )
        indexed[image_id] = image
    return indexed


def score_submission(
    observed: dict[str, Any],
    expected: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    observed_images = _index_images(observed, detections_key="detections")
    expected_images = _index_images(expected, detections_key="cells")
    if set(observed_images) != set(expected_images):
        missing = sorted(set(expected_images) - set(observed_images))
        unexpected = sorted(set(observed_images) - set(expected_images))
        raise ValueError(
            f"submission image IDs differ; missing={missing}, "
            f"unexpected={unexpected}"
        )

    tolerance_px = float(expected["matching_tolerance_px"])
    localization_totals = {
        "true_positives": 0,
        "false_positives": 0,
        "false_negatives": 0,
    }
    localization_by_cell_type = {
        cell_type: {
            "true_positives": 0,
            "false_negatives": 0,
        }
        for cell_type in CELL_TYPES
    }
    localization_by_image = {}
    typing_correct = 0
    confusion_counts = {
        correct_type: {
            assigned_type: 0 for assigned_type in CELL_TYPES
        }
        for correct_type in CELL_TYPES
    }
    image_diagnostics = []

    for image_id in sorted(expected_images):
        expected_image = expected_images[image_id]
        observed_image = observed_images[image_id]
        predictions = observed_image["detections"]
        references = expected_image["cells"]
        width = int(expected_image["width"])
        height = int(expected_image["height"])
        matches = match_points(
            predictions,
            references,
            width=width,
            height=height,
            tolerance_px=tolerance_px,
        )
        matched_predictions = {match[0] for match in matches}
        matched_references = {match[1] for match in matches}
        typed_matches = []
        true_positive_markers = []
        image_typing_correct = 0
        for prediction_index, reference_index, distance in matches:
            prediction = predictions[prediction_index]
            reference = references[reference_index]
            type_correct = (
                prediction["cell_type"] == reference["cell_type"]
            )
            typing_correct += int(type_correct)
            image_typing_correct += int(type_correct)
            confusion_counts[reference["cell_type"]][
                prediction["cell_type"]
            ] += 1
            localization_by_cell_type[reference["cell_type"]][
                "true_positives"
            ] += 1
            typed_matches.append(
                {
                    "prediction_index": prediction_index,
                    "reference_index": reference_index,
                    "distance_px": round(distance, 4),
                    "predicted_type": prediction["cell_type"],
                    "expected_type": reference["cell_type"],
                    "type_correct": type_correct,
                }
            )
            true_positive_markers.append(
                {
                    "prediction_index": prediction_index,
                    "reference_index": reference_index,
                    "x": prediction["x"],
                    "y": prediction["y"],
                    "expected_x": reference["x"],
                    "expected_y": reference["y"],
                    "assigned_type": prediction["cell_type"],
                    "expected_type": reference["cell_type"],
                    "type_correct": type_correct,
                }
            )

        false_positive_markers = []
        for prediction_index in sorted(
            set(range(len(predictions))) - matched_predictions
        ):
            prediction = predictions[prediction_index]
            false_positive_markers.append(
                {
                    "prediction_index": prediction_index,
                    "x": prediction["x"],
                    "y": prediction["y"],
                    "assigned_type": prediction["cell_type"],
                }
            )

        false_negative_markers = []
        for reference_index in sorted(
            set(range(len(references))) - matched_references
        ):
            reference = references[reference_index]
            localization_by_cell_type[reference["cell_type"]][
                "false_negatives"
            ] += 1
            false_negative_markers.append(
                {
                    "reference_index": reference_index,
                    "x": reference["x"],
                    "y": reference["y"],
                    "expected_type": reference["cell_type"],
                }
            )

        localization = {
            "true_positives": len(matches),
            "false_positives": len(predictions) - len(matches),
            "false_negatives": len(references) - len(matches),
        }
        localization_by_image[image_id] = localization
        for name, value in localization.items():
            localization_totals[name] += value

        image_diagnostics.append(
            {
                "image_id": image_id,
                "prediction_count": len(predictions),
                "reference_count": len(references),
                "localization": localization,
                "typing": {
                    "evaluated_cells": len(matches),
                    "correct": image_typing_correct,
                    "incorrect": len(matches) - image_typing_correct,
                    "accuracy": (
                        image_typing_correct / len(matches)
                        if matches
                        else None
                    ),
                },
                "matches": typed_matches,
                "markers": {
                    "true_positives": true_positive_markers,
                    "false_positives": false_positive_markers,
                    "false_negatives": false_negative_markers,
                },
                "unmatched_prediction_indexes": [
                    marker["prediction_index"]
                    for marker in false_positive_markers
                ],
                "unmatched_reference_indexes": [
                    marker["reference_index"]
                    for marker in false_negative_markers
                ],
            }
        )

    evaluated_cells = localization_totals["true_positives"]
    correct_type_totals = {
        correct_type: sum(confusion_counts[correct_type].values())
        for correct_type in CELL_TYPES
    }
    assigned_type_totals = {
        assigned_type: sum(
            confusion_counts[correct_type][assigned_type]
            for correct_type in CELL_TYPES
        )
        for assigned_type in CELL_TYPES
    }
    typing_by_cell_type = {}
    for cell_type in CELL_TYPES:
        type_evaluated_cells = correct_type_totals[cell_type]
        correct = confusion_counts[cell_type][cell_type]
        typing_by_cell_type[cell_type] = {
            "evaluated_cells": type_evaluated_cells,
            "correct": correct,
            "incorrect": type_evaluated_cells - correct,
            "accuracy": (
                correct / type_evaluated_cells
                if type_evaluated_cells
                else None
            ),
        }
    confusion_matrix = {
        "rows": "correct_type",
        "columns": "assigned_type",
        "labels": list(CELL_TYPES),
        "counts": confusion_counts,
        "correct_type_totals": correct_type_totals,
        "assigned_type_totals": assigned_type_totals,
        "total": evaluated_cells,
    }

    metrics = {
        "localization": {
            "per_image": localization_by_image,
            "per_cell_type": localization_by_cell_type,
            "total": localization_totals,
        },
        "typing": {
            "evaluated_cells": evaluated_cells,
            "correct": typing_correct,
            "incorrect": evaluated_cells - typing_correct,
            "accuracy": (
                typing_correct / evaluated_cells
                if evaluated_cells
                else None
            ),
            "per_cell_type": typing_by_cell_type,
            "confusion_matrix": confusion_matrix,
        },
    }
    summary = {
        "image_count": len(expected_images),
        "prediction_count": sum(
            len(image["detections"]) for image in observed_images.values()
        ),
        "reference_count": sum(
            len(image["cells"]) for image in expected_images.values()
        ),
        "localization": localization_totals,
        "typing": {
            "evaluated_cells": evaluated_cells,
            "correct": typing_correct,
            "incorrect": evaluated_cells - typing_correct,
            "accuracy": metrics["typing"]["accuracy"],
        },
        "matching_tolerance_px": tolerance_px,
    }
    diagnostics = {
        "schema_version": "1.0",
        "summary": summary,
        "metrics": metrics,
        "images": image_diagnostics,
    }
    return summary, metrics, diagnostics
