from __future__ import annotations

import json
import os
import sys


def prepare_arguments(arguments: list[str]) -> list[str]:
    prepared = list(arguments)
    if os.environ.get(
        "MONKEYBENCH_CLAUDE_NESTED_SANDBOX",
        "true",
    ).lower() not in {"1", "true", "yes"}:
        return prepared
    try:
        settings_index = prepared.index("--settings") + 1
    except ValueError as error:
        raise RuntimeError("Claude command does not include --settings") from error
    settings = json.loads(prepared[settings_index])
    sandbox = settings.setdefault("sandbox", {})
    sandbox["enableWeakerNestedSandbox"] = True
    prepared[settings_index] = json.dumps(
        settings,
        separators=(",", ":"),
    )
    return prepared


def main() -> None:
    os.execvp(
        "claude",
        ("claude", *prepare_arguments(sys.argv[1:])),
    )


if __name__ == "__main__":
    main()
