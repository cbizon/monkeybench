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
    :root {{ --ink:#17231d; --paper:#f2eee2; --panel:#fffdf7;
      --line:#c9c0aa; --accent:#a9442c; --green:#176653; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; color:var(--ink); background:
      radial-gradient(circle at 88% 3%,#d8e2cf 0,transparent 28rem),
      var(--paper); font:16px/1.5 Georgia,serif; }}
    main {{ max-width:1140px; margin:auto; padding:48px 24px 80px; }}
    h1 {{ margin:0 0 24px; font-size:clamp(2.8rem,7vw,5.8rem);
      line-height:.9; letter-spacing:-.045em; }}
    h2 {{ margin-top:42px; }}
    section {{ background:var(--panel); border:1px solid var(--line);
      padding:18px; margin-top:18px; }}
    .verdict {{ border-left:7px solid var(--green); font-size:1.16rem; }}
    .rating {{ display:inline-block; margin:0 0 8px; color:var(--accent);
      text-transform:uppercase; font:bold 13px/1.2 "Courier New",monospace;
      letter-spacing:.08em; }}
    .columns {{ display:grid; grid-template-columns:1fr 1fr; gap:18px; }}
    table {{ width:100%; border-collapse:collapse; }}
    th, td {{ border:1px solid var(--line); padding:9px 11px; text-align:left; }}
    th {{ background:#e9eee8; }}
    @media (max-width:700px) {{
      main {{ padding:32px 14px 60px; }}
      .columns {{ grid-template-columns:1fr; }}
      table {{ font-size:.86rem; }}
    }}
  </style>
</head>
<body><main>
  <h1>Overall qualitative review</h1>
  <section class="verdict">
    <strong>Bottom line</strong>
    <p>{_text(overall['bottom_line'])}</p>
  </section>

  <section>
    <h2>Transcript review</h2>
    <p><strong>Approach:</strong> {_text(transcript['approach'])}</p>
    <p>{_text(transcript['summary'])}</p>
    <h3>Training materials reviewed</h3>
    <p>{_text(transcript['training_material_use'])}</p>
    <h3>Image inspection and identification strategy</h3>
    <p><strong>Image inspection:</strong> {_text(transcript['image_inspection_strategy'])}</p>
    <p><strong>Cell identification:</strong> {_text(transcript['typing_strategy'])}</p>
    <h3>Notable actions</h3>
    {_list(transcript['notable_actions'])}
    <h3>Difficulties and adaptations</h3>
    {_list(transcript['failures_or_retries'])}
    <h3>Evidence</h3>
    {_evidence(transcript['evidence'])}
  </section>

  <div class="columns">
    <section>
      <h2>Detection performance</h2>
      <p class="rating">{_text(localization['performance'])}</p>
      <p>{_text(localization['summary'])}</p>
      <p><strong>Error distribution:</strong> {_text(localization['error_distribution'])}</p>
      <h3>Evidence</h3>
      {_evidence(localization['evidence'])}
    </section>

    <section>
      <h2>Identification performance</h2>
      <p class="rating">{_text(typing['performance'])}</p>
      <p>{_text(typing['summary'])}</p>
      <p><strong>Confusion pattern:</strong> {_text(typing['confusion_summary'])}</p>
      <p><strong>Marginals:</strong> {_text(typing['marginal_summary'])}</p>
      <h3>Evidence</h3>
      {_evidence(typing['evidence'])}
    </section>
  </div>

  <h2>Identification errors</h2>
  <table>
    <thead><tr><th>Correct type</th><th>Assigned type</th><th>Count</th><th>Interpretation</th></tr></thead>
    <tbody>{confusion_rows}</tbody>
  </table>

  <section>
    <h2>Strengths, weaknesses, and limitations</h2>
    <h3>Strengths</h3>
    {_list(overall['strengths'])}
    <h3>Weaknesses</h3>
    {_list(overall['weaknesses'])}
    <h3>Review limitations</h3>
    {_list(review['review_limitations'])}
  </section>
</main></body>
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
