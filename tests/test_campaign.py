from __future__ import annotations

import json
from pathlib import Path

import pytest

from brunner.campaign import default_workload_factory
from brunner.cluster import (
    apply_campaign_image_overrides,
    apply_definition_image_override,
    campaign_image_environment,
    campaign_resources,
    definition_image_environment,
    render_cluster_resources,
)
from brunner.contract import load_output_contract
from brunner.providers import ProviderRunContext, ProviderSettings
from brunner.providers.claude import ClaudeAdapter
from brunner.providers.codex import CodexAdapter

from monkeybench.campaign import (
    build_campaign,
    build_canary_campaign,
)
from monkeybench.campaign_matrix import (
    CANARY_TRIAL_IDS,
    CLAUDE_MATRIX,
    CODEX_MATRIX,
    DEFAULT_CODEX_BASE_URL,
    DEFAULT_CODEX_ENVIRONMENT_KEY,
    build_campaign_trials,
    build_trials,
    select_trials,
)
from monkeybench.definition import build_definition
from monkeybench.images import (
    DEFAULT_AGENT_IMAGE,
    DEFAULT_CONTROLLER_IMAGE,
)


EXPECTED_CODEX = {
    ("gpt-5.6-sol", "xhigh"),
    ("gpt-5.6-sol", "low"),
    ("gpt-5.6-terra", "xhigh"),
    ("gpt-5.6-terra", "low"),
    ("gpt-5.6-luna", "xhigh"),
    ("gpt-5.6-luna", "low"),
    ("gpt-5.5", "xhigh"),
    ("gpt-5.5", "low"),
    ("gpt-5.4", "xhigh"),
    ("gpt-5.4", "low"),
}
EXPECTED_CLAUDE = {
    ("claude-opus-5", "max"),
    ("claude-opus-5", "low"),
    ("claude-opus-4-8", "max"),
    ("claude-opus-4-8", "low"),
    ("claude-sonnet-5", "max"),
    ("claude-sonnet-5", "low"),
}
EXPECTED_AGENT_IMAGE = (
    "ghcr.io/cbizon/monkeybench-agent@sha256:"
    "97ac6644fd5c34375ba67b75c7e38c916a590a203f6288cdc3110ba88f4ef8d6"
)
EXPECTED_CONTROLLER_IMAGE = (
    "ghcr.io/cbizon/monkeybench-controller@sha256:"
    "4359cc062ce346dfa42239bee6c017ae8fac7ae9fdd19efba6c39517d3e897a7"
)


def _configure_images(monkeypatch: pytest.MonkeyPatch) -> None:
    images = {
        "MONKEYBENCH_AGENT_IMAGE": (
            "ghcr.io/cbizon/monkeybench-agent@sha256:" + "1" * 64
        ),
        "MONKEYBENCH_CONTROLLER_IMAGE": (
            "ghcr.io/cbizon/monkeybench-controller@sha256:" + "2" * 64
        ),
        "MONKEYBENCH_EVALUATOR_IMAGE": (
            "ghcr.io/cbizon/monkeybench-controller@sha256:" + "3" * 64
        ),
        "MONKEYBENCH_SQUID_IMAGE": (
            "ubuntu/squid@sha256:" + "4" * 64
        ),
    }
    for name, value in images.items():
        monkeypatch.setenv(name, value)


def _campaign(monkeypatch: pytest.MonkeyPatch):
    _configure_images(monkeypatch)
    definition = build_definition()
    contract = load_output_contract(definition.contract_path)
    return definition, contract, build_campaign(definition, contract)


def test_matrix_matches_granular_benchmark_without_fable() -> None:
    assert {(model, effort) for model, effort, _ in CODEX_MATRIX} == (
        EXPECTED_CODEX
    )
    assert {(model, effort) for model, effort, _ in CLAUDE_MATRIX} == (
        EXPECTED_CLAUDE
    )
    assert all("fable" not in model for model, _, _ in CLAUDE_MATRIX)
    assert sum(count for _, _, count in CODEX_MATRIX) == 10
    assert sum(count for _, _, count in CLAUDE_MATRIX) == 6
    assert all(count == 1 for _, _, count in CLAUDE_MATRIX)


