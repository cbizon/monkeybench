from __future__ import annotations

import math
from collections import Counter
from typing import Any

from monkeybench.matching import match_points


CELL_TYPES = (
    "neutrophil",
    "lymphocyte",
    "monocyte",
    "eosinophil",
    "basophil",
)


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def _f1(true_positives: int, predicted: int, expected: int) -> float:
    denominator = predicted + expected
    return 2 * true_positives / denominator if denominator else 1.0


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
    total_predictions = 0
    total_references = 0
    total_matches = 0
    correct_types = 0
    exact_count_images = 0
    no_wbc_images = 0
    correct_no_wbc_images = 0
    localization_distances = []
    predicted_by_type: Counter[str] = Counter()
    expected_by_type: Counter[str] = Counter()
    correct_by_type: Counter[str] = Counter()
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
        for prediction_index, reference_index, distance in matches:
            prediction = predictions[prediction_index]
            reference = references[reference_index]
            type_correct = (
                prediction["cell_type"] == reference["cell_type"]
            )
            correct_types += int(type_correct)
            if type_correct:
                correct_by_type[reference["cell_type"]] += 1
            localization_distances.append(distance)
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

        total_predictions += len(predictions)
        total_references += len(references)
        total_matches += len(matches)
        exact_count_images += int(len(predictions) == len(references))
        predicted_by_type.update(
            prediction["cell_type"] for prediction in predictions
        )
        expected_by_type.update(
            reference["cell_type"] for reference in references
        )
        if not references:
            no_wbc_images += 1
            correct_no_wbc_images += int(not predictions)

        image_diagnostics.append(
            {
                "image_id": image_id,
                "prediction_count": len(predictions),
                "reference_count": len(references),
                "localization_matches": len(matches),
                "correct_types": sum(
                    match["type_correct"] for match in typed_matches
                ),
                "matches": typed_matches,
                "unmatched_prediction_indexes": sorted(
                    set(range(len(predictions))) - matched_predictions
                ),
                "unmatched_reference_indexes": sorted(
                    set(range(len(references))) - matched_references
                ),
            }
        )

    localization_precision = _ratio(total_matches, total_predictions)
    localization_recall = _ratio(total_matches, total_references)
    localization_f1 = _f1(
        total_matches,
        total_predictions,
        total_references,
    )
    typed_precision = _ratio(correct_types, total_predictions)
    typed_recall = _ratio(correct_types, total_references)
    typed_f1 = _f1(
        correct_types,
        total_predictions,
        total_references,
    )

    per_class = {}
    for cell_type in CELL_TYPES:
        predicted = predicted_by_type[cell_type]
        reference = expected_by_type[cell_type]
        true_positive = correct_by_type[cell_type]
        per_class[cell_type] = {
            "reference_count": reference,
            "prediction_count": predicted,
            "true_positives": true_positive,
            "precision": (
                _ratio(true_positive, predicted) if predicted else None
            ),
            "recall": (
                _ratio(true_positive, reference) if reference else None
            ),
            "f1": (
                _f1(true_positive, predicted, reference)
                if predicted or reference
                else None
            ),
        }

    metrics = {
        "overall_score": typed_f1,
        "localization_precision": localization_precision,
        "localization_recall": localization_recall,
        "localization_f1": localization_f1,
        "type_accuracy_on_localized_cells": _ratio(
            correct_types,
            total_matches,
        ),
        "typed_precision": typed_precision,
        "typed_recall": typed_recall,
        "typed_f1": typed_f1,
        "exact_count_image_accuracy": _ratio(
            exact_count_images,
            len(expected_images),
        ),
        "no_wbc_image_accuracy": _ratio(
            correct_no_wbc_images,
            no_wbc_images,
        ),
        "mean_localization_error_px": (
            sum(localization_distances) / len(localization_distances)
            if localization_distances
            else None
        ),
        "per_class": per_class,
    }
    summary = {
        "prediction_count": total_predictions,
        "reference_count": total_references,
        "localized_count": total_matches,
        "correctly_typed_count": correct_types,
        "image_count": len(expected_images),
        "exact_count_images": exact_count_images,
        "matching_tolerance_px": tolerance_px,
    }
    diagnostics = {
        "schema_version": "1.0",
        "summary": summary,
        "metrics": metrics,
        "images": image_diagnostics,
    }
    return summary, metrics, diagnostics
