from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ASSET_MANIFEST = ROOT / "resources/external-training-assets.json"


@dataclass(frozen=True)
class ExternalAsset:
    asset_id: str
    role: str
    cache_path: Path
    challenge_path: Path
    size: int
    sha256: str


def _relative_path(value: Any, *, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field} must be a safe relative path: {value!r}")
    return path


def load_external_assets(
    manifest_path: Path = ASSET_MANIFEST,
) -> tuple[ExternalAsset, ...]:
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema_version") != "1.0":
        raise ValueError("external asset manifest schema_version must be 1.0")

    assets: list[ExternalAsset] = []
    seen_cache_paths: set[Path] = set()
    seen_challenge_paths: set[Path] = set()
    for download in manifest.get("downloads", []):
        download_id = download.get("id")
        if not isinstance(download_id, str) or not download_id.strip():
            raise ValueError("external asset download id must be non-empty")
        for value in download.get("assets", []):
            cache_path = _relative_path(
                value.get("cache_path"),
                field=f"{download_id} cache_path",
            )
            challenge_path = _relative_path(
                value.get("challenge_path"),
                field=f"{download_id} challenge_path",
            )
            if cache_path in seen_cache_paths:
                raise ValueError(f"duplicate cache path: {cache_path}")
            if challenge_path in seen_challenge_paths:
                raise ValueError(
                    f"duplicate challenge path: {challenge_path}"
                )
            size = value.get("size")
            sha256 = value.get("sha256")
            if not isinstance(size, int) or size < 0:
                raise ValueError(f"{download_id} asset size must be nonnegative")
            if (
                not isinstance(sha256, str)
                or len(sha256) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in sha256
                )
            ):
                raise ValueError(
                    f"{download_id} asset sha256 must be lowercase hex"
                )
            assets.append(
                ExternalAsset(
                    asset_id=download_id,
                    role=str(value.get("role", "")),
                    cache_path=cache_path,
                    challenge_path=challenge_path,
                    size=size,
                    sha256=sha256,
                )
            )
            seen_cache_paths.add(cache_path)
            seen_challenge_paths.add(challenge_path)
    if not assets:
        raise ValueError("external asset manifest contains no assets")
    return tuple(assets)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_asset(path: Path, asset: ExternalAsset) -> None:
    if not path.is_file():
        raise FileNotFoundError(
            f"missing external training asset: {path}\n"
            "Populate the Brunner resource cache with "
            "`uv run python scripts/fetch_external_training.py`."
        )
    actual_size = path.stat().st_size
    if actual_size != asset.size:
        raise ValueError(
            f"external training asset size mismatch for {path}: "
            f"expected {asset.size}, found {actual_size}"
        )
    actual_sha256 = sha256_file(path)
    if actual_sha256 != asset.sha256:
        raise ValueError(
            f"external training asset checksum mismatch for {path}: "
            f"expected {asset.sha256}, found {actual_sha256}"
        )


def materialize_assets(
    challenge_root: Path,
    cache_root: Path,
    *,
    manifest_path: Path = ASSET_MANIFEST,
) -> tuple[Path, ...]:
    challenge_root = challenge_root.resolve()
    cache_root = cache_root.resolve()
    materialized: list[Path] = []
    for asset in load_external_assets(manifest_path):
        source = cache_root / asset.cache_path
        destination = challenge_root / asset.challenge_path
        verify_asset(source, asset)
        if destination.exists():
            raise FileExistsError(
                f"materialized destination already exists: {destination}"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.tmp")
        shutil.copyfile(source, temporary)
        verify_asset(temporary, asset)
        temporary.replace(destination)
        materialized.append(destination)
    return tuple(materialized)


def main() -> int:
    challenge_value = os.environ.get("BRUNNER_CHALLENGE_ROOT")
    if not challenge_value:
        raise RuntimeError("BRUNNER_CHALLENGE_ROOT is required")
    cache_value = os.environ.get("BRUNNER_RESOURCE_CACHE")
    cache_root = Path(cache_value) if cache_value else ROOT / ".resource-cache"
    if not cache_root.is_absolute():
        cache_root = ROOT / cache_root
    challenge_root = Path(challenge_value).resolve()
    paths = materialize_assets(challenge_root, cache_root)
    for path in paths:
        print(f"materialized {path.relative_to(challenge_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