def test_campaign_trial_ids_are_unique() -> None:
    trials = build_campaign_trials()
    assert len(trials) == 16
    assert len({trial.test_id for trial in trials}) == len(trials)
    assert len(
        {(trial.provider, trial.model, trial.effort) for trial in trials}
    ) == len(trials)
    assert "codex-gpt-5-4-low-r01" in {
        trial.test_id for trial in trials
    }
    assert "claude-sonnet-5-low-r01" in {
        trial.test_id for trial in trials
    }
    assert not any(
        trial.test_id.startswith("claude-claude-") for trial in trials
    )


def test_default_images_are_published_immutable_digests() -> None:
    assert DEFAULT_AGENT_IMAGE == EXPECTED_AGENT_IMAGE
    assert DEFAULT_CONTROLLER_IMAGE == EXPECTED_CONTROLLER_IMAGE


def test_trial_selection_preserves_requested_order() -> None:
    trials = build_trials("codex", CODEX_MATRIX)
    selected = select_trials(
        trials,
        (
            "codex-gpt-5-4-low-r01",
            "codex-gpt-5-6-sol-xhigh-r01",
        ),
    )

    assert [trial.test_id for trial in selected] == [
        "codex-gpt-5-4-low-r01",
        "codex-gpt-5-6-sol-xhigh-r01",
    ]


def test_trial_selection_rejects_unknown_ids() -> None:
    with pytest.raises(ValueError, match="codex-missing"):
        select_trials(
            build_trials("codex", CODEX_MATRIX),
            ("codex-missing",),
        )


def test_canary_campaign_is_fixed_and_cluster_reproducible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_images(monkeypatch)
    definition = build_definition()
    contract = load_output_contract(definition.contract_path)

    campaign = build_canary_campaign(definition, contract)

    assert tuple(trial.test_id for trial in campaign.plan.trials) == (
        CANARY_TRIAL_IDS
    )
    assert campaign.plan.campaign_id == "monkey-wbc-canary-v2"
    assert campaign.plan.max_parallel == 1


def test_full_campaign_uses_provider_scoped_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, campaign = _campaign(monkeypatch)

    assert len(campaign.plan.trials) == 16
    assert {trial.provider for trial in campaign.plan.trials} == {
        "codex",
        "claude",
    }
    assert campaign.plan.campaign_id == "monkey-wbc-model-sweep-v2"
    assert campaign.plan.provider_secret_environment == {
        "codex": {
            "AZURE_OPENAI_API_KEY": (
                "codex-provider-credentials",
                "AZURE_OPENAI_API_KEY",
            )
        },
        "claude": {
            "CLAUDE_CODE_OAUTH_TOKEN": (
                "claude-provider-credentials",
                "CLAUDE_CODE_OAUTH_TOKEN",
            )
        },
    }
    assert campaign.backend.secret_environment == {}


def test_default_workload_uses_native_brunner_agent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    definition, _, campaign = _campaign(monkeypatch)
    codex_trial = next(
        trial
        for trial in campaign.plan.trials
        if trial.provider == "codex"
    )

    workload = default_workload_factory(
        tmp_path / codex_trial.test_id,
        codex_trial,
        campaign.plan,
        definition,
        "kubernetes",
    )

    assert workload.command[:4] == (
        "python",
        "-m",
        "brunner.agent_cli",
        "/brunner/trial",
    )
    assert "--provider-id" in workload.command
    assert DEFAULT_CODEX_BASE_URL in workload.command
    assert workload.cpu_request == "500m"
    assert workload.cpu_limit == "2"
    assert workload.memory_request == "4Gi"
    assert workload.memory_limit == "8Gi"
    assert workload.secret_environment == {
        DEFAULT_CODEX_ENVIRONMENT_KEY: (
            "codex-provider-credentials",
            DEFAULT_CODEX_ENVIRONMENT_KEY,
        )
    }


