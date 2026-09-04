from __future__ import annotations

import os


DEFAULT_AGENT_IMAGE = (
    "ghcr.io/cbizon/monkeybench-agent@sha256:"
    "97ac6644fd5c34375ba67b75c7e38c916a590a203f6288cdc3110ba88f4ef8d6"
)
DEFAULT_CONTROLLER_IMAGE = (
    "ghcr.io/cbizon/monkeybench-controller@sha256:"
    "4359cc062ce346dfa42239bee6c017ae8fac7ae9fdd19efba6c39517d3e897a7"
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
