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

The evaluator emits `evaluation/detection-typing-report.html` with the
per-image localization table and confusion matrix. It also emits
`evaluation/diagnostics.json` with every matched pair, pixel distance, type
comparison, and unmatched prediction/reference index.

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

- `challenge/` is copied to a fresh temporary directory on the orchestrator.
- `monkeybench.materialize_challenge` adds the checksum-verified WBC
  identification video and transcript from `BRUNNER_RESOURCE_CACHE`.
- The completed materialized challenge is copied into the agent workspace or
  pod and included in the challenge hash.
- `output-contract.json` generates the staged submission and artifact schemas.
- `reference/` is integrity-checked and withheld from the agent.
- `monkeybench.evaluator` reads only Brunner-validated artifacts and the
  trusted reference bundle.
- Browser navigation, the Zooniverse queue, Talk, and button interaction are
  outside the benchmark.
- Network access is used only by the explicit cache-population command, not by
  challenge staging or the agent.

## Qualitative Review

`monkeybench.definition:build_reviewed_definition` enables the
benchmark-specific qualitative assessment when `MONKEYBENCH_REVIEWER_MODEL`
is set. The assessment is required in that definition and complements rather
than replaces the deterministic localization and typing metrics.

The reviewed definition narrows `trial_evidence_paths` to the prompt, subject
manifest, submission, deterministic results and diagnostics, transcript,
timing, usage, and status. The reviewer characterizes the observed workflow,
localization error pattern, typing confusion pattern, and class marginals. It
does not receive the candidate image corpus or materialized video and cannot
visually re-grade the cells.
