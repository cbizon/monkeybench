from __future__ import annotations

import argparse
import heapq
import json
import math
from array import array
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
RING_RADII = range(22, 29)
RING_ANGLES = tuple(range(0, 360, 5))
MIN_CENTER_DISTANCE = 32


def is_overlay_blue(red: int, green: int, blue: int) -> bool:
    return (
        red < 100
        and green > 60
        and blue > 120
        and blue - green > 20
        and green - red > 20
    )


def build_mask(image: Image.Image) -> bytearray:
    pixels = image.convert("RGB").load()
    width, height = image.size
    mask = bytearray(width * height)
    for y in range(height):
        for x in range(width):
            if is_overlay_blue(*pixels[x, y]):
                mask[y * width + x] = 1
    return mask


def ring_offsets() -> tuple[tuple[int, int], ...]:
    offsets = {
        (
            round(radius * math.cos(math.radians(angle))),
            round(radius * math.sin(math.radians(angle))),
        )
        for radius in RING_RADII
        for angle in RING_ANGLES
    }
    return tuple(sorted(offsets))


def hough_votes(
    mask: bytearray,
    width: int,
    height: int,
) -> array[int]:
    votes = array("H", [0]) * (width * height)
    offsets = ring_offsets()
    for index, value in enumerate(mask):
        if not value:
            continue
        y, x = divmod(index, width)
        for offset_x, offset_y in offsets:
            center_x = x - offset_x
            center_y = y - offset_y
            if 0 <= center_x < width and 0 <= center_y < height:
                votes[center_y * width + center_x] += 1
    return votes


def ring_coverage(
    mask: bytearray,
    width: int,
    height: int,
    center_x: int,
    center_y: int,
) -> int:
    covered = 0
    for angle in RING_ANGLES:
        radians = math.radians(angle)
        if any(
            0 <= (x := center_x + round(radius * math.cos(radians))) < width
            and 0 <= (y := center_y + round(radius * math.sin(radians))) < height
            and mask[y * width + x]
            for radius in RING_RADII
        ):
            covered += 1
    return covered


def squared_distance(
    first: tuple[int, int],
    second: tuple[int, int],
) -> int:
    return (first[0] - second[0]) ** 2 + (first[1] - second[1]) ** 2


def detect_centers(
    image: Image.Image,
    expected_count: int,
) -> list[dict[str, int]]:
    if expected_count == 0:
        return []

    width, height = image.size
    mask = build_mask(image)
    votes = hough_votes(mask, width, height)
    peak_indexes = heapq.nlargest(
        max(500, expected_count * 100),
        range(len(votes)),
        key=votes.__getitem__,
    )

    rough_centers: list[tuple[int, int]] = []
    for index in peak_indexes:
        center_y, center_x = divmod(index, width)
        center = (center_x, center_y)
        if all(
            squared_distance(center, existing) >= 10**2
            for existing in rough_centers
        ):
            rough_centers.append(center)

    scored = []
    for rough_x, rough_y in rough_centers:
        refinements = []
        for delta_y in range(-4, 5):
            for delta_x in range(-4, 5):
                center_x = rough_x + delta_x
                center_y = rough_y + delta_y
                if not (0 <= center_x < width and 0 <= center_y < height):
                    continue
                refinements.append(
                    (
                        ring_coverage(
                            mask,
                            width,
                            height,
                            center_x,
                            center_y,
                        ),
                        votes[center_y * width + center_x],
                        center_x,
                        center_y,
                    )
                )
        scored.append(max(refinements))

    selected: list[tuple[int, int, int, int]] = []
    for coverage, vote_count, center_x, center_y in sorted(
        scored,
        reverse=True,
    ):
        center = (center_x, center_y)
        if all(
            squared_distance(center, (existing[2], existing[3]))
            >= MIN_CENTER_DISTANCE**2
            for existing in selected
        ):
            selected.append((coverage, vote_count, center_x, center_y))
        if len(selected) == expected_count:
            break

    if len(selected) != expected_count:
        raise ValueError(
            f"detected {len(selected)} of {expected_count} expected rings"
        )
    return [
        {
            "x_px": center_x,
            "y_px": center_y,
            "coverage": coverage,
            "votes": vote_count,
        }
        for coverage, vote_count, center_x, center_y in sorted(
            selected,
            key=lambda value: (value[3], value[2]),
        )
    ]


def load_expected_counts() -> dict[str, int]:
    source = json.loads(
        (ROOT / "reference/source-subjects.json").read_text()
    )
    return {
        subject["image_id"]: sum(subject["counts"].values())
        for subject in source["subjects"]
    }


def render_debug(
    image: Image.Image,
    centers: list[dict[str, int]],
    destination: Path,
) -> None:
    debug = image.convert("RGB").copy()
    draw = ImageDraw.Draw(debug)
    for index, center in enumerate(centers, start=1):
        x = center["x_px"]
        y = center["y_px"]
        draw.ellipse((x - 30, y - 30, x + 30, y + 30), outline="yellow", width=3)
        draw.text((x + 31, y - 10), str(index), fill="yellow", stroke_width=2)
    destination.parent.mkdir(parents=True, exist_ok=True)
    debug.save(destination, quality=95)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect cyan answer rings in the Zooniverse practice set."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("/tmp/monkeybench-ring-candidates.json"),
    )
    parser.add_argument(
        "--debug-dir",
        type=Path,
        default=Path("/tmp/monkeybench-ring-debug"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    expected_counts = load_expected_counts()
    images = []
    for image_id, expected_count in sorted(expected_counts.items()):
        path = ROOT / f"reference/answer-images/{image_id}.jpg"
        with Image.open(path) as image:
            centers = detect_centers(image, expected_count)
            width, height = image.size
            for center in centers:
                center["x"] = round(center["x_px"] / width, 6)
                center["y"] = round(center["y_px"] / height, 6)
            render_debug(
                image,
                centers,
                args.debug_dir / f"{image_id}.jpg",
            )
        images.append(
            {
                "image_id": image_id,
                "expected_count": expected_count,
                "centers": centers,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {"schema_version": "1.0", "images": images},
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    print(args.output)
    print(args.debug_dir)


if __name__ == "__main__":
    main()
