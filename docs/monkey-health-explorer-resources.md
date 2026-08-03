# Monkey Health Explorer Resources

Snapshot date: 2026-07-31

## Purpose

This document records the public data, training material, and actual behavior
of the Monkey Health Explorer beginner practice workflow. It is the source
inventory for constructing a Brunner benchmark without depending on browser
automation or the live Zooniverse user interface.

The source project is:

- Project: `Monkey Health Explorer`
- Zooniverse project ID: `6250`
- Project URL:
  <https://www.zooniverse.org/projects/mbarrierz/monkey-health-explorer>
- Beginner workflow ID: `14984`
- Displayed workflow name: `Beginner's Pratice - Start Here`
- Workflow URL:
  <https://www.zooniverse.org/projects/mbarrierz/monkey-health-explorer/classify/workflow/14984>

## Brunner Boundary

Brunner expects benchmark-owned challenge inputs, an output contract, trusted
evaluation code, and optional trusted references. For this benchmark:

- Candidate-visible material should include the unlabeled blood-smear images,
  the selected instructional material, and a manifest containing only the
  identifiers and filenames needed to perform the task.
- Trusted reference material should include the labeled answer images, cell
  counts, expected cell locations or classifications, and evaluator data.
- The answer images and labels must not be placed under `challenge/` or copied
  into the agent image. They belong under `reference/` and should be mounted
  only for trusted evaluation.
- The live Zooniverse page, subject queue, marking interface, and Talk workflow
  are not part of the benchmark runtime. All required resources should be
  downloaded and checksummed before a run.
- Large candidate-visible resources that are not committed are stored in a
  Brunner resource cache and copied into the fresh challenge by the benchmark
  materializer before staging.

This follows Brunner's lifecycle:

```text
isolated agent execution -> submission -> verified collection
                         -> trusted evaluation
```

## Practice Dataset

The actual practice set is Zooniverse subject set `75322`, named
`PracticeSet`. It contains 14 subjects. Each subject has two JPEG locations:

1. An unlabeled blood-smear image named `Practice-<ID>.JPG`.
2. A labeled answer image named `Practice-<ID>_A.JPG`.

Each answer image is a copy of the smear with circles and cell-type labels.
The public subject metadata also contains the correct count for each cell
type.

| ID | Neutrophils | Lymphocytes | Monocytes | Eosinophils | Basophils | Total WBCs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 2 | 1 | 0 | 0 | 0 | 3 |
| B | 2 | 0 | 0 | 0 | 0 | 2 |
| C | 1 | 0 | 0 | 2 | 0 | 3 |
| D | 4 | 0 | 0 | 0 | 0 | 4 |
| E | 3 | 1 | 1 | 2 | 0 | 7 |
| F | 0 | 0 | 0 | 0 | 0 | 0 |
| G | 5 | 0 | 0 | 1 | 0 | 6 |
| H | 2 | 1 | 0 | 1 | 0 | 4 |
| I | 2 | 0 | 0 | 0 | 0 | 2 |
| J | 3 | 0 | 0 | 0 | 0 | 3 |
| K | 5 | 0 | 0 | 0 | 0 | 5 |
| L | 2 | 1 | 0 | 1 | 0 | 4 |
| M | 1 | 0 | 0 | 2 | 0 | 3 |
| N | 2 | 1 | 1 | 0 | 0 | 4 |
| **Total** | **34** | **5** | **2** | **9** | **0** | **50** |

Important dataset properties:

- The 14 subjects contain 50 labeled white blood cells.
- Neutrophils dominate the set: 34 of 50 cells.
- There are no basophils, even though basophils are one of the five taught
  classes.
- Subject F is a negative example containing no WBCs.
- Monocytes are represented by only two examples.

The full subject inventory can be retrieved from:

```text
https://www.zooniverse.org/api/subjects?subject_set_id=75322&page_size=100
```

The subject-set metadata is available from:

```text
https://www.zooniverse.org/api/subject_sets/75322
```

## Queue And Selection Behavior

The workflow is not ordered. The Zooniverse front end uses its default random
queued-subject selection for this workflow:

```text
https://www.zooniverse.org/api/subjects/queued?workflow_id=14984
```

Observed behavior:

- The source set contains 14 subjects.
- A queue request returns 10 subjects.
- Repeated requests return different 10-subject subsets and different orders.
- Subjects use the `never_retire` retirement strategy, so they remain
  available for practice.
- After a signed-in user has seen the available subjects, Zooniverse can mark
  them as already seen. The workflow instructions treat this as the signal to
  move to a production workflow.

Random queue behavior is a property of the live presentation layer. The
benchmark should define its own explicit cases and trial sampling rather than
depending on this endpoint at runtime.

## Workflow Configuration

The public workflow record is available from:

```text
https://www.zooniverse.org/api/workflows/14984
```

Relevant settings include:

- `subjects_count`: `14`
- `multi_image_mode`: `flipbook`
- `persist_annotations`: `true`
- `multi_image_clone_markers`: `true`
- `pan_and_zoom`: `true`
- retirement criteria: `never_retire`
- linked subject set: `75322`

