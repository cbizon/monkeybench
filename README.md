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
qualitative/                Benchmark-specific reviewer prompt, rubric, schema
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
evaluation. Campaign runs use the reviewed definition, which defaults to
`gpt-5.6-sol` at `xhigh` effort. Override either value only when deliberately
testing reviewer behavior:

```bash
MONKEYBENCH_REVIEWER_MODEL=<model> \
MONKEYBENCH_REVIEWER_EFFORT=<effort> \
  uv run brunner \
  --benchmark monkeybench.definition:build_reviewed_definition \
  local-run runs/ \
  --provider codex \
  --model <candidate-model> \
  --effort high
```

The benchmark-specific review characterizes the transcript, summarizes
localization performance from per-image and total `TP`/`FP`/`FN`, and
interprets the typing accuracy and confusion matrix. It is required by the
reviewed definition and runs after deterministic evaluation, including when
that evaluation fails.

Its evidence is deliberately limited to deterministic results and diagnostics,
the rendered prompt, subject manifest, candidate submission, transcript,
timing, usage, and status. It does not duplicate the staged image corpus or
training video into the isolated reviewer workspace and does not visually
re-grade the cells.

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

The Sterling campaign uses one shared agent image and one Brunner campaign
containing both Codex and Claude trials. It reproduces the current
`granular_benchmark` model/effort matrix with Fable omitted:

- Codex: `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`, and
  `gpt-5.4`, each at `xhigh` and `low`.
- Claude: `claude-opus-5` and `claude-opus-4-8` at `max` and `low`;
  `claude-sonnet-5` at `max` and `low`.

The resulting campaign has 16 unique trials. Campaign trial IDs are
deterministic, and rerunning the command resumes its existing Brunner state.

Brunner currently configures Kubernetes Secret references on the campaign
profile rather than on individual workloads. Consequently, this combined
campaign mounts both provider credentials into every agent Job even though
the launcher uses only the credential for that trial's provider. This is a
temporary loss of least-privilege isolation until Brunner supports
per-workload Secret references.

### Build the agent image

The agent image contains Brunner, this package's remote launcher, Codex,
Claude Code, Pillow-compatible Python tooling, ImageMagick, and Poppler. It
does not contain the challenge images, reference answers, or training video.
The trial pod is the security boundary. The Codex launcher disables its
unavailable nested bubblewrap sandbox, and Brunner runs Claude with permission
bypass rather than attempting unsupported nested sandboxing. Generated
Sterling Pods and Jobs run as UID/GID 1000 with a read-only root filesystem, a
writable ephemeral `/tmp`, dropped capabilities, and the trial PVC assigned
through `fsGroup`.
Set
`MONKEYBENCH_CODEX_BYPASS_NESTED_SANDBOX=false` only in an environment where
unprivileged user namespaces work inside the container.

```bash
export GHCR_OWNER=cbizon
export IMAGE_TAG=brunner-8a7008d
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
mounted images on demand. Keep `IMAGE_TAG` from the build step above;
`brunner-9d71d2d` predates Brunner's Kubernetes helper working-directory fix
and cannot stage this image onto a fresh Sterling PVC.

```bash
uv run python scripts/fetch_external_training.py

export BRUNNER_RESOURCE_CACHE="$PWD/.resource-cache"
export MONKEYBENCH_AGENT_IMAGE=\
"ghcr.io/cbizon/monkeybench-agent:$IMAGE_TAG"
export MONKEYBENCH_K8S_NAMESPACE=bizon
export MONKEYBENCH_REVIEWER_MODEL=gpt-5.6-sol
export MONKEYBENCH_REVIEWER_EFFORT=xhigh

# Run one Codex and one Claude canary in an isolated subset campaign.
MONKEYBENCH_TRIAL_IDS=codex-gpt-5-4-low-r01,claude-sonnet-5-low-r01 \
MONKEYBENCH_MAX_PARALLEL=2 \
uv run brunner \
  --benchmark monkeybench.definition:build_reviewed_definition \
  campaign-run monkeybench.campaign \
  --poll-seconds 30

# Run the complete campaign after both canaries pass.
uv run brunner \
  --benchmark monkeybench.definition:build_reviewed_definition \
  campaign-run monkeybench.campaign \
  --poll-seconds 30
```

Brunner enforces a default cap of four concurrent trials. Each agent Job
requests and is limited to 500 millicores and 4 GiB memory, with a 1 GiB
`basic` PVC per trial. At the default cap, agents reserve 2 CPUs and 16 GiB
memory in total.
The fixed qualitative reviewer runs on the orchestrator after each
deterministic evaluation and uses the local `AZURE_OPENAI_API_KEY`.
`MONKEYBENCH_TRIAL_IDS` accepts a comma-separated list of exact deterministic
trial IDs. A selected subset receives its own deterministic state directory,
so canaries cannot alter the full campaign state.
Override these with `MONKEYBENCH_MAX_PARALLEL`, `MONKEYBENCH_AGENT_CPU`,
`MONKEYBENCH_AGENT_MEMORY`, `MONKEYBENCH_TRIAL_STORAGE_SIZE`, and
`MONKEYBENCH_STORAGE_CLASS`. `MONKEYBENCH_MAX_PARALLEL` is applied both by the
campaign scheduler and by Brunner's namespace-level Kubernetes capacity check.

Campaign state and dashboards are written under `campaign-runs/`. A remote
agent Job continues if the orchestrator disconnects; rerun the same
`campaign-run` command to collect, evaluate, and clean up completed work.
Trusted references stay local to the orchestrator and are never uploaded to
the agent PVC. Set `MONKEYBENCH_CAMPAIGN_ROOT` to place campaign state
elsewhere.

The full campaign dashboard is `campaign-runs/model-sweep-v1/index.html`.
Brunner regenerates it after state transitions but does not serve it. Serve
the campaign directory locally with:

```bash
uv run python -m http.server 8000 --directory campaign-runs
```

Then open `http://localhost:8000/model-sweep-v1/`.

See [docs/monkey-health-explorer-resources.md](docs/monkey-health-explorer-resources.md)
for the source inventory and
[docs/benchmark-design.md](docs/benchmark-design.md) for scoring semantics.
