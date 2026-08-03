# Monkey white blood cell localization and typing

Identify every visible white blood cell in each image listed in
`inputs/subjects.json`.

These images are blood smears from monkeys and contain many red blood cells and other items, but your only goal is to locate and classify the white blood cells.
The materials in `training/` should be consulted to guide you in how to recognize and classify cells.

For every white blood cell in each image, report:

- its approximate center as normalized `x` and `y` coordinates;
- its type: `neutrophil`, `lymphocyte`, `monocyte`, `eosinophil`, or
  `basophil`.

The coordinate origin is the top-left corner. `x` increases left-to-right and
`y` increases top-to-bottom. Both coordinates must be in `[0, 1]` relative to
the complete original image. Report each physical cell at most once.

Do not use network tools.  Do not mark red blood cells, platelets, burst cells, cell fakes, or debris.  Every assigned image must appear in the result, including any images where no white blood cells are detected.

{{BRUNNER_OUTPUT_CONTRACT}}
