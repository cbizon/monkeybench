from __future__ import annotations

from brunner import BenchmarkDefinition, ClusterCampaign
from brunner.contract import OutputContract

from monkeybench.campaign_matrix import (
    CANARY_TRIAL_IDS,
    build_campaign_trials,
    build_cluster_campaign,
    select_trials,
)


def build_campaign(
    definition: BenchmarkDefinition,
    contract: OutputContract,
) -> ClusterCampaign:
    return build_cluster_campaign(
        definition,
        contract,
        campaign_id="monkey-wbc-model-sweep-v2",
        trials=build_campaign_trials(),
    )


def build_canary_campaign(
    definition: BenchmarkDefinition,
    contract: OutputContract,
) -> ClusterCampaign:
    trials = select_trials(build_campaign_trials(), CANARY_TRIAL_IDS)
    return build_cluster_campaign(
        definition,
        contract,
        campaign_id="monkey-wbc-canary-v2",
        trials=trials,
    )
