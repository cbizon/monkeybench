from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load_expected() -> dict[str, Any]:
    return json.loads((ROOT / "reference/expected-cells.json").read_text())


def perfect_submission() -> dict[str, Any]:
    expected = load_expected()
    return {
        "schema_version": "1.0",
        "images": [
            {
                "image_id": image["image_id"],
                "detections": [
                    {
                        "x": cell["x"],
                        "y": cell["y"],
                        "cell_type": cell["cell_type"],
                    }
                    for cell in image["cells"]
                ],
            }
            for image in expected["images"]
        ],
    }


@pytest.fixture
def expected_reference() -> dict[str, Any]:
    return load_expected()


@pytest.fixture
def perfect_detections() -> dict[str, Any]:
    return copy.deepcopy(perfect_submission())
