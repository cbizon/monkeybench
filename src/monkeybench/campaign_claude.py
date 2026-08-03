from __future__ import annotations

import os

from brunner import BenchmarkDefinition, CampaignRunner
from brunner.contract import OutputContract

from monkeybench.campaign_matrix import (
    CLAUDE_MATRIX,
    build_kubernetes_campaign,
)


def build_campaign(
    definition: BenchmarkDefinition,
    contract: OutputContract,
) -> CampaignRunner:
    return build_kubernetes_campaign(
        definition,
        contract,
        provider="claude",
        matrix=CLAUDE_MATRIX,
        secret_name=os.environ.get(
            "MONKEYBENCH_CLAUDE_SECRET",
            "balls-bench-claude-oauth",
        ),
        secret_key=os.environ.get(
            "MONKEYBENCH_CLAUDE_SECRET_KEY",
            "CLAUDE_CODE_OAUTH_TOKEN",
        ),
        environment_name="CLAUDE_CODE_OAUTH_TOKEN",
    )
