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

See [docs/monkey-health-explorer-resources.md](docs/monkey-health-explorer-resources.md)
for the source inventory and
[docs/benchmark-design.md](docs/benchmark-design.md) for scoring semantics.
