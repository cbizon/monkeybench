from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from brunner.providers import ProviderSettings
from brunner.runner import run_staged_trial
from brunner.trial import TrialIdentity, load_trial_identity


DEFAULT_CODEX_PROVIDER_ID = "azure"
DEFAULT_CODEX_PROVIDER_NAME = "Azure OpenAI"
DEFAULT_CODEX_BASE_URL = (
    "https://renci-analytics.openai.azure.com/openai/v1/"
)
DEFAULT_CODEX_ENVIRONMENT_KEY = "AZURE_OPENAI_API_KEY"


def provider_settings(identity: TrialIdentity) -> ProviderSettings:
    if identity.provider == "codex":
        return ProviderSettings(
            provider=identity.provider,
            model=identity.model,
            effort=identity.effort,
            provider_id=os.environ.get(
                "MONKEYBENCH_CODEX_PROVIDER_ID",
                DEFAULT_CODEX_PROVIDER_ID,
            ),
            provider_name=os.environ.get(
                "MONKEYBENCH_CODEX_PROVIDER_NAME",
                DEFAULT_CODEX_PROVIDER_NAME,
            ),
            base_url=os.environ.get(
                "MONKEYBENCH_CODEX_BASE_URL",
                DEFAULT_CODEX_BASE_URL,
            ),
            environment_key=os.environ.get(
                "MONKEYBENCH_CODEX_ENVIRONMENT_KEY",
                DEFAULT_CODEX_ENVIRONMENT_KEY,
            ),
        )
    if identity.provider == "claude":
        return ProviderSettings(
            provider=identity.provider,
            model=identity.model,
            effort=identity.effort,
        )
    raise ValueError(f"unsupported provider: {identity.provider}")


def main() -> int:
    parser = argparse.ArgumentParser(prog="monkeybench-remote-agent")
    parser.add_argument("trial", type=Path)
    arguments = parser.parse_args()
    trial = arguments.trial.resolve()
    identity = load_trial_identity(trial)
    state = run_staged_trial(
        trial,
        provider_settings(identity),
        executable=(
            "monkeybench-claude"
            if identity.provider == "claude"
            else "monkeybench-codex"
        ),
    )
    print(json.dumps(state, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
