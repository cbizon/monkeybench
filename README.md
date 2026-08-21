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
containers/                 Candidate agent and trusted controller images
deploy/                     Sterling PVC declarations
tests/                      Contract, isolation, scoring, and trial tests
```

Brunner's trusted cluster preparation Job copies `challenge/` to a temporary
location and runs the benchmark materializer there. The materializer adds the
task-relevant WBC identification video and its English transcript from a
checksum-verified resource-cache PVC. Brunner stages only that materialized
challenge and the generated schemas onto the candidate trial PVC. The
reference bundle is mounted from a separate read-only PVC only for trusted
evaluation.

## Qualitative Review

The default definition runs only deterministic localization and typing
evaluation. Campaigns use the reviewed definition with a fixed
`gpt-5.6-sol` reviewer at `xhigh` effort. The reviewer identity is intentionally
deterministic because the cluster controller reloads and verifies the same
definition after laptop submission.

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

For a local stage, `BRUNNER_RESOURCE_CACHE` may point at `.resource-cache`.
For Sterling, copy that cache into the `monkeybench-resource-cache` RWX PVC.
Only the trusted preparation Job mounts it. The video is not committed to this
repository and is not built into either runtime image.

To refresh upstream resources and rebuild reference integrity metadata:

```bash
uv run python scripts/fetch_resources.py
uv run python -m monkeybench.reference_validation
uv run brunner --benchmark monkeybench.definition reference-build
```

`scripts/detect_answer_rings.py` reproduces the cyan-ring center extraction
used to curate `reference/expected-cells.json`. Cell types remain explicitly
checked against the answer labels and source metadata.

## Sterling Campaign

The Sterling campaign uses one shared agent image and one Brunner campaign
containing both Codex and Claude trials. It reproduces the current
`granular_benchmark` model/effort matrix with Fable omitted:

- Codex: `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`, and
  `gpt-5.4`, each at `xhigh` and `low`.
- Claude: `claude-opus-5` and `claude-opus-4-8` at `max` and `low`;
  `claude-sonnet-5` at `max` and `low`.

The full campaign has 16 deterministic trial IDs and is serialized by default.
The fixed canary campaign contains `codex-gpt-5-4-low-r01` and
`claude-sonnet-5-low-r01`. Campaign state is cluster-resident and append-only
by trial ID.

### Build the images

The agent image contains only Brunner, Codex, Claude Code, and candidate image
inspection tools. It does not contain Monkeybench source, challenge images,
reference answers, qualitative materials, or the training video. Current
Brunner owns provider invocation, schema delivery, retries, transcripts,
usage, and timing. For Claude, Brunner derives a provider-specific schema that
omits the unsupported top-level Draft 2020-12 dialect marker while retaining
the unchanged staged schema as the canonical validation contract.

The controller image contains Brunner, `kubectl`, Monkeybench, the challenge
template, the reference manifest, and the fixed qualitative-review runtime.
It is also used as the trusted evaluator and artifact-reader image. Reference
answers remain on the separate reference PVC.

```bash
export RELEASE=brunner-0994ab5
export KUBECTL_VERSION=v1.31.9

docker buildx build --platform linux/amd64 \
  -f containers/agent.Dockerfile \
  -t "ghcr.io/cbizon/monkeybench-agent:$RELEASE" \
  --push .

docker buildx build --platform linux/amd64 \
  --build-arg KUBECTL_VERSION="$KUBECTL_VERSION" \
  -f containers/controller.Dockerfile \
  -t "ghcr.io/cbizon/monkeybench-controller:$RELEASE" \
  --push .
```

Resolve both pushed digests and use `image@sha256:...` values below. The
campaign also pins the managed Squid image. Mutable tags are rejected before
candidate work starts.

### Configure Sterling inputs

The campaign references these existing Secrets:

- `codex-provider-credentials`, key `AZURE_OPENAI_API_KEY`
- `claude-provider-credentials`, key `CLAUDE_CODE_OAUTH_TOKEN`
- `registry-credentials`, a Docker registry Secret

Create two RWX `basic` PVCs before submission:

```bash
kubectl apply -f deploy/sterling-storage.yaml
```

- `monkeybench-reference`: copy the contents of `reference/` to its root.
- `monkeybench-resource-cache`: copy the contents of `.resource-cache/` to its
  root after running `scripts/fetch_external_training.py`.

Annotate the reference PVC with the exact manifest-file digest:

```bash
REFERENCE_SHA256=$(shasum -a 256 reference/manifest.json | awk '{print $1}')
kubectl --namespace bizon annotate pvc monkeybench-reference \
  "dev.brunner/reference-manifest-sha256=$REFERENCE_SHA256" \
  --overwrite