The cloned-marker setting causes marks made on the unlabeled frame to remain
visible when viewing the labeled answer frame. This supports visual
self-comparison.

The workflow also contains `training_set_ids: [75332]`. Subject set `75332`
is named `GRU_S1_batch_4`, contains 9,597 camera-trap subjects, and belongs to
another Zooniverse project (`5115`). It was not returned by the beginner
workflow queue during inspection. Treat this as stale or erroneous
configuration, not as Monkey Health Explorer benchmark data.

## Tutorial

The workflow opens a six-step Zooniverse tutorial. Its source is:

```text
https://www.zooniverse.org/api/tutorials?workflow_id=14984
```

The tutorial teaches:

1. Identify five WBC classes: neutrophil, lymphocyte, monocyte, eosinophil,
   and basophil.
2. Do not mark red blood cells, platelets, or cellular debris.
3. Use image navigation, task help, and the Field Guide.
4. In workflows that use it, apply the "Goldilocks Test" to recognize sparse,
   overly thick, acceptable, or low-quality smears.
5. Click each WBC, select its type, make a best guess when morphology is
   ambiguous, and mark identifiable cells at an image edge.
6. Zoom out, compare work with the answer image, complete the self-assessment,
   and move to a production workflow.

The tutorial is introductory workflow guidance. Most of the substantive cell
recognition material is in the Field Guide.

## Field Guide

The shared project Field Guide is available from:

```text
https://www.zooniverse.org/api/field_guides?project_id=6250
```

It contains:

- Three YouTube videos:
  - Marking cells: <https://www.youtube.com/watch?v=n1cTsCz4LrI>
  - Using Talk: <https://www.youtube.com/watch?v=griEnT82RT8>
  - Identifying WBCs: <https://www.youtube.com/watch?v=jauLFRhVr8U>
- An activity FAQ covering ambiguous morphology, staining variation, blurry
  images, images with no WBCs, edge cells, and editing marks.
- A composite WBC example sheet.
- Separate image guides for neutrophils, lymphocytes, monocytes, eosinophils,
  and basophils.
- Examples of cell spread that is too sparse, too thick, or acceptable.
- A "Not a White Blood Cell" guide covering burst cells, platelets, cell
  fakes, overstained red cells, and general debris.
- A printable two-page WBC reference PDF.
- Reptile blood-cell materials that share the project Field Guide but are not
  part of the monkey beginner practice task.

Monkeybench includes only the identifying-WBC video because it teaches the
classification task. The marking-cells and Talk videos teach browser
interaction that this benchmark deliberately excludes. The selected video
and its official English transcript are checksum-pinned in
`resources/external-training-assets.json` and materialized into
`challenge/training/videos/` at staging time.

The printable WBC guide is:

```text
https://panoptes-uploads.zooniverse.org/project_attached_image/fba9b1ce-75e6-4569-93e7-f17349bb28f7.pdf
```

### Morphology Summary

- **Neutrophil:** Usually 2-3 times larger than an RBC. Light pinkish
  cytoplasm with small granules and sometimes a vacuole. Dark purple nucleus
  with multiple connected shapes; less-common C- or U-shaped forms are shown.
- **Lymphocyte:** Nucleus only slightly larger than an RBC. Light, often
  bluish, clear cytoplasm without granules. Rounded dark-purple nucleus that
  fills most of the cell; a less-common flower-like form is shown.
- **Monocyte:** Usually 2-3 times larger than an RBC. Light, often bluish,
  clear cytoplasm without granules and sometimes with vacuoles. Irregular,
  C-shaped, or bean-shaped dark-purple nucleus.
- **Eosinophil:** Usually 2-3 times larger than an RBC. Darker red or purplish
  cytoplasm with medium-sized granules. Dark-purple nucleus with two or three
  rounded connected shapes.
- **Basophil:** Usually 2-3 times larger than an RBC. Large dark-purple
  granules fill the cytoplasm and mostly hide a bean-shaped nucleus.

The guide displays human frequency ranges but states that the example images
come from project slides. Staining color varies between slides and years.

### Non-WBC Guidance

- Do not mark burst cells unless enough remains intact for confident
  identification.
- Large platelets can resemble lymphocytes but lack the characteristic dark
  nucleus surrounded by lighter cytoplasm and a cell membrane.
- Platelets or debris on an RBC can create a "cell fake" resembling a WBC.
- Overstained or debris-covered RBCs can appear abnormally dark.
- Do not classify cell-sized debris or cells obscured too heavily by debris.

## Actual Practice Flow

The live workflow behaves as follows:

1. The six-step tutorial opens, but the user can close it.
2. A random practice subject appears as a two-frame flipbook.
3. The user marks every suspected WBC with a point and assigns one of the five
   cell types.
4. The second thumbnail displays the static labeled answer image.
5. The user clicks task `Next`.
6. The second task asks, "How did you do?" and provides one response:
   "I've checked my answers and am ready for the next one."
7. `Done` submits the classification. `Done & Talk` also opens the subject's
   discussion page.
8. After the practice images are exhausted, the user manually returns to the
   project page and selects a production workflow.

