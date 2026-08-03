# Monkeybench

Monkeybench is a Brunner benchmark derived from the Monkey Health Explorer
beginner practice workflow. An agent receives 14 unlabeled rhesus macaque
blood-smear images plus the project tutorial and white blood cell guides. It
must report every visible white blood cell as a normalized center point and
one of five cell types.

The benchmark evaluates all 14 images. The trusted reference contains 50
cells: 34 neutrophils, 9 eosinophils, 5 lymphocytes, 2 monocytes, and no
basophils. Image F is the no-WBC negative control.

## Layout

```text
challenge/                  Candidate-visible images and training material
reference/                  Withheld answer images and typed point annotations
resources/                  Source and external-asset checksum manifests
src/monkeybench/            Brunner definition, evaluator, matching, validation
output-contract.json        Submission and artifact contract
scripts/                    Resource fetch and answer-ring extraction tools
containers/                 Optional trusted evaluator image
tests/                      Contract, isolation, scoring, and trial tests
```

Brunner first copies `challenge/` to a temporary location and runs the
benchmark materializer there. The materializer adds the task-relevant WBC
identification video and its English transcript from a checksum-verified
resource cache. Brunner then copies only that materialized challenge and the
generated schemas into the agent workspace or pod. It validates
`reference/manifest.json` separately and makes that bundle available only to
trusted evaluation.

## Qualitative Review

The default definition runs only deterministic localization and typing
evaluation. To add Brunner's standard, non-gating qualitative review, provide
an explicit fixed reviewer model and select the reviewed definition:

```bash
MONKEYBENCH_REVIEWER_MODEL=<model> \
  uv run brunner \
  --benchmark monkeybench.definition:build_reviewed_definition \
  local-run runs/ \
  --provider codex \
  --model <candidate-model> \
  --effort high
```

The review runs after deterministic evaluation, including when that
evaluation fails. Its evidence is deliberately limited to the rendered
prompt, subject manifest, candidate submission, evaluator diagnostics,
transcript, timing, usage, and status. It does not duplicate the staged image
corpus or training video into the isolated reviewer workspace.

## Local Setup

```bash
uv sync --all-groups
uv run python scripts/fetch_external_training.py
uv run brunner --benchmark monkeybench.definition contract-check
uv run brunner --benchmark monkeybench.definition reference-validate
uv run pytest --cov=monkeybench
```

To inspect the exact candidate workspace:

```bash
uv run brunner --benchmark monkeybench.definition stage staged/monkeybench
```

For Sterling or another orchestrated deployment, pre-populate a persistent
cache with `scripts/fetch_external_training.py`, set
`BRUNNER_RESOURCE_CACHE` to that cache root as an absolute path, and run
Brunner normally. The materializer copies the verified assets into
`training/videos/` before Brunner hashes and submits the challenge. The video
is not committed to this repository and does not need to be built into the
agent image.

To refresh upstream resources and rebuild reference integrity metadata:

```bash
uv run python scripts/fetch_resources.py
uv run python -m monkeybench.reference_validation
uv run brunner --benchmark monkeybench.definition reference-build
```

`scripts/detect_answer_rings.py` reproduces the cyan-ring center extraction
used to curate `reference/expected-cells.json`. Cell types remain explicitly
checked against the answer labels and source metadata.

## Evaluator Image

The optional trusted evaluator image is built from the parent `experiments`
directory so the local Brunner checkout is available:

```bash
docker build \
  -f monkeybench/containers/evaluator.Dockerfile \
  -t monkeybench-evaluator:1.0.0 \
  .
```

Set `MONKEYBENCH_EVALUATOR_IMAGE` to the pushed image name when the evaluator
should run in a container. Agent pod images and provider/model campaign
settings remain Brunner deployment configuration and are not hard-coded here.

## Sterling Campaign

The Sterling campaign uses one shared agent image but two Brunner campaign
modules so Codex and Claude credentials are never mounted into the same pod.
Together the modules reproduce the current `granular_benchmark` model/effort
matrix with Fable omitted:

- Codex: `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`, and
  `gpt-5.4`, each at `xhigh` and `low`.
- Claude: `claude-opus-5` and `claude-opus-4-8` at `max` and `low`;
  `claude-sonnet-5` at `max` twice and `low` once.

The resulting campaign has 17 trials. Campaign trial IDs are deterministic,
and rerunning either command resumes its existing Brunner state.

