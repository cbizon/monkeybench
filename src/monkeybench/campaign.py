from __future__ import annotations

import os

from brunner import BenchmarkDefinition, CampaignRunner
from brunner.contract import OutputContract

from monkeybench.campaign_matrix import build_kubernetes_campaign


def build_campaign(
    definition: BenchmarkDefinition,
    contract: OutputContract,
) -> CampaignRunner:
    # Brunner currently applies profile secret references to every Job.
    # Keep both providers in one campaign until per-workload secrets exist.
    secret_environment = {
        "AZURE_OPENAI_API_KEY": (
            os.environ.get(
                "MONKEYBENCH_CODEX_SECRET",
                "balls-bench-codex-azure",
            ),
            os.environ.get(
                "MONKEYBENCH_CODEX_SECRET_KEY",
                "AZURE_OPENAI_API_KEY",
            ),
        ),
        "CLAUDE_CODE_OAUTH_TOKEN": (
            os.environ.get(
                "MONKEYBENCH_CLAUDE_SECRET",
                "balls-bench-claude-oauth",
            ),
            os.environ.get(
                "MONKEYBENCH_CLAUDE_SECRET_KEY",
                "CLAUDE_CODE_OAUTH_TOKEN",
            ),
        ),
    }
    return build_kubernetes_campaign(
        definition,
        contract,
        secret_environment=secret_environment,
    )
