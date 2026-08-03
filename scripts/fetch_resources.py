from __future__ import annotations

import hashlib
import json
import re
import shutil
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
API_ROOT = "https://www.zooniverse.org/api"
SUBJECT_SET_ID = "75322"
WORKFLOW_ID = "14984"
PROJECT_ID = "6250"

EXPECTED_IMAGE_IDS = tuple("ABCDEFGHIJKLMN")
EXPECTED_TOTALS = {
    "Basophils": 0,
    "Monocytes": 2,
    "Eosinophils": 9,
    "Lymphocytes": 5,
    "Neutrophils": 34,
}

TRAINING_RESOURCES = {
    "wbc-overview.jpg": (
        "https://panoptes-uploads.zooniverse.org/"
        "project_attached_image/ba7ceef9-6c0f-411d-bcea-949a7540e761.jpeg"
    ),
    "basophil-guide.jpg": (
        "https://panoptes-uploads.zooniverse.org/"
        "project_attached_image/9b0f8ec2-63d2-4d3b-96da-c70fccb51360.jpeg"
    ),
    "eosinophil-guide.jpg": (
        "https://panoptes-uploads.zooniverse.org/"
        "project_attached_image/c84951a8-4e13-48af-a616-91673a8f380d.jpeg"
    ),
    "lymphocyte-guide.jpg": (
        "https://panoptes-uploads.zooniverse.org/"
        "project_attached_image/170d5184-8e2b-446e-b601-cf9ebc71e07e.jpeg"
    ),
    "monocyte-guide.jpg": (
        "https://panoptes-uploads.zooniverse.org/"
        "project_attached_image/ec8c4da4-cd56-4e16-8cca-242ecda029d2.jpeg"
    ),
    "neutrophil-guide.jpg": (
        "https://panoptes-uploads.zooniverse.org/"
        "project_attached_image/038d6737-f402-4c55-89e3-79ab6d870a93.jpeg"
    ),
    "not-a-wbc.jpg": (
        "https://panoptes-uploads.zooniverse.org/"
        "project_attached_image/f7154674-2566-4f9e-9bf8-67a9ee774d35.jpeg"
    ),
    "wbc-guide.pdf": (
        "https://panoptes-uploads.zooniverse.org/"
        "project_attached_image/fba9b1ce-75e6-4569-93e7-f17349bb28f7.pdf"
    ),
}


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.api+json; version=1",
            "User-Agent": "monkeybench-resource-fetcher/0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def fetch_json(url: str) -> dict[str, Any]:
    value = json.loads(fetch_bytes(url))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object from {url}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_bytes(fetch_bytes(url))
    temporary.replace(destination)


def image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def reset_generated_directories() -> None:
    for path in (
        ROOT / "challenge/inputs/images",
        ROOT / "challenge/training/assets",
        ROOT / "reference/answer-images",
    ):
        if path.exists():
            shutil.rmtree(path)


def subject_location(subject: dict[str, Any], index: int) -> str:
    location = subject["locations"][index]
    if not isinstance(location, dict) or len(location) != 1:
        raise ValueError(
            f"subject {subject.get('id')} location {index} is malformed"
        )
    return str(next(iter(location.values())))


