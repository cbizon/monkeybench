from __future__ import annotations

import math
from functools import lru_cache
from typing import Any


Match = tuple[int, int, float]


def pixel_distance(
    prediction: dict[str, Any],
    reference: dict[str, Any],
    *,
    width: int,
    height: int,
) -> float:
    return math.hypot(
        (float(prediction["x"]) - float(reference["x"])) * width,
        (float(prediction["y"]) - float(reference["y"])) * height,
    )


def _is_better(
    candidate: tuple[int, float, tuple[Match, ...]],
    incumbent: tuple[int, float, tuple[Match, ...]],
) -> bool:
    candidate_count, candidate_distance, candidate_pairs = candidate
    incumbent_count, incumbent_distance, incumbent_pairs = incumbent
    if candidate_count != incumbent_count:
        return candidate_count > incumbent_count
    if not math.isclose(candidate_distance, incumbent_distance):
        return candidate_distance < incumbent_distance
    return candidate_pairs < incumbent_pairs


def match_points(
    predictions: list[dict[str, Any]],
    references: list[dict[str, Any]],
    *,
    width: int,
    height: int,
    tolerance_px: float,
) -> list[Match]:
    distances = [
        [
            pixel_distance(
                prediction,
                reference,
                width=width,
                height=height,
            )
            for reference in references
        ]
        for prediction in predictions
    ]

    @lru_cache(maxsize=None)
    def solve(
        prediction_index: int,
        used_references: int,
    ) -> tuple[int, float, tuple[Match, ...]]:
        if prediction_index == len(predictions):
            return 0, 0.0, ()

        best = solve(prediction_index + 1, used_references)
        for reference_index, distance in enumerate(
            distances[prediction_index]
        ):
            reference_bit = 1 << reference_index
            if used_references & reference_bit or distance > tolerance_px:
                continue
            count, total_distance, pairs = solve(
                prediction_index + 1,
                used_references | reference_bit,
            )
            candidate = (
                count + 1,
                total_distance + distance,
                ((prediction_index, reference_index, distance),) + pairs,
            )
            if _is_better(candidate, best):
                best = candidate
        return best

    return list(solve(0, 0)[2])
