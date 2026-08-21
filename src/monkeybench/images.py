from __future__ import annotations

import os


_PLACEHOLDER_DIGEST = "0" * 64

DEFAULT_AGENT_IMAGE = (
    "ghcr.io/cbizon/monkeybench-agent@sha256:"
    f"{_PLACEHOLDER_DIGEST}"
)
DEFAULT_CONTROLLER_IMAGE = (
    "ghcr.io/cbizon/monkeybench-controller@sha256:"
    f"{_PLACEHOLDER_DIGEST}"
)
DEFAULT_EVALUATOR_IMAGE = DEFAULT_CONTROLLER_IMAGE
DEFAULT_SQUID_IMAGE = (
    "ubuntu/squid@sha256:"
    "6a097f68bae708cedbabd6188d68c7e2e7a38cedd05a176e1cc0ba29e3bbe029"
)


def agent_image() -> str:
    return os.environ.get(
        "MONKEYBENCH_AGENT_IMAGE",
        DEFAULT_AGENT_IMAGE,
    )


def controller_image() -> str:
    return os.environ.get(
        "MONKEYBENCH_CONTROLLER_IMAGE",
        DEFAULT_CONTROLLER_IMAGE,
    )


def evaluator_image() -> str:
    return os.environ.get(
        "MONKEYBENCH_EVALUATOR_IMAGE",
        controller_image(),
    )


def squid_image() -> str:
    return os.environ.get(
        "MONKEYBENCH_SQUID_IMAGE",
        DEFAULT_SQUID_IMAGE,
    )
