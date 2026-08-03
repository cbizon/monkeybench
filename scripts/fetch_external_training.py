from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL

from monkeybench.materialize_challenge import (
    ASSET_MANIFEST,
    ExternalAsset,
    load_external_assets,
    verify_asset,
)


ROOT = Path(__file__).resolve().parents[1]


def _download_assets(
    download: dict[str, Any],
    expected: dict[str, ExternalAsset],
    destination: Path,
) -> None:
    output_template = str(destination / "identifying-wbcs.%(ext)s")
    options = {
        "format": download["video_format"],
        "noplaylist": True,
        "outtmpl": output_template,
        "subtitlesformat": "vtt",
        "subtitleslangs": [download["subtitle_language"]],
        "writesubtitles": True,
    }
    with YoutubeDL(options) as downloader:
        downloader.download([download["source_url"]])

    for filename, asset in expected.items():
        verify_asset(destination / filename, asset)


def fetch_external_training(cache_root: Path) -> tuple[Path, ...]:
    manifest = json.loads(ASSET_MANIFEST.read_text())
    assets_by_path = {
        asset.cache_path: asset for asset in load_external_assets()
    }
    installed: list[Path] = []
    for download in manifest["downloads"]:
        expected = {
            value["download_filename"]: assets_by_path[
                Path(value["cache_path"])
            ]
            for value in download["assets"]
        }
        cache_destinations = {
            filename: cache_root / asset.cache_path
            for filename, asset in expected.items()
        }
        if all(
            destination.is_file()
            for destination in cache_destinations.values()
        ):
            for filename, destination in cache_destinations.items():
                verify_asset(destination, expected[filename])
            installed.extend(cache_destinations.values())
            continue

        with tempfile.TemporaryDirectory(
            prefix=f"monkeybench-{download['id']}-"
        ) as temporary:
            temporary_path = Path(temporary)
            _download_assets(download, expected, temporary_path)
            for filename, destination in cache_destinations.items():
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary_destination = destination.with_name(
                    f".{destination.name}.tmp"
                )
                shutil.copyfile(
                    temporary_path / filename,
                    temporary_destination,
                )
                verify_asset(temporary_destination, expected[filename])
                temporary_destination.replace(destination)
                installed.append(destination)
    return tuple(installed)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Populate Monkeybench's external Brunner resource cache."
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=ROOT / ".resource-cache",
        help="Resource cache root (default: .resource-cache)",
    )
    arguments = parser.parse_args()
    for path in fetch_external_training(arguments.cache_dir.resolve()):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