def test_claude_workload_receives_only_claude_credentials(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    definition, _, campaign = _campaign(monkeypatch)
    claude_trial = next(
        trial
        for trial in campaign.plan.trials
        if trial.provider == "claude"
    )

    workload = default_workload_factory(
        tmp_path / claude_trial.test_id,
        claude_trial,
        campaign.plan,
        definition,
        "kubernetes",
    )

    assert "--provider-id" not in workload.command
    assert workload.secret_environment == {
        "CLAUDE_CODE_OAUTH_TOKEN": (
            "claude-provider-credentials",
            "CLAUDE_CODE_OAUTH_TOKEN",
        )
    }


def test_codex_connection_is_part_of_trial_identity() -> None:
    codex = build_trials("codex", CODEX_MATRIX)[0]
    claude = build_trials("claude", CLAUDE_MATRIX)[0]

    assert codex.provider_id == "azure"
    assert codex.base_url == DEFAULT_CODEX_BASE_URL
    assert codex.environment_key == DEFAULT_CODEX_ENVIRONMENT_KEY
    assert claude.provider_id is None
    assert claude.base_url is None


def test_cluster_profiles_follow_current_brunner_security_boundary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    definition, _, campaign = _campaign(monkeypatch)

    campaign.validate()

    assert campaign.backend.network_isolation_mode == "controlled-egress"
    assert campaign.backend.reference_claim_name == "monkeybench-reference"
    assert campaign.backend.retain_failed_storage is True
    assert campaign.backend.proxy_image.endswith("4" * 64)
    assert campaign.backend.image_pull_secrets == (
        "registry-credentials",
    )
    assert campaign.controller.resource_cache_claim_name == (
        "monkeybench-resource-cache"
    )
    assert campaign.controller.reviewer_secret_environment == {
        "codex": {
            "AZURE_OPENAI_API_KEY": (
                "codex-provider-credentials",
                "AZURE_OPENAI_API_KEY",
            )
        }
    }
    assert definition.evaluation.image.endswith("3" * 64)


def test_controller_reload_reproduces_submitted_image_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    definition, contract, submitted = _campaign(monkeypatch)
    definition_environment = definition_image_environment(definition)
    campaign_environment = campaign_image_environment(submitted)
    for name in (
        "MONKEYBENCH_AGENT_IMAGE",
        "MONKEYBENCH_CONTROLLER_IMAGE",
        "MONKEYBENCH_EVALUATOR_IMAGE",
        "MONKEYBENCH_SQUID_IMAGE",
    ):
        monkeypatch.delenv(name)

    reloaded_definition = apply_definition_image_override(
        build_definition(),
        definition_environment,
    )
    reloaded_campaign = apply_campaign_image_overrides(
        build_campaign(reloaded_definition, contract),
        campaign_environment,
    )

    assert reloaded_definition.evaluation.image == (
        definition.evaluation.image
    )
    assert reloaded_campaign.to_dict() == submitted.to_dict()


def test_cluster_resources_include_controller_and_continuation_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    definition, _, campaign = _campaign(monkeypatch)
    names = campaign_resources(definition, campaign)

    resources = render_cluster_resources(
        definition,
        campaign,
        benchmark_ref="monkeybench.definition:build_reviewed_definition",
        campaign_ref="monkeybench.campaign",
    )

    assert all(item["kind"] != "Service" for item in resources)
    deployment = next(
        item for item in resources if item["kind"] == "Deployment"
    )
    preparation = next(item for item in resources if item["kind"] == "Job")
    config_maps = {
        item["metadata"]["name"]: item
        for item in resources
        if item["kind"] == "ConfigMap"
    }
    continuation_requests = json.loads(
        config_maps[names.continuation_config_map]["data"]["requests.json"]
    )
    controller_pod = deployment["spec"]["template"]["spec"]
    preparation_pod = preparation["spec"]["template"]["spec"]

    assert continuation_requests["requests"] == []
    assert continuation_requests["campaign_sha256"] == campaign.sha256
    assert controller_pod["securityContext"]["runAsNonRoot"] is True
    assert preparation_pod["securityContext"]["runAsUser"] == 1000
    assert "ports" not in controller_pod["containers"][0]
    assert "readinessProbe" not in controller_pod["containers"][0]
    assert controller_pod["containers"][0]["securityContext"][
        "readOnlyRootFilesystem"
    ] is True
    assert not any(
        item.get("valueFrom", {}).get("secretKeyRef")
        for item in controller_pod["containers"][0].get("env", ())
    )


def test_current_codex_adapter_owns_unsandboxed_candidate_execution(
    tmp_path: Path,
) -> None:
    schema = tmp_path / "schema.json"
    schema.write_text(
        json.dumps(
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["status"],
                "properties": {"status": {"type": "string"}},
            }
        )
    )
    context = ProviderRunContext(
        workspace=tmp_path,
        transcript_dir=tmp_path / "transcript",
        final_schema_path=schema,
        final_output_path=tmp_path / "final.json",
        persist_session=False,
        resume_session=False,
        session_id=None,
    )

    command = CodexAdapter().build_command(
        ProviderSettings(
            provider="codex",
            model="gpt-5.6-sol",
            effort="low",
        ),
        context,
    ).command

    assert "--dangerously-bypass-approvals-and-sandbox" in command
    assert command[command.index("--output-schema") + 1] == str(schema)