### Build the agent image

The agent image contains Brunner, this package's remote launcher, Codex,
Claude Code, Pillow-compatible Python tooling, ImageMagick, and Poppler. It
does not contain the challenge images, reference answers, or training video.
The trial pod is the security boundary: the Codex launcher disables its
unavailable nested bubblewrap sandbox, while the Claude launcher enables
Claude Code's weaker nested sandbox mode. Generated Sterling Pods and Jobs run
as UID/GID 1000 with a read-only root filesystem, a writable ephemeral
`/tmp`, dropped capabilities, and the trial PVC assigned through `fsGroup`.
Set
`MONKEYBENCH_CODEX_BYPASS_NESTED_SANDBOX=false` only in an environment where
unprivileged user namespaces work inside the container.

```bash
export GHCR_OWNER=cbizon
export IMAGE_TAG=monkeybench-v1
export MONKEYBENCH_AGENT_IMAGE=\
"ghcr.io/$GHCR_OWNER/monkeybench-agent:$IMAGE_TAG"

docker build \
  --platform linux/amd64 \
  -f containers/agent.Dockerfile \
  -t "$MONKEYBENCH_AGENT_IMAGE" \
  .
docker push "$MONKEYBENCH_AGENT_IMAGE"
```

Make the GHCR package public, or set
`MONKEYBENCH_IMAGE_PULL_SECRETS` to a comma-separated list of Kubernetes
image-pull Secret names.

### Configure provider Secrets

The default Secret names and keys match the existing granular benchmark
deployment:

```bash
kubectl config use-context bizon@sterling

kubectl --namespace bizon create secret generic \
  balls-bench-codex-azure \
  --from-literal=AZURE_OPENAI_API_KEY="$AZURE_OPENAI_API_KEY" \
  --dry-run=client -o yaml \
  | kubectl apply -f -

kubectl --namespace bizon create secret generic \
  balls-bench-claude-oauth \
  --from-literal=CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN" \
  --dry-run=client -o yaml \
  | kubectl apply -f -
```

Override `MONKEYBENCH_CODEX_SECRET`, `MONKEYBENCH_CLAUDE_SECRET`, or their
corresponding `*_SECRET_KEY` variables if different Secrets are used.
Codex is configured for RENCI Azure OpenAI by the remote launcher; its base
URL can be overridden with `MONKEYBENCH_CODEX_BASE_URL`.

### Run the campaigns

Populate the external resource cache and use an absolute cache path. Brunner
materializes the video and transcript into each fresh challenge before it
creates or uploads the trial. The complete candidate workspace is then copied
to the trial PVC, where Codex `view_image` and Claude `Read` can inspect the
mounted images on demand.

```bash
uv run python scripts/fetch_external_training.py

export BRUNNER_RESOURCE_CACHE="$PWD/.resource-cache"
export MONKEYBENCH_AGENT_IMAGE=\
"ghcr.io/cbizon/monkeybench-agent:monkeybench-v1"
export MONKEYBENCH_K8S_NAMESPACE=bizon

uv run brunner \
  --benchmark monkeybench.definition \
  campaign-run monkeybench.campaign_codex \
  --poll-seconds 30

uv run brunner \
  --benchmark monkeybench.definition \
  campaign-run monkeybench.campaign_claude \
  --poll-seconds 30
```

The two campaigns may be run concurrently in separate terminals. Both default
to two concurrent trials, one CPU, 4 GiB memory, and a 1 GiB PVC per trial.
Override these with `MONKEYBENCH_MAX_PARALLEL`, `MONKEYBENCH_AGENT_CPU`,
`MONKEYBENCH_AGENT_MEMORY`, and `MONKEYBENCH_TRIAL_STORAGE_SIZE`.

Campaign state and dashboards are written under `campaign-runs/`. A remote
agent Job continues if the orchestrator disconnects; rerun the same
`campaign-run` command to collect, evaluate, and clean up completed work.
Trusted references stay local to the orchestrator and are never uploaded to
the agent PVC. Set `MONKEYBENCH_CAMPAIGN_ROOT` to place campaign state
elsewhere.

See [docs/monkey-health-explorer-resources.md](docs/monkey-health-explorer-resources.md)
for the source inventory and
[docs/benchmark-design.md](docs/benchmark-design.md) for scoring semantics.
