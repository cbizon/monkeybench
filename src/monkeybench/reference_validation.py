from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

from monkeybench.scoring import CELL_TYPES


EXPECTED_IMAGE_IDS = tuple("ABCDEFGHIJKLMN")
EXPECTED_COUNTS = Counter(
    {
        "neutrophil": 34,
        "eosinophil": 9,
        "lymphocyte": 5,
        "monocyte": 2,
        "basophil": 0,
    }
)


def validate_reference(reference_root: Path) -> None:
    expected = json.loads(
        (reference_root / "expected-cells.json").read_text()
    )
    source = json.loads(
        (reference_root / "source-subjects.json").read_text()
    )
    expected_images = expected["images"]
    source_images = source["subjects"]
    expected_ids = tuple(image["image_id"] for image in expected_images)
    source_ids = tuple(image["image_id"] for image in source_images)
    if expected_ids != EXPECTED_IMAGE_IDS or source_ids != EXPECTED_IMAGE_IDS:
        raise ValueError(
            f"unexpected image IDs: expected={expected_ids}, source={source_ids}"
        )
    if expected["matching_tolerance_px"] <= 0:
        raise ValueError("matching tolerance must be positive")

    observed_counts: Counter[str] = Counter()
    for expected_image, source_image in zip(
        expected_images,
        source_images,
        strict=True,
    ):
        if (
            expected_image["width"] != source_image["width"]
            or expected_image["height"] != source_image["height"]
        ):
            raise ValueError(
                f"image dimensions differ for {expected_image['image_id']}"
            )
        cell_counts = Counter(
            cell["cell_type"] for cell in expected_image["cells"]
        )
        unknown_types = set(cell_counts) - set(CELL_TYPES)
        if unknown_types:
            raise ValueError(
                f"unknown cell types in {expected_image['image_id']}: "
                f"{sorted(unknown_types)}"
            )
        if cell_counts != Counter(source_image["counts"]):
            raise ValueError(
                f"source counts differ for {expected_image['image_id']}: "
                f"{cell_counts} != {source_image['counts']}"
            )
        for cell in expected_image["cells"]:
            if not 0 <= cell["x"] <= 1 or not 0 <= cell["y"] <= 1:
                raise ValueError(
                    f"out-of-range coordinate in {expected_image['image_id']}"
                )
            if (
                abs(
                    cell["x"] * expected_image["width"] - cell["x_px"]
                )
                > 0.001
            ):
                raise ValueError(
                    f"x coordinate mismatch in {expected_image['image_id']}"
                )
            if (
                abs(
                    cell["y"] * expected_image["height"] - cell["y_px"]
                )
                > 0.001
            ):
                raise ValueError(
                    f"y coordinate mismatch in {expected_image['image_id']}"
                )
        answer_image = (
            reference_root
            / "answer-images"
            / f"{expected_image['image_id']}.jpg"
        )
        if not answer_image.is_file():
            raise ValueError(f"missing answer image: {answer_image}")
        observed_counts.update(cell_counts)

    for cell_type in CELL_TYPES:
        observed_counts.setdefault(cell_type, 0)
    if observed_counts != EXPECTED_COUNTS:
        raise ValueError(
            f"aggregate counts differ: {observed_counts} != {EXPECTED_COUNTS}"
        )


def main() -> int:
    root_value = os.environ.get("BRUNNER_REFERENCE_ROOT")
    reference_root = (
        Path(root_value).resolve() if root_value else Path.cwd().resolve()
    )
    validate_reference(reference_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
