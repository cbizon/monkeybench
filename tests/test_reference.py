from __future__ import annotations

from collections import Counter
from pathlib import Path

from monkeybench.reference_validation import (
    EXPECTED_COUNTS,
    validate_reference,
)


ROOT = Path(__file__).resolve().parents[1]


def test_trusted_reference_matches_source_metadata(
    expected_reference: dict,
) -> None:
    validate_reference(ROOT / "reference")

    counts = Counter(
        cell["cell_type"]
        for image in expected_reference["images"]
        for cell in image["cells"]
    )
    counts.setdefault("basophil", 0)
    assert counts == EXPECTED_COUNTS
    assert sum(counts.values()) == 50
    assert expected_reference["matching_tolerance_px"] == 30