def test_current_claude_adapter_owns_candidate_permissions(
    tmp_path: Path,
) -> None:
    schema = tmp_path / "schema.json"
    canonical_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["status"],
        "properties": {"status": {"type": "string"}},
    }
    schema.write_text(json.dumps(canonical_schema))
    context = ProviderRunContext(
        workspace=tmp_path,
        transcript_dir=tmp_path / "transcript",
        final_schema_path=schema,
        final_output_path=tmp_path / "final.json",
        persist_session=False,
        resume_session=False,
        session_id=None,
    )

    command = ClaudeAdapter().build_command(
        ProviderSettings(
            provider="claude",
            model="claude-sonnet-5",
            effort="low",
        ),
        context,
    ).command

    assert "--dangerously-skip-permissions" in command
    assert "--no-session-persistence" in command
    assert "--json-schema" in command
    provider_schema = json.loads(command[command.index("--json-schema") + 1])
    assert "$schema" not in provider_schema
    assert provider_schema["properties"] == canonical_schema["properties"]
    assert json.loads(schema.read_text()) == canonical_schema


def test_agent_image_excludes_trusted_monkeybench_code() -> None:
    root = Path(__file__).resolve().parents[1]
    agent = (root / "containers/agent.Dockerfile").read_text()
    controller = (root / "containers/controller.Dockerfile").read_text()
    dockerignore = (root / ".dockerignore").read_text()

    brunner_ref = "bb51a9eb048f6f6470fb101124de8958f1fb748b"
    assert f"ARG BRUNNER_REF={brunner_ref}" in agent
    assert f"ARG BRUNNER_REF={brunner_ref}" in controller
    assert "ARG CLAUDE_CODE_VERSION=2.1.236" in agent
    assert "COPY src" not in agent
    assert "COPY challenge" not in agent
    assert "COPY src" in controller
    assert "COPY challenge" in controller
    assert "COPY resources" in controller
    assert "COPY reference/manifest.json" in controller
    assert "COPY reference /opt" not in controller
    assert "!resources/**" in dockerignore