This is self-guided practice, not an automated proficiency test:

- There is no automatic comparison between user marks and the answer key.
- There is no score, threshold, pass/fail result, or gate.
- The answer image is accessible before task completion.
- `Subject Info` exposes the expected count for every cell type.
- The completion response only confirms that the user checked the answer.

For Monkeybench, any scoring and withholding of answers must therefore be
implemented in the benchmark evaluator rather than copied from the live
workflow.

## Additional Education Resources

The project Education page provides a larger classroom-oriented collection:

<https://www.zooniverse.org/projects/mbarrierz/monkey-health-explorer/about/education>

Available material includes:

- Two versions of a middle/high-school classroom lesson plan.
- Classroom slide decks.
- Student classification worksheets and answer keys.
- Labeled and unlabeled blood-smear image sets.
- English and Spanish materials.
- Printable blood-slide flash cards and keys.
- A blood-smear field guide.
- Project information sheets.
- Blood-smear model worksheets and crosswords.
- Student datasets, summaries, formulas, and t-test answer files.
- A simplified online lesson and activity worksheet.
- Related research articles.

These are optional benchmark resources. They should not be copied wholesale
until the benchmark task establishes whether the model is expected to learn
from the compact Field Guide, from classroom instruction, or from both.

## Recommended Local Asset Split

When resources are downloaded, use a trust-aware layout such as:

```text
challenge/
  prompt.md
  inputs/
    subjects.json
    images/
      Practice-A.JPG
      ...
      Practice-N.JPG
  training/
    tutorial.json
    field-guide.json
    wbc-guide.pdf
    images/
reference/
  manifest.json
  expected-cells.json
  answer-images/
    Practice-A_A.JPG
    ...
    Practice-N_A.JPG
docs/
  monkey-health-explorer-resources.md
```

`challenge/inputs/subjects.json` should omit answer counts and answer-image
URLs. `reference/expected-cells.json` should contain the normalized truth used
by the evaluator. Every downloaded source should be recorded in a manifest
with its original URL, byte size, SHA-256 digest, retrieval date, and intended
trust zone.

## Benchmark Task

The benchmark will evaluate **white blood cell localization and type**. This
matches the original volunteer interaction:

1. Find a white blood cell.
2. Click approximately at the center of the cell.
3. Assign one of the five cell types.

The agent will replace the browser click with a structured point annotation.
For each input image it must return zero or more detections containing:

- `x`: horizontal position normalized to `[0, 1]`
- `y`: vertical position normalized to `[0, 1]`
- `cell_type`: one of `neutrophil`, `lymphocyte`, `monocyte`, `eosinophil`,
  or `basophil`

Coordinates use the top-left of the image as `(0, 0)` and the bottom-right as
`(1, 1)`. A point should identify the approximate center of the cell. The
normalized representation is independent of display scaling, browser zoom,
pod tooling, and source image dimensions.

The candidate artifact should have this general shape:

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
    },
    {
      "image_id": "F",
      "detections": []
    }
  ]
}
```

Every assigned input image must have exactly one result entry, including
images for which the agent detects no WBCs. Detection order has no meaning.
Confidence scores are not required for the initial benchmark.

## Evaluation Semantics

Trusted reference data must contain one normalized center point and cell type
for every labeled WBC. The evaluator should:

1. Match predicted and reference points within each image using a one-to-one
   minimum-distance assignment.
2. Apply a fixed localization tolerance defined by the benchmark version.
3. Match by location before judging type, so a correctly localized cell with
   the wrong type is distinguishable from a missed cell plus a false positive.
4. Report unmatched references as false negatives.
5. Report unmatched predictions as false positives.
6. Report the cell-type result for every spatially matched pair.

Primary metrics should include:

- Localization precision, recall, and F1.
- Cell-type accuracy on spatially matched detections.
- Per-class precision, recall, and F1.
- Joint localization-and-type precision, recall, and F1.
- Exact image count: images with exactly the correct number of detections.
- Negative-image accuracy, including the no-WBC subject F.

The evaluator should also produce a per-image diagnostic artifact listing
matches, distances, type errors, false positives, and false negatives. That
artifact remains trusted evaluation output and is not exposed to the
candidate during execution.

Version 1.0 uses a 30-pixel localization tolerance in the original 1056 by
816 image. The source answer rings have a radius of approximately 25 pixels,
so this represents the original click-at-the-cell interaction without making
the location threshold a broad fraction of the image.

## Implemented Benchmark Decisions

- All 14 images A through N are evaluated in every trial.
- The source answer overlays yielded 50 trusted center points, validated
  against every per-image metadata count.
- Image F is a mandatory negative example.
- The supplied tutorial, compact morphology guide, field-guide payload,
  printable guide, five type-specific guide images, and non-WBC guide are
  candidate-visible.
- Answer overlays, source counts and URLs, and typed reference points remain
  under `reference/`.
- The output is a JSON list of typed normalized points, not browser clicks.
- Browser navigation, the live random queue, Talk, and Zooniverse submission
  behavior are outside the benchmark.
- The evaluator reports the class imbalance and zero basophil support through
  per-class reference and prediction counts.
