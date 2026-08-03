from __future__ import annotations

import html
from typing import Any


def _text(value: object) -> str:
    return html.escape(str(value))


def _accuracy(value: float | None) -> str:
    return "not available" if value is None else f"{value:.1%}"


def render_evaluation_report(
    summary: dict[str, Any],
    metrics: dict[str, Any],
) -> str:
    localization = metrics["localization"]
    total = localization["total"]
    per_image_rows = "".join(
        "<tr>"
        f"<th>{_text(image_id)}</th>"
        f"<td>{counts['true_positives']}</td>"
        f"<td>{counts['false_positives']}</td>"
        f"<td>{counts['false_negatives']}</td>"
        "</tr>"
        for image_id, counts in localization["per_image"].items()
    )

    typing = metrics["typing"]
    matrix = typing["confusion_matrix"]
    labels = matrix["labels"]
    matrix_header = "".join(f"<th>{_text(label)}</th>" for label in labels)
    matrix_rows = "".join(
        "<tr>"
        f"<th>{_text(correct_type)}</th>"
        + "".join(
            f"<td>{matrix['counts'][correct_type][assigned_type]}</td>"
            for assigned_type in labels
        )
        + f"<td>{matrix['correct_type_totals'][correct_type]}</td>"
        "</tr>"
        for correct_type in labels
    )
    assigned_totals = "".join(
        f"<td>{matrix['assigned_type_totals'][assigned_type]}</td>"
        for assigned_type in labels
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Monkeybench detection and typing evaluation</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; color: #17212b; }}
    h1, h2 {{ margin-bottom: 0.4rem; }}
    .facts {{ display: flex; gap: 1rem; flex-wrap: wrap; margin: 1rem 0; }}
    .fact {{ border: 1px solid #bcc7d1; border-radius: 0.4rem; padding: 0.8rem 1rem; }}
    .fact strong {{ display: block; font-size: 1.4rem; }}
    table {{ border-collapse: collapse; margin: 1rem 0 2rem; }}
    th, td {{ border: 1px solid #bcc7d1; padding: 0.45rem 0.7rem; text-align: right; }}
    th {{ background: #edf2f5; }}
    th:first-child {{ text-align: left; }}
    caption {{ text-align: left; font-weight: bold; margin-bottom: 0.5rem; }}
  </style>
</head>
<body>
  <h1>Monkeybench detection and typing evaluation</h1>
  <p>Spatial detection and cell typing are evaluated independently.</p>

  <h2>White blood cell localization</h2>
  <div class="facts">
    <div class="fact">True positives<strong>{total['true_positives']}</strong></div>
    <div class="fact">False positives<strong>{total['false_positives']}</strong></div>
    <div class="fact">False negatives<strong>{total['false_negatives']}</strong></div>
  </div>
  <table>
    <caption>Localization counts by image</caption>
    <thead><tr><th>Image</th><th>TP</th><th>FP</th><th>FN</th></tr></thead>
    <tbody>{per_image_rows}</tbody>
    <tfoot>
      <tr><th>Total</th><td>{total['true_positives']}</td><td>{total['false_positives']}</td><td>{total['false_negatives']}</td></tr>
    </tfoot>
  </table>

  <h2>Cell typing</h2>
  <div class="facts">
    <div class="fact">Typing accuracy<strong>{_accuracy(typing['accuracy'])}</strong></div>
    <div class="fact">Correctly typed<strong>{typing['correct']}</strong></div>
    <div class="fact">Incorrectly typed<strong>{typing['incorrect']}</strong></div>
    <div class="fact">Localized cells evaluated<strong>{typing['evaluated_cells']}</strong></div>
  </div>
  <table>
    <caption>Confusion matrix: rows are correct types; columns are assigned types</caption>
    <thead>
      <tr><th>Correct \\ assigned</th>{matrix_header}<th>Correct-type total</th></tr>
    </thead>
    <tbody>{matrix_rows}</tbody>
    <tfoot>
      <tr><th>Assigned-type total</th>{assigned_totals}<td>{matrix['total']}</td></tr>
    </tfoot>
  </table>

  <p>Matches use a {_text(summary['matching_tolerance_px'])}-pixel tolerance in the original image.</p>
</body>
</html>
"""
