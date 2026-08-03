from __future__ import annotations

import pytest

from monkeybench.matching import match_points, pixel_distance


def point(x: float, y: float = 0.0) -> dict[str, float]:
    return {"x": x, "y": y}


def test_pixel_distance_uses_original_image_dimensions() -> None:
    distance = pixel_distance(
        point(0.25, 0.5),
        point(0.20, 0.40),
        width=1000,
        height=500,
    )

    assert distance == pytest.approx(50 * 2**0.5)


def test_matching_maximizes_cardinality_before_distance() -> None:
    predictions = [point(0.02), point(0.0)]
    references = [point(0.0), point(0.04)]

    matches = match_points(
        predictions,
        references,
        width=100,
        height=100,
        tolerance_px=2.1,
    )

    assert {(prediction, reference) for prediction, reference, _ in matches} == {
        (0, 1),
        (1, 0),
    }


def test_matching_minimizes_distance_with_equal_cardinality() -> None:
    predictions = [point(0.01), point(0.09)]
    references = [point(0.0), point(0.10)]

    matches = match_points(
        predictions,
        references,
        width=100,
        height=100,
        tolerance_px=20,
    )

    assert [(prediction, reference) for prediction, reference, _ in matches] == [
        (0, 0),
        (1, 1),
    ]


def test_matching_rejects_points_outside_tolerance() -> None:
    matches = match_points(
        [point(0.5)],
        [point(0.0)],
        width=100,
        height=100,
        tolerance_px=30,
    )

    assert matches == []
