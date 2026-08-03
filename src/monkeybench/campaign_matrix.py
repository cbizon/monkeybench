from __future__ import annotations

import os
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

from brunner import (
    BenchmarkDefinition,
    CampaignPlan,
    CampaignRunner,
    CampaignTrial,
)
from brunner.backends import (
    KubernetesBackend,
    KubernetesProfile,
    WorkloadSpec,
)
from brunner.campaign import default_workload_factory
from brunner.contract import OutputContract


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NAMESPACE = "bizon"
DEFAULT_AGENT_CPU = "1"
DEFAULT_AGENT_MEMORY = "4Gi"
DEFAULT_STORAGE_SIZE = "1Gi"
DEFAULT_MAX_PARALLEL = 2
BENCHMARK_UID = 1000
BENCHMARK_GID = 1000

CODEX_MATRIX = (
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

CLAUDE_MATRIX = (
    ("claude-opus-5", "max", 1),
    ("claude-opus-5", "low", 1),
    ("claude-opus-4-8", "max", 1),
    ("claude-opus-4-8", "low", 1),
    ("claude-sonnet-5", "max", 2),
    ("claude-sonnet-5", "low", 1),
)


def harden_kubernetes_manifest(
    manifest: dict[str, Any],
) -> dict[str, Any]:
    hardened = deepcopy(manifest)
    kind = hardened.get("kind")
    if kind == "Pod":
        pod_spec = hardened["spec"]
    elif kind == "Job":
        pod_spec = hardened["spec"]["template"]["spec"]
    else:
        return hardened

    pod_spec["automountServiceAccountToken"] = False
    pod_spec["terminationGracePeriodSeconds"] = 30
    pod_spec["securityContext"] = {
        "runAsNonRoot": True,
        "runAsUser": BENCHMARK_UID,
        "runAsGroup": BENCHMARK_GID,
        "fsGroup": BENCHMARK_GID,
        "seccompProfile": {"type": "RuntimeDefault"},
    }
    volumes = pod_spec.setdefault("volumes", [])
    if not any(volume.get("name") == "tmp" for volume in volumes):
        volumes.append({"name": "tmp", "emptyDir": {}})

    for container in pod_spec.get("containers", []):
        container["imagePullPolicy"] = "IfNotPresent"
        container["securityContext"] = {
            "allowPrivilegeEscalation": False,
            "capabilities": {"drop": ["ALL"]},
            "readOnlyRootFilesystem": True,
        }
        mounts = container.setdefault("volumeMounts", [])
        if not any(mount.get("name") == "tmp" for mount in mounts):
            mounts.append({"name": "tmp", "mountPath": "/tmp"})
    return hardened


class SterlingKubernetesBackend(KubernetesBackend):
    def _apply(self, manifest: dict[str, Any]) -> None:
        super()._apply(harden_kubernetes_manifest(manifest))


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _slug(value: str) -> str:
    return value.lower().replace(".", "-")


def build_trials(
    provider: str,
    matrix: tuple[tuple[str, str, int], ...],
) -> tuple[CampaignTrial, ...]:
    return tuple(
        CampaignTrial(
            test_id=(
                f"{provider}-{_slug(model)}-{effort}-r{run_number:02d}"
            ),
            provider=provider,
            model=model,
            effort=effort,
        )
        for model, effort, run_count in matrix
        for run_number in range(1, run_count + 1)
    )


def _image_pull_secrets() -> tuple[str, ...]:
    value = os.environ.get("MONKEYBENCH_IMAGE_PULL_SECRETS", "")
    return tuple(
        item.strip() for item in value.split(",") if item.strip()
    )


def _workload_factory(
    trial: Path,
    campaign_trial: CampaignTrial,
    plan: CampaignPlan,
    definition: BenchmarkDefinition,
    backend_name: str,
) -> WorkloadSpec:
    workload = default_workload_factory(
        trial,
        campaign_trial,
        plan,
        definition,
        backend_name,
    )
    command = (
        os.sys.executable if backend_name == "local" else "python",
        "-m",
        "monkeybench.remote_agent",
        str(trial) if backend_name == "local" else "/brunner/trial",
    )
    return replace(
        workload,
        command=command,
        cpu=os.environ.get(
            "MONKEYBENCH_AGENT_CPU",
            DEFAULT_AGENT_CPU,
        ),
        memory=os.environ.get(
            "MONKEYBENCH_AGENT_MEMORY",
            DEFAULT_AGENT_MEMORY,
        ),
        labels={
            **workload.labels,
            "dev.brunner/provider": campaign_trial.provider,
        },
    )


def build_kubernetes_campaign(
    definition: BenchmarkDefinition,
    contract: OutputContract,
    *,
    provider: str,
    matrix: tuple[tuple[str, str, int], ...],
    secret_name: str,
    secret_key: str,
    environment_name: str,
) -> CampaignRunner:
    image = _required_environment("MONKEYBENCH_AGENT_IMAGE")
    campaign_root = Path(
        os.environ.get(
            "MONKEYBENCH_CAMPAIGN_ROOT",
            str(ROOT / "campaign-runs"),
        )
    ).resolve()
    max_parallel = int(
        os.environ.get(
            "MONKEYBENCH_MAX_PARALLEL",
            str(DEFAULT_MAX_PARALLEL),
        )
    )
    plan = CampaignPlan(
        campaign_id=f"monkey-wbc-{provider}-model-sweep-v1",
        root=campaign_root / f"{provider}-model-sweep-v1",
        trials=build_trials(provider, matrix),
        max_parallel=max_parallel,
        backend_image=image,
        collection_retry_seconds=60,
        collection_max_attempts=5,
        max_pause_seconds=24 * 60 * 60,
        evaluation_timeout_seconds=20 * 60,
    )
    profile = KubernetesProfile(
        namespace=os.environ.get(
            "MONKEYBENCH_K8S_NAMESPACE",
            DEFAULT_NAMESPACE,
        ),
        agent_image=image,
        artifact_reader_image=image,
        storage_size=os.environ.get(
            "MONKEYBENCH_TRIAL_STORAGE_SIZE",
            DEFAULT_STORAGE_SIZE,
        ),
        storage_class_name=(
            os.environ.get("MONKEYBENCH_STORAGE_CLASS") or None
        ),
        image_pull_secrets=_image_pull_secrets(),
        secret_environment={
            environment_name: (secret_name, secret_key),
        },
        max_parallel=max_parallel,
    )
    return CampaignRunner(
        definition,
        contract,
        plan,
        SterlingKubernetesBackend(
            profile,
            kubectl=os.environ.get("MONKEYBENCH_KUBECTL", "kubectl"),
        ),
        workload_factory=_workload_factory,
    )
