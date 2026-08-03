from __future__ import annotations

import json
from pathlib import Path

import pytest

from brunner.contract import load_output_contract
from brunner.trial import TrialIdentity

from monkeybench.claude_wrapper import prepare_arguments
from monkeybench.codex_wrapper import (
    prepare_arguments as prepare_codex_arguments,
    strict_output_schema,
)
from monkeybench.campaign_claude import build_campaign as build_claude_campaign
from monkeybench.campaign_codex import build_campaign as build_codex_campaign
from monkeybench.campaign_matrix import (
    CLAUDE_MATRIX,
    CODEX_MATRIX,
    build_trials,
    harden_kubernetes_manifest,
)
from monkeybench.definition import build_definition
from monkeybench.remote_agent import (
    DEFAULT_CODEX_BASE_URL,
    provider_settings,
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


def test_matrix_matches_granular_benchmark_without_fable() -> None:
    assert {(model, effort) for model, effort, _ in CODEX_MATRIX} == (
        EXPECTED_CODEX
    )
    assert {(model, effort) for model, effort, _ in CLAUDE_MATRIX} == (
        EXPECTED_CLAUDE
    )
    assert all("fable" not in model for model, _, _ in CLAUDE_MATRIX)
    assert sum(count for _, _, count in CODEX_MATRIX) == 10
    assert sum(count for _, _, count in CLAUDE_MATRIX) == 7


def test_campaign_trial_ids_are_unique() -> None:
    trials = (
        *build_trials("codex", CODEX_MATRIX),
        *build_trials("claude", CLAUDE_MATRIX),
    )
    assert len(trials) == 17
    assert len({trial.test_id for trial in trials}) == len(trials)


def test_campaigns_isolate_provider_secrets(monkeypatch) -> None:
    monkeypatch.setenv(
        "MONKEYBENCH_AGENT_IMAGE",
        "ghcr.io/cbizon/monkeybench-agent:test",
    )
    definition = build_definition()
    contract = load_output_contract(definition.contract_path)

    codex = build_codex_campaign(definition, contract)
    claude = build_claude_campaign(definition, contract)

    assert codex.backend.profile.secret_environment == {
        "AZURE_OPENAI_API_KEY": (
            "balls-bench-codex-azure",
            "AZURE_OPENAI_API_KEY",
        )
    }
    assert claude.backend.profile.secret_environment == {
        "CLAUDE_CODE_OAUTH_TOKEN": (
            "balls-bench-claude-oauth",
            "CLAUDE_CODE_OAUTH_TOKEN",
        )
    }


def test_remote_workload_uses_benchmark_launcher(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(
        "MONKEYBENCH_AGENT_IMAGE",
        "ghcr.io/cbizon/monkeybench-agent:test",
    )
    definition = build_definition()
    contract = load_output_contract(definition.contract_path)
    runner = build_codex_campaign(definition, contract)
    campaign_trial = runner.plan.trials[0]
    trial = tmp_path / campaign_trial.test_id
    trial.mkdir()

    workload = runner.workload_factory(
        trial,
        campaign_trial,
        runner.plan,
        definition,
        "kubernetes",
    )

    assert workload.command == (
        "python",
        "-m",
        "monkeybench.remote_agent",
        "/brunner/trial",
    )
    assert workload.cpu == "1"
    assert workload.memory == "4Gi"
    assert runner.backend.profile.storage_class_name == "basic"


def test_kubernetes_manifest_runs_nonroot_with_writable_tmp() -> None:
    manifest = harden_kubernetes_manifest(
        {
            "kind": "Job",
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": "agent",
                                "volumeMounts": [
                                    {
                                        "name": "trial",
                                        "mountPath": "/brunner/trial",
                                    }
                                ],
                            }
                        ],
                        "volumes": [{"name": "trial"}],
                    }
                }
            },
        }
    )
    pod = manifest["spec"]["template"]["spec"]
    container = pod["containers"][0]

    assert pod["automountServiceAccountToken"] is False
    assert pod["securityContext"] == {
        "runAsNonRoot": True,
        "runAsUser": 1000,
        "runAsGroup": 1000,
        "fsGroup": 1000,
        "seccompProfile": {"type": "RuntimeDefault"},
    }
    assert {"name": "tmp", "emptyDir": {}} in pod["volumes"]
    assert {"name": "tmp", "mountPath": "/tmp"} in (
        container["volumeMounts"]
    )
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert container["securityContext"]["capabilities"] == {
        "drop": ["ALL"]
    }