def build_subject_resources() -> list[dict[str, Any]]:
    payload = fetch_json(
        f"{API_ROOT}/subjects"
        f"?subject_set_id={SUBJECT_SET_ID}&page_size=100"
    )
    subjects = payload.get("subjects")
    if not isinstance(subjects, list) or len(subjects) != 14:
        raise ValueError("expected exactly 14 practice subjects")
    subjects.sort(key=lambda subject: subject["metadata"]["ImageID"])

    observed_ids = tuple(
        subject["metadata"]["ImageID"] for subject in subjects
    )
    if observed_ids != EXPECTED_IMAGE_IDS:
        raise ValueError(
            f"unexpected practice IDs: {observed_ids!r}"
        )

    totals = {key: 0 for key in EXPECTED_TOTALS}
    challenge_subjects = []
    reference_subjects = []
    for subject in subjects:
        metadata = subject["metadata"]
        image_id = str(metadata["ImageID"])
        counts = {
            key: int(metadata[key])
            for key in EXPECTED_TOTALS
        }
        for key, count in counts.items():
            totals[key] += count

        candidate_url = subject_location(subject, 0)
        answer_url = subject_location(subject, 1)
        candidate_path = ROOT / f"challenge/inputs/images/{image_id}.jpg"
        answer_path = ROOT / f"reference/answer-images/{image_id}.jpg"
        download(candidate_url, candidate_path)
        download(answer_url, answer_path)
        candidate_size = image_size(candidate_path)
        answer_size = image_size(answer_path)
        if candidate_size != answer_size:
            raise ValueError(
                f"subject {image_id} image dimensions differ: "
                f"{candidate_size} != {answer_size}"
            )

        challenge_subjects.append(
            {
                "image_id": image_id,
                "path": f"images/{image_id}.jpg",
                "width": candidate_size[0],
                "height": candidate_size[1],
            }
        )
        reference_subjects.append(
            {
                "subject_id": str(subject["id"]),
                "image_id": image_id,
                "candidate_filename": str(metadata["Blank"]),
                "answer_filename": str(metadata["Answer"]),
                "counts": {
                    key.removesuffix("s").lower(): value
                    for key, value in counts.items()
                },
                "candidate_url": candidate_url,
                "answer_url": answer_url,
                "width": candidate_size[0],
                "height": candidate_size[1],
            }
        )

    if totals != EXPECTED_TOTALS:
        raise ValueError(
            f"unexpected aggregate cell counts: {totals!r}"
        )

    write_json(
        ROOT / "challenge/inputs/subjects.json",
        {
            "schema_version": "1.0",
            "coordinate_system": {
                "origin": "top-left",
                "x_range": [0.0, 1.0],
                "y_range": [0.0, 1.0],
            },
            "subjects": challenge_subjects,
        },
    )
    write_json(
        ROOT / "reference/source-subjects.json",
        {
            "schema_version": "1.0",
            "project_id": PROJECT_ID,
            "workflow_id": WORKFLOW_ID,
            "subject_set_id": SUBJECT_SET_ID,
            "subjects": reference_subjects,
        },
    )
    return reference_subjects


def build_training_resources() -> None:
    tutorial = fetch_json(
        f"{API_ROOT}/tutorials?workflow_id={WORKFLOW_ID}"
    )
    field_guide = fetch_json(
        f"{API_ROOT}/field_guides?project_id={PROJECT_ID}"
    )
    write_json(ROOT / "challenge/training/tutorial.json", tutorial)
    write_json(ROOT / "challenge/training/field-guide.json", field_guide)
    for filename, url in TRAINING_RESOURCES.items():
        if not re.fullmatch(r"[\w.-]+", filename):
            raise ValueError(f"unsafe training filename: {filename}")
        download(url, ROOT / "challenge/training/assets" / filename)


def manifest_entry(path: Path, *, root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "size": path.stat().st_size,
        "sha256": sha256(path),
    }


def write_source_manifest() -> None:
    challenge_paths = sorted(
        path
        for path in (ROOT / "challenge").rglob("*")
        if path.is_file()
    )
    reference_paths = sorted(
        path
        for path in (ROOT / "reference").rglob("*")
        if path.is_file() and path.name != "manifest.json"
    )
    write_json(
        ROOT / "resources/source-manifest.json",
        {
            "schema_version": "1.0",
            "source_project": (
                "https://www.zooniverse.org/projects/"
                "mbarrierz/monkey-health-explorer"
            ),
            "challenge_files": [
                manifest_entry(path, root=ROOT)
                for path in challenge_paths
            ],
            "reference_files": [
                manifest_entry(path, root=ROOT)
                for path in reference_paths
            ],
            "training_sources": TRAINING_RESOURCES,
        },
    )


def main() -> int:
    reset_generated_directories()
    build_subject_resources()
    build_training_resources()
    write_source_manifest()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
