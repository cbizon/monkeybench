# Monkeybench Design

## Task Definition

Given an unlabeled rhesus macaque blood-smear image and candidate-visible
training material, identify every visible white blood cell and classify it as
one of:

- `neutrophil`
- `lymphocyte`
- `monocyte`
- `eosinophil`
- `basophil`

The original Zooniverse task records a click and a cell type. Monkeybench uses
the machine-readable equivalent: a typed point near the center of each cell.

## Coordinate Contract

- Coordinates are normalized floating-point values in `[0, 1]`.
- `(0, 0)` is the top-left corner.
- `(1, 1)` is the bottom-right corner.
- `x` increases from left to right.
- `y` increases from top to bottom.
- Coordinates refer to the complete original image, before any resizing,
  cropping, padding, or display transformation.
- Each physical cell must be reported at most once.

This avoids tying submissions to a browser viewport, image viewer, or a
particular pixel resolution.

## Candidate Output

The required benchmark artifact will be JSON:

```json
{
  "schema_version": "1.0",
  "images": [
    {
      "image_id": "A",
      "detections": [
        {
          "x": 0.5123,
          "y": 0.2841,
          "cell_type": "neutrophil"
        }
      ]
    }
  ]
}
```

The output contract will require:

- One entry for every assigned image.
- No unknown or duplicate image IDs.
- Zero or more detections per image.
- Coordinates within `[0, 1]`.
- Cell types restricted to the five benchmark labels.
- No ordering requirement for detections.

## Trusted Evaluation

Reference annotations are withheld from the candidate pod. Each reference
annotation contains an image ID, normalized center point, and cell type.

Evaluation first performs one-to-one spatial matching within each image, then
evaluates the type assigned to each spatial match. This separation preserves
three distinct errors:

- A missed WBC.
- A spurious WBC.
- A correctly localized WBC assigned the wrong type.

The version 1.0 evaluator maximizes the number of one-to-one spatial matches,
then minimizes total pixel distance among assignments with equal cardinality.
A match must be within 30 pixels in the original 1056 by 816 image. This
accepts a point placed within the approximately 25-pixel answer ring while
remaining substantially smaller than the distance between distinct WBC
centers.

## Deterministic Metrics

Localization and typing are reported independently.

For localization, the evaluator reports per-image and total:

- True positives: one-to-one spatial matches within the tolerance.
- False positives: unmatched predicted points.
- False negatives: unmatched reference cells.

It also reports localization outcomes by cell type. True positives and false
negatives use the known reference type. Because false positives have no
ground-truth type, they are grouped by the type assigned by the agent.

For typing, only spatially matched cells are evaluated. The evaluator reports:

- The number of matched cells evaluated.
- Correct and incorrect type counts.
- Overall typing accuracy.
- A confusion matrix whose rows are correct/reference types and whose columns
  are assigned types.
- Correct-type row marginals and assigned-type column marginals.

There is no combined localization-and-typing score. A wrong type does not
change localization counts, and a missed or spurious location does not enter
the typing confusion matrix.

The evaluator emits separate reports:

- `evaluation/detection-report.html` contains total, per-image, and
  per-cell-type localization counts plus each source image overlaid with true
  positive, false positive, and false negative locations.
- `evaluation/identification-report.html` contains typing accuracy, the
  confusion matrix with marginal counts, and the off-diagonal identification
  errors.

It also emits `evaluation/diagnostics.json` with every matched pair, pixel
distance, type comparison, unmatched prediction/reference index, and the
normalized coordinates used by the overlays.

Brunner's generic `evaluation/run-report.html` intentionally has no benchmark
display title. Its header identifies the run and records provider, model, and
effort; links to the detection, identification, and qualitative reports follow
below the compact timing, usage, and evaluation summaries.

## Fixed Corpus

Version 1.0 evaluates all 14 practice images A through N rather than sampling
the live workflow's random ten-image queue. The reference contains:

- 34 neutrophils
- 9 eosinophils
- 5 lymphocytes
- 2 monocytes
- 0 basophils

Image F contains no WBCs and is required in every submission with an empty
detection array when classified correctly. The absence of basophils and the
strong neutrophil imbalance are reported properties of this benchmark
version, not hidden sampling behavior.

## Brunner Boundary

- The cluster preparation Job copies `challenge/` to a fresh temporary
  directory on the control PVC.
- `monkeybench.materialize_challenge` adds the checksum-verified WBC
  identification video and transcript from the resource-cache PVC.
- A resumable in-cluster stager copies the materialized challenge into each
  candidate trial PVC and verifies its per-file inventory.
- `output-contract.json` generates the staged submission and artifact schemas.
- The reference PVC is mounted read-only only by the trusted evaluator and is
  verified against the approved manifest digest.
- Candidate provider credentials are selected per trial. Evaluator,
  controller, preparation, collection, and publication workloads receive no
  candidate credentials.
- Managed Squid and NetworkPolicies limit candidate egress to provider APIs;
  helper workloads have no egress.
- `monkeybench.evaluator` runs in the trusted evaluator container and reads
  only Brunner-validated artifacts plus the mounted reference bundle.
- The cluster controller owns evaluation finalization, qualitative review,
  checksummed archive publication, and cleanup.
- `campaign-sync` copies and verifies active or terminal snapshots into a
  portable local archive. `campaign-monitor` serves only that local archive,
  while `campaign-retire` requires a verified terminal archive before deleting
  all campaign-owned cluster resources.
- Provider-credit exhaustion is terminal. Brunner retains the failed trial PVC
  and provider session, and `campaign-continue` can authorize exactly one
  resumed attempt without changing the staged workspace or workload identity.
- Pending collection and deterministic evaluation take admission priority over
  new candidate Jobs, so a newly admitted trial cannot starve evaluation of a
  completed trial.
- Claude receives a provider-specific copy of the response schema without the
  unsupported top-level Draft 2020-12 dialect marker. The canonical staged
  schema remains unchanged and governs Brunner validation.
- Browser navigation, the Zooniverse queue, Talk, and button interaction are
  outside the benchmark.
- The agent image contains Brunner and provider CLIs but no Monkeybench source,
  challenge, reference, or assessment material.

## Qualitative Review

`monkeybench.definition:build_reviewed_definition` enables the
benchmark-specific qualitative assessment with a fixed `gpt-5.6-sol` reviewer
at `xhigh` effort. The assessment is required and complements rather than
replaces the deterministic localization and typing metrics.

The reviewed definition narrows `trial_evidence_paths` to the prompt, subject
manifest, submission, deterministic results and diagnostics, transcript,
timing, usage, and status. The reviewer characterizes the observed workflow,
localization error pattern, typing confusion pattern, and class marginals. It
does not receive the candidate image corpus or materialized video and cannot
visually re-grade the cells.
Because `run_if_evaluation_failed` is enabled, a provider-error trial can still
receive a transcript and partial-work review; localization and typing are
reported as unavailable when deterministic evaluation did not run.