```

### Run the campaigns

```bash
export MONKEYBENCH_AGENT_IMAGE=\
"ghcr.io/cbizon/monkeybench-agent@sha256:AGENT_DIGEST"
export MONKEYBENCH_CONTROLLER_IMAGE=\
"ghcr.io/cbizon/monkeybench-controller@sha256:CONTROLLER_DIGEST"
export MONKEYBENCH_EVALUATOR_IMAGE="$MONKEYBENCH_CONTROLLER_IMAGE"

# Submit the fixed two-provider canary.
uv run brunner \
  --benchmark monkeybench.definition:build_reviewed_definition \
  campaign-submit monkeybench.campaign:build_canary_campaign

uv run brunner \
  --benchmark monkeybench.definition:build_reviewed_definition \
  campaign-status monkeybench.campaign:build_canary_campaign

uv run brunner \
  --benchmark monkeybench.definition:build_reviewed_definition \
  campaign-monitor monkeybench.campaign:build_canary_campaign \
  --local-port 8766

uv run brunner \
  --benchmark monkeybench.definition:build_reviewed_definition \
  campaign-retrieve monkeybench.campaign:build_canary_campaign \
  ./monkeybench-canary-results

# Submit the full serialized model sweep after the canary passes.
uv run brunner \
  --benchmark monkeybench.definition:build_reviewed_definition \
  campaign-submit monkeybench.campaign
```

Each candidate requests 500 millicores and 4 GiB, may burst to 2 CPUs and
8 GiB, and receives a 2 GiB trial PVC. The runtime limit is 12 hours so a
Claude trial can survive a subscription reset. The cluster controller owns
preparation, reconciliation, trusted evaluation, review, publication,
dashboard serving, and cleanup even when the laptop disconnects.
When a candidate Job exits, Brunner finishes its collection and deterministic
evaluation before admitting another candidate. This prevents the next trial
from consuming resources needed to evaluate the completed one.
Use `campaign-delete` to remove a campaign control plane; add
`--delete-results` only when its finalized results PVC should also be removed.

### Analyze campaigns

Collect normalized tables from historical `campaign-runs/` directories or a
new checksum-verified `campaign-retrieve` destination:

```bash
uv run python scripts/collect_campaign_metrics.py \
  monkeybench-results \
  --output-dir analysis-output

uv run python scripts/plot_campaign_metrics.py \
  analysis-output \
  --output-dir analysis-output/charts
```

The collector writes `runs.csv`, `cell_types.csv`, `confusion_matrix.csv`, and
`analysis.json`. Re-running it safely refreshes the tables as additional trials
are collected. The plotter writes PNG and SVG charts plus
`analysis-output/charts/index.html`. Detection counts are ranked by true
positives and identification bars are ranked by accuracy. Separate scatter
plots compare detection F1 and identification accuracy with total tokens and
agent-active time. Paired model plots join low and xhigh effort results and
order models by the absolute performance gap.

`runs.csv` includes detection TP/FP/FN, precision, recall, F1, overall typing
accuracy, model and effort, Brunner timing partitions, and normalized token
counts. `cell_types.csv` includes localization recall and typing accuracy for
each true cell type. False positives are reported only at run level because
they do not have a known reference cell type.

`inference_time_proxy_seconds` duplicates Brunner's `agent_active_seconds`,
which is the closest available inference-time proxy. It also includes provider
latency and orchestration, so it should not be interpreted as pure model
compute time.

See [docs/monkey-health-explorer-resources.md](docs/monkey-health-explorer-resources.md)
for the source inventory and
[docs/benchmark-design.md](docs/benchmark-design.md) for scoring semantics.
