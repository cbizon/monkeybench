# Monkeybench qualitative review rubric

Rubric version: `1.0`

## Purpose

This review complements the deterministic localization and typing evaluator.
It describes how the agent approached the task and provides a concise,
evidence-grounded interpretation of the resulting detection counts and typing
confusion matrix. It does not replace or recalculate deterministic results.

## Evidence order

Use evidence in this order:

1. Deterministic evaluation results and diagnostics.
2. Provider transcript, commands, and tool output.
3. Submitted artifacts and run status.
4. Prompt and subject manifest.
5. Timing and usage records.

Candidate claims do not override generated artifacts or evaluator results.
Every major characterization must cite a supplied evidence path and finding.
When the evidence is insufficient, say so directly.

## Transcript characterization

Describe observable behavior rather than reconstructing private reasoning.
Identify:

- whether the agent primarily used direct visual inspection, tool-assisted
  inspection, automated image analysis, or a hybrid approach;
- which training materials it consulted;
- how it selected white blood cell centers;
- how it assigned cell types;
- whether it generated crops, measurements, scripts, or other intermediate
  aids;
- important retries, failures, corrections, or abandoned approaches;
- how it checked and finalized the submission.

Do not treat provider API duration as private thinking time.

## Localization characterization

Use the deterministic per-image and total `true_positives`,
`false_positives`, and `false_negatives`.

- `perfect`: no false positives or false negatives.
- `strong`: few errors and no broad or systematic localization failure.
- `mixed`: meaningful correct localization with substantial or concentrated
  misses or spurious detections.
- `weak`: errors dominate or most images show serious localization problems.
- `failed`: no meaningful successful localization.
- `unavailable`: deterministic localization results are absent or invalid.

Describe whether errors are isolated or concentrated in particular images.
Do not fold typing errors into localization performance.

## Typing characterization

Typing is evaluated only for spatially matched cells. Use the deterministic
typing accuracy and confusion matrix.

- `perfect`: every localized cell has the correct type.
- `strong`: typing is predominantly correct with limited confusion.
- `mixed`: several classes are recognized, but important confusion patterns
  remain.
- `weak`: incorrect assignments are common or predictions collapse toward one
  class.
- `failed`: no evaluated cell is typed correctly.
- `unavailable`: there are no localized cells or no valid typing results.

Rows in the confusion matrix are correct/reference types. Columns are assigned
types. Report important off-diagonal cells and interpret row and column
marginals without treating absent reference classes as measured recognition
performance.

## Overall synthesis

State a short bottom line that keeps localization and typing separate. List
specific strengths and weaknesses. Do not calculate a combined score or
override the deterministic metrics.
