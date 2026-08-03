from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any


def _text(value: object) -> str:
    return html.escape(str(value))


def _list(items: list[str]) -> str:
    if not items:
        return "<p>None reported.</p>"
    return "<ul>" + "".join(f"<li>{_text(item)}</li>" for item in items) + "</ul>"


def _evidence(items: list[dict[str, Any]]) -> str:
    return _list(
        [
            f"{item['path']}: {item['finding']}"
            for item in items
        ]
    )


def render(review: dict[str, Any]) -> str:
    transcript = review["transcript_characterization"]
    localization = review["localization_characterization"]
    typing = review["typing_characterization"]
    overall = review["overall"]
    confusion_rows = "".join(
        "<tr>"
        f"<td>{_text(item['correct_type'])}</td>"
        f"<td>{_text(item['assigned_type'])}</td>"
        f"<td>{item['count']}</td>"
        f"<td>{_text(item['interpretation'])}</td>"
        "</tr>"
        for item in typing["notable_confusions"]
    )
    if not confusion_rows:
        confusion_rows = (
            '<tr><td colspan="4">No notable off-diagonal confusion.</td></tr>'
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Monkeybench qualitative review</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; color: #17212b; max-width: 72rem; }}
    section {{ border-top: 1px solid #bcc7d1; padding-top: 1rem; margin-top: 1.5rem; }}
    .rating {{ text-transform: uppercase; font-weight: bold; letter-spacing: 0.05em; }}
    table {{ border-collapse: collapse; }}
    th, td {{ border: 1px solid #bcc7d1; padding: 0.45rem 0.7rem; text-align: left; }}
    th {{ background: #edf2f5; }}
  </style>
</head>
<body>
  <h1>Monkeybench qualitative review</h1>
  <p>{_text(overall['bottom_line'])}</p>

  <section>
    <h2>Transcript characterization</h2>
    <p><strong>Approach:</strong> {_text(transcript['approach'])}</p>
    <p>{_text(transcript['summary'])}</p>
    <p><strong>Training material:</strong> {_text(transcript['training_material_use'])}</p>
    <p><strong>Image inspection:</strong> {_text(transcript['image_inspection_strategy'])}</p>
    <p><strong>Typing strategy:</strong> {_text(transcript['typing_strategy'])}</p>
    <h3>Notable actions</h3>
    {_list(transcript['notable_actions'])}
    <h3>Failures or retries</h3>
    {_list(transcript['failures_or_retries'])}
    <h3>Evidence</h3>
    {_evidence(transcript['evidence'])}
  </section>

  <section>
    <h2>Localization performance</h2>
    <p class="rating">{_text(localization['performance'])}</p>
    <p>{_text(localization['summary'])}</p>
    <p><strong>Error distribution:</strong> {_text(localization['error_distribution'])}</p>
    <h3>Evidence</h3>
    {_evidence(localization['evidence'])}
  </section>

  <section>
    <h2>Typing performance</h2>
    <p class="rating">{_text(typing['performance'])}</p>
    <p>{_text(typing['summary'])}</p>
    <p><strong>Confusion pattern:</strong> {_text(typing['confusion_summary'])}</p>
    <p><strong>Marginals:</strong> {_text(typing['marginal_summary'])}</p>
    <table>
      <thead><tr><th>Correct type</th><th>Assigned type</th><th>Count</th><th>Interpretation</th></tr></thead>
      <tbody>{confusion_rows}</tbody>
    </table>
    <h3>Evidence</h3>
    {_evidence(typing['evidence'])}
  </section>

  <section>
    <h2>Overall</h2>
    <h3>Strengths</h3>
    {_list(overall['strengths'])}
    <h3>Weaknesses</h3>
    {_list(overall['weaknesses'])}
    <h3>Review limitations</h3>
    {_list(review['review_limitations'])}
  </section>
</body>
</html>
"""


def main() -> int:
    output = Path(os.environ["BRUNNER_ASSESSMENT_OUTPUT"]).resolve()
    trial = Path(os.environ["BRUNNER_TRIAL_ROOT"]).resolve()
    report = trial / "evaluation/qualitative-review.html"
    review = json.loads(output.read_text())
    report.write_text(render(review))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
