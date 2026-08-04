from __future__ import annotations

import base64
import html
from pathlib import Path
from typing import Any


def _text(value: object) -> str:
    return html.escape(str(value))


def _accuracy(value: float | None) -> str:
    return "not available" if value is None else f"{value:.1%}"


def _image_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def _document(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_text(title)}</title>
  <style>
    :root {{
      --ink:#17231d; --muted:#5b655f; --paper:#f2eee2; --panel:#fffdf7;
      --line:#c9c0aa; --tp:#16765c; --fp:#bd3f32; --fn:#c78318;
      --accent:#174d62;
    }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; color:var(--ink); background:
      radial-gradient(circle at 88% 4%,#d8e2cf 0,transparent 28rem),
      linear-gradient(115deg,transparent 72%,#e3dac4 72% 73%,transparent 73%),
      var(--paper); font:16px/1.45 Georgia,serif; }}
    main {{ max-width:1240px; margin:auto; padding:46px 24px 80px; }}
    h1 {{ margin:0; font-size:clamp(2.6rem,7vw,5.4rem); line-height:.9;
      letter-spacing:-.045em; }}
    h2 {{ margin-top:42px; }}
    .lede {{ max-width:820px; color:var(--muted); font-size:1.1rem; }}
    .facts {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
      gap:12px; margin:24px 0; }}
    .fact,section,.image-card {{ background:var(--panel);
      border:1px solid var(--line); }}
    .fact {{ padding:16px 18px; }}
    .fact span {{ display:block; color:var(--muted); text-transform:uppercase;
      font:12px/1.2 "Courier New",monospace; letter-spacing:.08em; }}
    .fact strong {{ display:block; margin-top:7px; font-size:1.55rem; }}
    table {{ width:100%; border-collapse:collapse; background:var(--panel);
      margin:16px 0 28px; }}
    th,td {{ padding:9px 11px; border:1px solid var(--line); text-align:right; }}
    th {{ background:#e9eee8; }}
    th:first-child {{ text-align:left; }}
    caption {{ text-align:left; font-weight:bold; margin-bottom:8px; }}
    .legend {{ display:flex; flex-wrap:wrap; gap:16px; margin:18px 0; }}
    .legend span {{ display:inline-flex; align-items:center; gap:7px; }}
    .swatch {{ --marker-color:var(--ink); position:relative; width:17px;
      height:17px; border:2px solid var(--marker-color); border-radius:50%;
      display:inline-block; color:var(--marker-color); background:transparent; }}
    .swatch::before,.swatch::after {{ content:""; position:absolute; left:50%;
      top:50%; width:7px; height:2px; background:currentColor;
      transform:translate(-50%,-50%) rotate(45deg); }}
    .swatch::after {{ transform:translate(-50%,-50%) rotate(-45deg); }}
    .swatch.tp {{ --marker-color:var(--tp); }}
    .swatch.fp {{ --marker-color:var(--fp); }}
    .swatch.fn {{ --marker-color:var(--fn); }}
    .image-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(330px,1fr));
      gap:18px; }}
    .image-card {{ padding:12px; }}
    .image-card header {{ display:flex; justify-content:space-between; gap:12px;
      align-items:baseline; margin-bottom:9px; }}
    .image-card h3 {{ margin:0; font-size:1.3rem; }}
    .image-card small {{ color:var(--muted); }}
    .image-frame {{ position:relative; line-height:0; background:#ddd; overflow:hidden; }}
    .image-frame img {{ width:100%; height:auto; display:block; }}
    .marker {{ --marker-color:var(--ink); position:absolute; width:26px;
      height:26px; transform:translate(-50%,-50%); border-radius:50%;
      border:3px solid var(--marker-color); color:var(--marker-color);
      background:transparent;
      filter:drop-shadow(0 0 1px rgba(255,255,255,.95))
        drop-shadow(0 1px 2px rgba(0,0,0,.75)); }}
    .marker::before,.marker::after {{ content:""; position:absolute; left:50%;
      top:50%; width:10px; height:2px; background:currentColor;
      box-shadow:0 0 1px rgba(255,255,255,.95);
      transform:translate(-50%,-50%) rotate(45deg); }}
    .marker::after {{ transform:translate(-50%,-50%) rotate(-45deg); }}
    .marker.tp {{ --marker-color:var(--tp); }}
    .marker.fp {{ --marker-color:var(--fp); }}
    .marker.fn {{ --marker-color:var(--fn); }}
    .bars {{ display:grid; gap:15px; margin:18px 0 30px; }}
    .bar-row {{ display:grid; grid-template-columns:110px 1fr; gap:14px; align-items:start; }}
    .bar-label {{ font-weight:bold; padding-top:3px; }}
    .bar-stack {{ display:grid; gap:5px; }}
    .bar {{ min-width:2.1rem; width:max(2.1rem,var(--width)); color:white;
      padding:3px 8px; font:12px/1.3 "Courier New",monospace; }}
    .bar.tp {{ background:var(--tp); }}
    .bar.fp {{ background:var(--fp); }}
    .bar.fn {{ background:var(--fn); color:#2b210f; }}
    .note {{ color:var(--muted); font-size:.93rem; }}
    .matrix td.diagonal {{ background:#dceadf; font-weight:bold; }}
    .matrix td.error {{ background:#f2d8d1; }}
    .matrix td.zero {{ color:#89918c; }}
    .error-list {{ display:grid; gap:8px; padding:0; list-style:none; }}
    .error-list li {{ border-left:5px solid var(--fp); background:var(--panel);
      padding:10px 12px; }}
    @media (max-width:650px) {{
      main {{ padding:32px 13px 60px; }}
      .image-grid {{ grid-template-columns:1fr; }}
      .bar-row {{ grid-template-columns:1fr; gap:4px; }}
      table {{ font-size:.82rem; }}
      th,td {{ padding:6px; }}
    }}
  </style>
</head>
<body><main>{body}</main></body>
</html>
"""


def _marker(marker: dict[str, Any], kind: str) -> str:
    if kind == "tp":
        title = (
            f"True positive: expected {marker['expected_type']}, "
            f"assigned {marker['assigned_type']}"
        )
    elif kind == "fp":
        title = f"False positive: assigned {marker['assigned_type']}"
    else:
        title = f"False negative: missed {marker['expected_type']}"
    return (
        f'<span class="marker {kind}" '
        f'style="left:{float(marker["x"]) * 100:.4f}%;'
        f'top:{float(marker["y"]) * 100:.4f}%" '
        f'title="{_text(title)}" aria-label="{_text(title)}" '
        'role="img"></span>'
    )


def _type_bars(per_cell_type: dict[str, dict[str, int]]) -> str:
    maximum = max(
        (
            count
            for counts in per_cell_type.values()
            for count in counts.values()
        ),
        default=1,
    )
    rows = []
    for cell_type, counts in per_cell_type.items():
        bars = []
        for key, label, css_class in (
            ("true_positives", "TP", "tp"),
            ("false_positives", "FP", "fp"),
            ("false_negatives", "FN", "fn"),
        ):
            count = counts[key]
            width = count / maximum * 100 if maximum else 0
            bars.append(
                f'<div class="bar {css_class}" style="--width:{width:.2f}%">'
                f"{label} {count}</div>"
            )
        rows.append(
            '<div class="bar-row">'
            f'<div class="bar-label">{_text(cell_type)}</div>'
            f'<div class="bar-stack">{"".join(bars)}</div>'
            "</div>"
        )
    return "".join(rows)


def render_detection_report(
    summary: dict[str, Any],
    metrics: dict[str, Any],
    diagnostics: dict[str, Any],
    image_paths: dict[str, Path],
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
    image_cards = []
    for image in diagnostics["images"]:
        image_id = image["image_id"]
        counts = image["localization"]
        markers = image["markers"]
        overlays = "".join(
            [
                *(
                    _marker(marker, "tp")
                    for marker in markers["true_positives"]
                ),
                *(
                    _marker(marker, "fp")
                    for marker in markers["false_positives"]
                ),
                *(
                    _marker(marker, "fn")
                    for marker in markers["false_negatives"]
                ),
            ]
        )
        image_cards.append(
            '<article class="image-card">'
            "<header>"
            f"<h3>Image {_text(image_id)}</h3>"
            f"<small>TP {counts['true_positives']} · "
            f"FP {counts['false_positives']} · "
            f"FN {counts['false_negatives']}</small>"
            "</header>"
            '<div class="image-frame">'
            f'<img src="{_image_data_uri(image_paths[image_id])}" '
            f'alt="Monkey blood-smear image {image_id}">'
            f"{overlays}</div></article>"
        )

    body = f"""
<h1>White blood cell detection</h1>
<p class="lede">Localization is scored independently of cell identification.
Markers show the locations used by the deterministic matcher.</p>
<div class="facts">
  <div class="fact"><span>Reference cells</span><strong>{summary['reference_count']}</strong></div>
  <div class="fact"><span>Predicted cells</span><strong>{summary['prediction_count']}</strong></div>
  <div class="fact"><span>True positives</span><strong>{total['true_positives']}</strong></div>
  <div class="fact"><span>False positives</span><strong>{total['false_positives']}</strong></div>
  <div class="fact"><span>False negatives</span><strong>{total['false_negatives']}</strong></div>
</div>
<h2>Outcomes by cell type</h2>
<p class="note">TP and FN are grouped by the known reference type. A false
positive has no ground-truth type, so FP is grouped by the type assigned by
the agent.</p>
<div class="bars">{_type_bars(localization['per_cell_type'])}</div>
<table>
  <caption>Localization counts by image</caption>
  <thead><tr><th>Image</th><th>TP</th><th>FP</th><th>FN</th></tr></thead>
  <tbody>{per_image_rows}</tbody>
  <tfoot><tr><th>Total</th><td>{total['true_positives']}</td>
    <td>{total['false_positives']}</td><td>{total['false_negatives']}</td></tr></tfoot>
</table>
<h2>Spatial results</h2>
<div class="legend">
  <span><i class="swatch tp"></i>True positive</span>
  <span><i class="swatch fp"></i>False positive</span>
  <span><i class="swatch fn"></i>False negative</span>
</div>
<div class="image-grid">{''.join(image_cards)}</div>
<p class="note">Matches use a {_text(summary['matching_tolerance_px'])}-pixel
tolerance in the original image. Hover over a marker for type information.</p>
"""
    return _document("White blood cell detection", body)


def render_identification_report(
    summary: dict[str, Any],
    metrics: dict[str, Any],
) -> str:
    typing = metrics["typing"]
    matrix = typing["confusion_matrix"]
    labels = matrix["labels"]
    matrix_header = "".join(f"<th>{_text(label)}</th>" for label in labels)
    matrix_rows = []
    errors = []
    for correct_type in labels:
        cells = []
        for assigned_type in labels:
            count = matrix["counts"][correct_type][assigned_type]
            css_class = (
                "zero"
                if count == 0
                else "diagonal"
                if correct_type == assigned_type
                else "error"
            )
            cells.append(f'<td class="{css_class}">{count}</td>')
            if count and correct_type != assigned_type:
                errors.append(
                    f"{count} {_text(correct_type)} "
                    f"{'was' if count == 1 else 'were'} assigned "
                    f"{_text(assigned_type)}"
                )
        matrix_rows.append(
            "<tr>"
            f"<th>{_text(correct_type)}</th>"
            f"{''.join(cells)}"
            f"<td>{matrix['correct_type_totals'][correct_type]}</td>"
            "</tr>"
        )
    assigned_totals = "".join(
        f"<td>{matrix['assigned_type_totals'][assigned_type]}</td>"
        for assigned_type in labels
    )
    error_items = (
        "".join(f"<li>{item}</li>" for item in errors)
        if errors
        else "<li>No off-diagonal type errors.</li>"
    )
    body = f"""
<h1>White blood cell identification</h1>
<p class="lede">Identification is evaluated only for predictions that were
successfully matched to a reference cell. {typing['evaluated_cells']} of
{summary['reference_count']} reference cells enter this report.</p>
<div class="facts">
  <div class="fact"><span>Typing accuracy</span><strong>{_accuracy(typing['accuracy'])}</strong></div>
  <div class="fact"><span>Correctly identified</span><strong>{typing['correct']}</strong></div>
  <div class="fact"><span>Incorrectly identified</span><strong>{typing['incorrect']}</strong></div>
  <div class="fact"><span>Localized cells evaluated</span><strong>{typing['evaluated_cells']}</strong></div>
</div>
<h2>Confusion matrix</h2>
<table class="matrix">
  <caption>Rows are correct types; columns are assigned types</caption>
  <thead><tr><th>Correct \\ assigned</th>{matrix_header}<th>Correct-type total</th></tr></thead>
  <tbody>{''.join(matrix_rows)}</tbody>
  <tfoot><tr><th>Assigned-type total</th>{assigned_totals}<td>{matrix['total']}</td></tr></tfoot>
</table>
<h2>Identification errors</h2>
<ul class="error-list">{error_items}</ul>
<p class="note">{typing['correct']} of {typing['evaluated_cells']} localized
cells were identified correctly. Detection misses and false positives are
reported separately in the detection report.</p>
"""
    return _document("White blood cell identification", body)
