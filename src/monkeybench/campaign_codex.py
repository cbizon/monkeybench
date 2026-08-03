from __future__ import annotations

import os

from brunner import BenchmarkDefinition, CampaignRunner
from brunner.contract import OutputContract

from monkeybench.campaign_matrix import (
    CODEX_MATRIX,
    build_kubernetes_campaign,
)


def build_campaign(
    definition: BenchmarkDefinition,
    contract: OutputContract,
) -> CampaignRunner:
    return build_kubernetes_campaign(
        definition,
        contract,
        provider="codex",
        matrix=CODEX_MATRIX,
        secret_name=os.environ.get(
            "MONKEYBENCH_CODEX_SECRET",
            "balls-bench-codex-azure",
        ),
        secret_key=os.environ.get(
            "MONKEYBENCH_CODEX_SECRET_KEY",
            "AZURE_OPENAI_API_KEY",
        ),
        environment_name="AZURE_OPENAI_API_KEY",
    )
