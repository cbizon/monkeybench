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
    .spatial-toolbar {{ position:sticky; top:0; z-index:10; display:flex;
      flex-wrap:wrap; justify-content:space-between; align-items:center; gap:14px;
      margin:18px 0; padding:10px 12px; background:rgba(255,253,247,.96);
      border:1px solid var(--line); box-shadow:0 3px 10px rgba(23,35,29,.12); }}
    .legend {{ display:flex; flex-wrap:wrap; gap:16px; }}
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
    .viewer-controls {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px; }}
    .viewer-button {{ border:1px solid var(--accent); background:var(--panel);
      color:var(--accent); padding:8px 12px; cursor:pointer;
      font:bold 13px/1.2 "Courier New",monospace; }}
    .viewer-button:hover:not(:disabled) {{ background:#e4eceb; }}
    .viewer-button:disabled {{ cursor:not-allowed; opacity:.45; }}
    .viewer-button:focus-visible {{ outline:3px solid #87a8b7;
      outline-offset:2px; }}
    .marker-toggle {{ background:var(--accent); color:white; }}
    .marker-toggle:hover {{ background:#0f3e50; }}
    .image-counter {{ min-width:7.6rem; text-align:center;
      font:bold 13px/1.2 "Courier New",monospace; }}
    .image-viewer {{ width:100%; }}
    .image-card {{ padding:16px; }}
    .image-card[hidden] {{ display:none; }}
    .image-card header {{ display:flex; justify-content:space-between; gap:12px;
      align-items:baseline; margin-bottom:9px; }}
    .image-card h3 {{ margin:0; font-size:1.3rem; }}
    .image-card small {{ color:var(--muted); }}
    .image-frame {{ position:relative; line-height:0; background:#ddd; overflow:hidden; }}
    .image-frame img {{ width:100%; height:auto; display:block; }}
    .marker-layer {{ position:absolute; inset:0; }}
    .marker {{ --marker-color:var(--ink); position:absolute; width:28px;
      height:28px; transform:translate(-50%,-50%); border-radius:50%;
      border:2px solid var(--marker-color); color:var(--marker-color);
      background:transparent; }}
    .marker::before,.marker::after {{ content:""; position:absolute; left:50%;
      top:50%; width:11px; height:2px; background:currentColor;
      transform:translate(-50%,-50%) rotate(45deg); }}
    .marker::after {{ transform:translate(-50%,-50%) rotate(-45deg); }}
    .marker.tp {{ --marker-color:var(--tp); }}
    .marker.fp {{ --marker-color:var(--fp); }}
    .marker.fn {{ --marker-color:var(--fn); }}
    .note {{ color:var(--muted); font-size:.93rem; }}
    .matrix td.diagonal {{ background:#dceadf; font-weight:bold; }}
    .matrix td.error {{ background:#f2d8d1; }}
    .matrix td.zero {{ color:#89918c; }}
    .error-list {{ display:grid; gap:8px; padding:0; list-style:none; }}
    .error-list li {{ border-left:5px solid var(--fp); background:var(--panel);
      padding:10px 12px; }}
    @media (max-width:650px) {{
      main {{ padding:32px 13px 60px; }}
      .spatial-toolbar {{ align-items:flex-start; flex-direction:column; }}
      .viewer-controls {{ width:100%; }}
      .image-counter {{ flex:1; }}
      .image-card {{ padding:8px; }}
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
    per_cell_type_rows = "".join(
        "<tr>"
        f"<th>{_text(cell_type)}</th>"
        f"<td>{counts['true_positives']}</td>"
        f"<td>{counts['false_negatives']}</td>"
        "</tr>"
        for cell_type, counts in localization["per_cell_type"].items()
    )
    image_cards = []
    for image_index, image in enumerate(diagnostics["images"]):
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
            '<article class="image-card" data-image-card'
            f'{" hidden" if image_index else ""}>'
            "<header>"
            f"<h3>Image {_text(image_id)}</h3>"
            f"<small>TP {counts['true_positives']} · "
            f"FP {counts['false_positives']} · "
            f"FN {counts['false_negatives']}</small>"
            "</header>"
            '<div class="image-frame">'
            f'<img src="{_image_data_uri(image_paths[image_id])}" '
            f'alt="Monkey blood-smear image {image_id}">'
            f'<div class="marker-layer">{overlays}</div>'
            "</div></article>"
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
<p class="note">TP and FN are grouped by the known reference type. False
positives have no ground-truth cell type and are reported in the overall and
per-image counts instead.</p>
<table>
  <caption>Localization counts by cell type</caption>
  <thead><tr><th>Cell type</th><th>TP</th><th>FN</th></tr></thead>
  <tbody>{per_cell_type_rows}</tbody>
  <tfoot><tr><th>Total</th><td>{total['true_positives']}</td>
    <td>{total['false_negatives']}</td></tr></tfoot>
</table>
<table>
  <caption>Localization counts by image</caption>
  <thead><tr><th>Image</th><th>TP</th><th>FP</th><th>FN</th></tr></thead>
  <tbody>{per_image_rows}</tbody>
  <tfoot><tr><th>Total</th><td>{total['true_positives']}</td>
    <td>{total['false_positives']}</td><td>{total['false_negatives']}</td></tr></tfoot>
</table>
<h2>Spatial results</h2>
<div class="spatial-toolbar">
  <div class="legend">
    <span><i class="swatch tp"></i>True positive</span>
    <span><i class="swatch fp"></i>False positive</span>
    <span><i class="swatch fn"></i>False negative</span>
  </div>
  <div class="viewer-controls">
    <button class="viewer-button" type="button" data-image-prev disabled>Back</button>
    <output class="image-counter" data-image-counter>Image 1 of {len(image_cards)}</output>
    <button class="viewer-button" type="button" data-image-next>Next</button>
    <button class="viewer-button marker-toggle" type="button"
      data-marker-toggle aria-pressed="true">Hide markers</button>
  </div>
</div>
<div class="image-viewer">{''.join(image_cards)}</div>
<p class="note">Matches use a {_text(summary['matching_tolerance_px'])}-pixel
tolerance in the original image. Hover over a marker for type information.</p>
<script>
  (() => {{
    const markerButton = document.querySelector("[data-marker-toggle]");
    const layers = document.querySelectorAll(".marker-layer");
    if (markerButton && layers.length) {{
      markerButton.addEventListener("click", () => {{
        const visible =
          markerButton.getAttribute("aria-pressed") === "true";
        layers.forEach((layer) => {{ layer.hidden = visible; }});
        markerButton.setAttribute("aria-pressed", String(!visible));
        markerButton.textContent =
          visible ? "Show markers" : "Hide markers";
      }});
    }}

    const cards = [...document.querySelectorAll("[data-image-card]")];
    const previousButton = document.querySelector("[data-image-prev]");
    const nextButton = document.querySelector("[data-image-next]");
    const counter = document.querySelector("[data-image-counter]");
    if (!cards.length || !previousButton || !nextButton || !counter) return;

    let activeIndex = 0;
    const showImage = (index) => {{
      activeIndex = Math.max(0, Math.min(index, cards.length - 1));
      cards.forEach((card, cardIndex) => {{
        card.hidden = cardIndex !== activeIndex;
      }});
      previousButton.disabled = activeIndex === 0;
      nextButton.disabled = activeIndex === cards.length - 1;
      counter.textContent = `Image ${{activeIndex + 1}} of ${{cards.length}}`;
    }};
    previousButton.addEventListener(
      "click",
      () => {{ showImage(activeIndex - 1); }},
    );
    nextButton.addEventListener(
      "click",
      () => {{ showImage(activeIndex + 1); }},
    );
    showImage(0);
  }})();
</script>
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
    per_cell_type_rows = "".join(
        "<tr>"
        f"<th>{_text(cell_type)}</th>"
        f"<td>{counts['correct']}</td>"
        f"<td>{counts['incorrect']}</td>"
        f"<td>{counts['evaluated_cells']}</td>"
        f"<td>{_accuracy(counts['accuracy'])}</td>"
        "</tr>"
        for cell_type, counts in typing["per_cell_type"].items()
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
<h2>Accuracy by cell type</h2>
<table>
  <caption>Typing accuracy among spatially matched cells</caption>
  <thead><tr><th>Correct type</th><th>Correct</th><th>Incorrect</th>
    <th>Evaluated</th><th>Accuracy</th></tr></thead>
  <tbody>{per_cell_type_rows}</tbody>
  <tfoot><tr><th>Overall</th><td>{typing['correct']}</td>
    <td>{typing['incorrect']}</td><td>{typing['evaluated_cells']}</td>
    <td>{_accuracy(typing['accuracy'])}</td></tr></tfoot>
</table>
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
