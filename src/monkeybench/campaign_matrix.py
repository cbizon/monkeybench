from __future__ import annotations

from brunner import (
    BenchmarkDefinition,
    CampaignPlan,
    CampaignTrial,
    ClusterCampaign,
    ControllerProfile,
)
from brunner.backends import KubernetesProfile
from brunner.contract import OutputContract

from monkeybench.images import (
    HISTORICAL_AGENT_IMAGE,
    agent_image,
    controller_image,
    squid_image,
)


DEFAULT_NAMESPACE = "bizon"
DEFAULT_STORAGE_CLASS = "basic"
DEFAULT_MAX_PARALLEL = 1
DEFAULT_REFERENCE_CLAIM = "monkeybench-reference"
DEFAULT_RESOURCE_CACHE_CLAIM = "monkeybench-resource-cache"
DEFAULT_IMAGE_PULL_SECRETS = ("registry-credentials",)
DEFAULT_CODEX_PROVIDER_ID = "azure"
DEFAULT_CODEX_PROVIDER_NAME = "RENCI Azure OpenAI"
DEFAULT_CODEX_BASE_URL = (
    "https://renci-analytics.openai.azure.com/openai/v1/"
)
DEFAULT_CODEX_ENVIRONMENT_KEY = "AZURE_OPENAI_API_KEY"

CODEX_MATRIX = (
    ("gpt-6-astra", "xhigh", 1),
    ("gpt-6-astra", "low", 1),
    ("gpt-5.6-sol", "xhigh", 1),
    ("gpt-5.6-sol", "low", 1),
    ("gpt-5.6-terra", "xhigh", 1),
    ("gpt-5.6-terra", "low", 1),
    ("gpt-5.6-luna", "xhigh", 1),
    ("gpt-5.6-luna", "low", 1),
    ("gpt-5.5", "xhigh", 1),
    ("gpt-5.5", "low", 1),
    ("gpt-5.4", "xhigh", 1),
    ("gpt-5.4", "low", 1),
)

HISTORICAL_CLAUDE_MATRIX = (
    ("claude-opus-5", "max", 1),
    ("claude-opus-5", "low", 1),
    ("claude-opus-4-8", "max", 1),
    ("claude-opus-4-8", "low", 1),
    ("claude-sonnet-5", "max", 1),
    ("claude-sonnet-5", "low", 1),
)

NEW_CLAUDE_MATRIX = (
    ("claude-fable-5-1", "low", 1),
)

CLAUDE_MATRIX = (*HISTORICAL_CLAUDE_MATRIX, *NEW_CLAUDE_MATRIX)

CANARY_TRIAL_IDS = (
    "codex-gpt-5-4-low-r01",
    "claude-sonnet-5-low-r01",
)


def _slug(value: str) -> str:
    return value.lower().replace(".", "-")


def _trial_id(
    provider: str,
    model: str,
    effort: str,
    run_number: int,
) -> str:
    model_slug = _slug(model)
    prefix = "" if model_slug.startswith(f"{provider}-") else f"{provider}-"
    return f"{prefix}{model_slug}-{effort}-r{run_number:02d}"


def build_trials(
    provider: str,
    matrix: tuple[tuple[str, str, int], ...],
    *,
    backend_image: str | None = None,
) -> tuple[CampaignTrial, ...]:
    trials = []
    for model, effort, run_count in matrix:
        for run_number in range(1, run_count + 1):
            connection = (
                {
                    "provider_id": DEFAULT_CODEX_PROVIDER_ID,
                    "provider_name": DEFAULT_CODEX_PROVIDER_NAME,
                    "base_url": DEFAULT_CODEX_BASE_URL,
                    "environment_key": DEFAULT_CODEX_ENVIRONMENT_KEY,
                }
                if provider == "codex"
                else {}
            )
            trials.append(
                CampaignTrial(
                    test_id=_trial_id(
                        provider,
                        model,
                        effort,
                        run_number,
                    ),
                    provider=provider,
                    model=model,
                    effort=effort,
                    backend_image=backend_image,
                    **connection,
                )
            )
    return tuple(trials)


