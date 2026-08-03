from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from monkeybench.materialize_challenge import materialize_assets


def write_manifest(
    path: Path,
    *,
    content: bytes,
    sha256: str | None = None,
) -> None:
    path.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "downloads": [
                    {
                        "id": "test-video",
                        "assets": [
                            {
                                "role": "video",
                                "cache_path": "test/video.mp4",
                                "challenge_path": (
                                    "training/videos/video.mp4"
                                ),
                                "size": len(content),
                                "sha256": sha256
                                or hashlib.sha256(content).hexdigest(),
                            }
                        ],
                    }
                ],
            }
        )
    )


def test_materialize_assets_copies_verified_file(tmp_path: Path) -> None:
    content = b"small test video"
    cache = tmp_path / "cache"
    challenge = tmp_path / "challenge"
    manifest = tmp_path / "manifest.json"
    source = cache / "test/video.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(content)
    challenge.mkdir()
    write_manifest(manifest, content=content)

    paths = materialize_assets(
        challenge,
        cache,
        manifest_path=manifest,
    )

    assert paths == (challenge / "training/videos/video.mp4",)
    assert paths[0].read_bytes() == content


def test_materialize_assets_rejects_missing_cache_file(
    tmp_path: Path,
) -> None:
    content = b"small test video"
    cache = tmp_path / "cache"
    challenge = tmp_path / "challenge"
    manifest = tmp_path / "manifest.json"
    cache.mkdir()
    challenge.mkdir()
    write_manifest(manifest, content=content)

    with pytest.raises(FileNotFoundError, match="fetch_external_training"):
        materialize_assets(
            challenge,
            cache,
            manifest_path=manifest,
        )


def test_materialize_assets_rejects_checksum_mismatch(
    tmp_path: Path,
) -> None:
    content = b"small test video"
    cache = tmp_path / "cache"
    challenge = tmp_path / "challenge"
    manifest = tmp_path / "manifest.json"
    source = cache / "test/video.mp4"
    source.parent.mkdir(parents=True)
    source.write_bytes(content)
    challenge.mkdir()
    write_manifest(manifest, content=content, sha256="0" * 64)

    with pytest.raises(ValueError, match="checksum mismatch"):
        materialize_assets(
            challenge,
            cache,
            manifest_path=manifest,
        )