def test_remote_agent_configures_azure_codex() -> None:
    settings = provider_settings(
        TrialIdentity(
            test_id="codex-test",
            provider="codex",
            model="gpt-5.6-sol",
            effort="xhigh",
        )
    )
    assert settings.provider_id == "azure"
    assert settings.base_url == DEFAULT_CODEX_BASE_URL
    assert settings.environment_key == "AZURE_OPENAI_API_KEY"


def test_remote_agent_keeps_claude_native() -> None:
    settings = provider_settings(
        TrialIdentity(
            test_id="claude-test",
            provider="claude",
            model="claude-opus-5",
            effort="max",
        )
    )
    assert settings.provider_id is None
    assert settings.base_url is None


def test_codex_wrapper_bypasses_nested_sandbox(monkeypatch) -> None:
    monkeypatch.delenv(
        "MONKEYBENCH_CODEX_BYPASS_NESTED_SANDBOX",
        raising=False,
    )
    arguments = prepare_codex_arguments(
        [
            "exec",
            "--json",
            "--sandbox",
            "workspace-write",
            "--model",
            "gpt-5.4",
        ]
    )
    assert arguments == [
        "exec",
        "--dangerously-bypass-approvals-and-sandbox",
        "--json",
        "--model",
        "gpt-5.4",
    ]


def test_codex_wrapper_requires_expected_sandbox(monkeypatch) -> None:
    monkeypatch.delenv(
        "MONKEYBENCH_CODEX_BYPASS_NESTED_SANDBOX",
        raising=False,
    )
    with pytest.raises(
        RuntimeError,
        match="does not include --sandbox",
    ):
        prepare_codex_arguments(["exec", "--json"])


def test_codex_wrapper_creates_strict_provider_schema(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.delenv(
        "MONKEYBENCH_CODEX_BYPASS_NESTED_SANDBOX",
        raising=False,
    )
    monkeypatch.setenv("CODEX_HOME", str(tmp_path / "codex-home"))
    source = tmp_path / "final-response.schema.json"
    source.write_text(
        json.dumps(
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["status"],
                "properties": {
                    "status": {"enum": ["complete", "failed"]},
                    "details": {"type": "object"},
                },
            }
        )
    )

    arguments = prepare_codex_arguments(
        [
            "exec",
            "--sandbox",
            "workspace-write",
            "--output-schema",
            str(source),
        ]
    )

    strict_path = Path(arguments[arguments.index("--output-schema") + 1])
    strict = json.loads(strict_path.read_text())
    assert strict["required"] == ["status"]
    assert strict["properties"] == {
        "status": {
            "enum": ["complete", "failed"],
            "type": "string",
        }
    }
    assert strict["additionalProperties"] is False
    assert json.loads(source.read_text())["properties"]["details"] == {
        "type": "object"
    }


def test_strict_output_schema_closes_nested_required_objects() -> None:
    assert strict_output_schema(
        {
            "type": "object",
            "required": ["payload"],
            "properties": {
                "payload": {
                    "type": "object",
                    "required": ["version"],
                    "properties": {
                        "version": {"const": "1.0"},
                        "note": {"type": "string"},
                    },
                }
            },
        }
    ) == {
        "type": "object",
        "required": ["payload"],
        "properties": {
            "payload": {
                "type": "object",
                "required": ["version"],
                "properties": {
                    "version": {
                        "const": "1.0",
                        "type": "string",
                    }
                },
                "additionalProperties": False,
            }
        },
        "additionalProperties": False,
    }


def test_claude_wrapper_enables_nested_sandbox(monkeypatch) -> None:
    monkeypatch.delenv(
        "MONKEYBENCH_CLAUDE_NESTED_SANDBOX",
        raising=False,
    )
    arguments = prepare_arguments(
        [
            "--settings",
            '{"sandbox":{"enabled":true}}',
            "--model",
            "claude-opus-5",
        ]
    )
    settings = json.loads(arguments[1])
    assert settings["sandbox"]["enableWeakerNestedSandbox"] is True