def build_campaign_trials() -> tuple[CampaignTrial, ...]:
    return (
        *build_trials(
            "codex",
            CODEX_MATRIX,
            backend_image=HISTORICAL_AGENT_IMAGE,
        ),
        *build_trials(
            "claude",
            HISTORICAL_CLAUDE_MATRIX,
            backend_image=HISTORICAL_AGENT_IMAGE,
        ),
        *build_trials("claude", NEW_CLAUDE_MATRIX),
    )


def select_trials(
    trials: tuple[CampaignTrial, ...],
    requested: tuple[str, ...],
) -> tuple[CampaignTrial, ...]:
    if not requested:
        raise ValueError("requested trial IDs cannot be empty")
    if len(set(requested)) != len(requested):
        raise ValueError("requested trial IDs contain duplicates")
    available = {trial.test_id: trial for trial in trials}
    unknown = tuple(test_id for test_id in requested if test_id not in available)
    if unknown:
        raise ValueError("unknown trial IDs: " + ", ".join(unknown))
    return tuple(available[test_id] for test_id in requested)


def build_cluster_campaign(
    definition: BenchmarkDefinition,
    contract: OutputContract,
    *,
    campaign_id: str,
    trials: tuple[CampaignTrial, ...],
    max_parallel: int = DEFAULT_MAX_PARALLEL,
) -> ClusterCampaign:
    del definition, contract
    agent = agent_image()
    controller = controller_image()
    plan = CampaignPlan(
        campaign_id=campaign_id,
        trials=trials,
        max_parallel=max_parallel,
        backend_image=agent,
        cpu_request="500m",
        cpu_limit="2",
        memory_request="4Gi",
        memory_limit="8Gi",
        ephemeral_storage_request="512Mi",
        ephemeral_storage_limit="2Gi",
        provider_secret_environment={
            "codex": {
                DEFAULT_CODEX_ENVIRONMENT_KEY: (
                    "codex-provider-credentials",
                    DEFAULT_CODEX_ENVIRONMENT_KEY,
                )
            },
            "claude": {
                "CLAUDE_CODE_OAUTH_TOKEN": (
                    "claude-provider-credentials",
                    "CLAUDE_CODE_OAUTH_TOKEN",
                )
            },
        },
        submission_retry_seconds=30,
        collection_retry_seconds=30,
        cleanup_retry_seconds=30,
        publication_retry_seconds=30,
        collection_max_attempts=5,
        evaluation_timeout_seconds=20 * 60,
    )
    return ClusterCampaign(
        plan=plan,
        backend=KubernetesProfile(
            namespace=DEFAULT_NAMESPACE,
            network_isolation_mode="controlled-egress",
            agent_image=agent,
            artifact_reader_image=controller,
            reference_claim_name=DEFAULT_REFERENCE_CLAIM,
            storage_size="2Gi",
            storage_class_name=DEFAULT_STORAGE_CLASS,
            image_pull_secrets=DEFAULT_IMAGE_PULL_SECRETS,
            proxy_image=squid_image(),
            max_parallel=max_parallel,
            retain_failed_storage=True,
            command_timeout_seconds=60,
            staging_timeout_seconds=10 * 60,
            reader_timeout_seconds=10 * 60,
        ),
        controller=ControllerProfile(
            namespace=DEFAULT_NAMESPACE,
            image=controller,
            control_storage_size="10Gi",
            results_storage_size="20Gi",
            storage_class_name=DEFAULT_STORAGE_CLASS,
            resource_cache_claim_name=DEFAULT_RESOURCE_CACHE_CLAIM,
            image_pull_secrets=DEFAULT_IMAGE_PULL_SECRETS,
            poll_seconds=5,
            preparation_timeout_seconds=20 * 60,
            command_timeout_seconds=60,
            max_published_trial_bytes=512 * 1024 * 1024,
            controller_cpu_request="250m",
            controller_cpu_limit="1",
            controller_memory_request="512Mi",
            controller_memory_limit="2Gi",
            assessment_cpu_request="500m",
            assessment_cpu_limit="2",
            assessment_memory_request="1Gi",
            assessment_memory_limit="4Gi",
            reviewer_secret_environment={
                "codex": {
                    DEFAULT_CODEX_ENVIRONMENT_KEY: (
                        "codex-provider-credentials",
                        DEFAULT_CODEX_ENVIRONMENT_KEY,
                    )
                }
            },
        ),
    )
