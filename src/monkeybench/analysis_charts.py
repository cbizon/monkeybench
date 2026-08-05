from __future__ import annotations

import argparse
import csv
import html
import math
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


CELL_TYPE_ORDER = (
    "neutrophil",
    "lymphocyte",
    "monocyte",
    "eosinophil",
    "basophil",
)
PROVIDER_COLORS = {
    "codex": "#176b87",
    "claude": "#c65d32",
}
TP_COLOR = "#19705b"
FP_COLOR = "#b84336"
FN_COLOR = "#d09528"
NA_COLOR = "#d7d9d8"
LOW_EFFORT_COLOR = "#d09528"
XHIGH_EFFORT_COLOR = "#176b87"
OBSOLETE_CHART_NAMES = (
    "detection-vs-identification",
    "runtime-vs-tokens",
)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def _float(value: str | int | float | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _run_labels(runs: list[dict[str, str]]) -> dict[str, str]:
    bases = {
        run["run_id"]: f"{run['model']} / {run['effort']}"
        for run in runs
    }
    duplicate_bases = {
        label
        for label in bases.values()
        if list(bases.values()).count(label) > 1
    }
    return {
        run["run_id"]: (
            f"{bases[run['run_id']]} [{run['campaign_id']}]"
            if bases[run["run_id"]] in duplicate_bases
            else bases[run["run_id"]]
        )
        for run in runs
    }


def _sort_runs(runs: list[dict[str, str]]) -> list[dict[str, str]]:
    effort_order = {"low": 0, "medium": 1, "high": 2, "xhigh": 3}
    return sorted(
        runs,
        key=lambda run: (
            run["provider"],
            run["model"],
            effort_order.get(run["effort"], 99),
            run["campaign_id"],
            run["test_id"],
        ),
    )


def _sort_detection_runs(
    runs: list[dict[str, str]],
) -> list[dict[str, str]]:
    return sorted(
        runs,
        key=lambda run: (
            -float(run["true_positives"]),
            float(run["false_positives"]),
            float(run["false_negatives"]),
            run["provider"],
            run["model"],
            run["effort"],
            run["test_id"],
        ),
    )


def _sort_typing_runs(
    runs: list[dict[str, str]],
) -> list[dict[str, str]]:
    return sorted(
        runs,
        key=lambda run: (
            -float(run["typing_accuracy"]),
            -float(run["typing_correct"]),
            run["provider"],
            run["model"],
            run["effort"],
            run["test_id"],
        ),
    )


def _save_figure(fig: plt.Figure, output_dir: Path, name: str) -> None:
    fig.savefig(output_dir / f"{name}.png", dpi=180, bbox_inches="tight")
    fig.savefig(output_dir / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def _chart_detection_counts(
    runs: list[dict[str, str]],
    output_dir: Path,
) -> None:
    runs = _sort_detection_runs(runs)
    run_labels = _run_labels(runs)
    labels = [run_labels[run["run_id"]] for run in runs]
    positions = np.arange(len(runs))
    height = 0.24
    fig, ax = plt.subplots(figsize=(10, max(4.5, len(runs) * 0.55)))
    ax.barh(
        positions - height,
        [float(run["true_positives"]) for run in runs],
        height,
        color=TP_COLOR,
        label="True positives",
    )
    ax.barh(
        positions,
        [float(run["false_positives"]) for run in runs],
        height,
        color=FP_COLOR,
        label="False positives",
    )
    ax.barh(
        positions + height,
        [float(run["false_negatives"]) for run in runs],
        height,
        color=FN_COLOR,
        label="False negatives",
    )
    ax.set_yticks(positions, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Cell count")
    ax.set_title("White blood cell detection, ranked by true positives")
    ax.legend(
        frameon=False,
        ncols=3,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.08),
    )
    ax.grid(axis="x", alpha=0.2)
    _save_figure(fig, output_dir, "detection-counts")


def _chart_typing_accuracy(
    runs: list[dict[str, str]],
    output_dir: Path,
) -> None:
    runs = _sort_typing_runs(runs)
    run_labels = _run_labels(runs)
    labels = [run_labels[run["run_id"]] for run in runs]
    positions = np.arange(len(runs))
    values = [100 * float(run["typing_accuracy"]) for run in runs]
    colors = [
        PROVIDER_COLORS.get(run["provider"], "#52616b")
        for run in runs
    ]
    fig, ax = plt.subplots(figsize=(10, max(4.5, len(runs) * 0.48)))
    bars = ax.barh(positions, values, color=colors)
    ax.bar_label(bars, fmt="%.1f%%", padding=4)
    ax.set_yticks(positions, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 105)
    ax.set_xlabel("Accuracy among matched cells")
    ax.set_title("Cell identification accuracy, ranked by accuracy")
    ax.grid(axis="x", alpha=0.2)
    _save_figure(fig, output_dir, "typing-accuracy")


def _chart_performance_by_resource(
    runs: list[dict[str, str]],
    output_dir: Path,
    *,
    performance_field: str,
    performance_label: str,
    resource_field: str,
    resource_label: str,
    title: str,
    name: str,
    resource_scale: float = 1.0,
    log_resource: bool = False,
) -> None:
    chart_runs = [
        run
        for run in runs
        if _float(run.get(performance_field)) is not None
        and (_float(run.get(resource_field)) or 0) > 0
    ]
    run_labels = _run_labels(chart_runs)
    fig, ax = plt.subplots(figsize=(12, 7))
    for index, run in enumerate(chart_runs, start=1):
        resource = float(run[resource_field]) / resource_scale
        performance = 100 * float(run[performance_field])
        color = PROVIDER_COLORS.get(run["provider"], "#52616b")
        ax.scatter(
            resource,
            performance,
            s=95,
            color=color,
            alpha=0.9,
            label=f"{index}. {run_labels[run['run_id']]}",
        )
        ax.text(
            resource,
            performance,
            str(index),
            ha="center",
            va="center",
            color="white",
            fontsize=7,
            fontweight="bold",
        )
    ax.set_ylim(0, 103)
    if log_resource and chart_runs:
        ax.set_xscale("log")
    ax.set_xlabel(resource_label)
    ax.set_ylabel(performance_label)
    ax.set_title(title)
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0f}%")
    ax.grid(alpha=0.2)
    if chart_runs:
        ax.legend(
            frameon=False,
            bbox_to_anchor=(1.02, 1),
            loc="upper left",
            fontsize=8,
        )
    _save_figure(fig, output_dir, name)


def _paired_effort_values(
    runs: list[dict[str, str]],
    metric_field: str,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, dict[str, str]]] = {}
    for run in runs:
        if run["effort"] not in {"low", "xhigh"}:
            continue
        key = (run["campaign_id"], run["provider"], run["model"])
        grouped.setdefault(key, {})[run["effort"]] = run

    pairs = []
    for (campaign_id, provider, model), efforts in grouped.items():
        if "low" not in efforts or "xhigh" not in efforts:
            continue
        low = _float(efforts["low"].get(metric_field))
        xhigh = _float(efforts["xhigh"].get(metric_field))
        if low is None or xhigh is None:
            continue
        pairs.append(
            {
                "campaign_id": campaign_id,
                "provider": provider,
                "model": model,
                "low": low,
                "xhigh": xhigh,
                "gap": abs(xhigh - low),
                "change": xhigh - low,
            }
        )
    pairs.sort(
        key=lambda pair: (
            -pair["gap"],
            pair["provider"],
            pair["model"],
            pair["campaign_id"],
        )
    )
    return pairs


def _chart_effort_gap(
    runs: list[dict[str, str]],
    output_dir: Path,
    *,
    metric_field: str,
    metric_label: str,
    title: str,
    name: str,
) -> None:
    pairs = _paired_effort_values(runs, metric_field)
    fig, ax = plt.subplots(figsize=(max(8, len(pairs) * 1.6), 7))
    if not pairs:
        ax.text(
            0.5,
            0.5,
            "No models have both low and xhigh runs.",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
        ax.set_axis_off()
        ax.set_title(title)
        _save_figure(fig, output_dir, name)
        return

    model_counts: dict[str, int] = {}
    for pair in pairs:
        model_counts[pair["model"]] = model_counts.get(pair["model"], 0) + 1
    labels = [
        (
            f"{pair['model']}\n[{pair['campaign_id']}]"
            if model_counts[pair["model"]] > 1
            else pair["model"]
        )
        for pair in pairs
    ]
    positions = np.arange(len(pairs))
    low_values = np.array([100 * pair["low"] for pair in pairs])
    xhigh_values = np.array([100 * pair["xhigh"] for pair in pairs])
    ax.vlines(
        positions,
        np.minimum(low_values, xhigh_values),
        np.maximum(low_values, xhigh_values),
        color="#7a8582",
        linewidth=4,
        alpha=0.7,
        zorder=1,
    )
    ax.scatter(
        positions,
        low_values,
        color=LOW_EFFORT_COLOR,
        edgecolor="white",
        linewidth=1,
        s=110,
        label="Low effort",
        zorder=2,
    )
    ax.scatter(
        positions,
        xhigh_values,
        color=XHIGH_EFFORT_COLOR,
        edgecolor="white",
        linewidth=1,
        s=110,
        label="xhigh effort",
        zorder=2,
    )
    for position, pair, low_value, xhigh_value in zip(
        positions,
        pairs,
        low_values,
        xhigh_values,
        strict=True,
    ):
        ax.annotate(
            f"{pair['change'] * 100:+.1f} pp",
            (position, max(low_value, xhigh_value)),
            xytext=(0, 9),
            textcoords="offset points",
            ha="center",
            fontsize=8,
        )
    ax.set_xticks(positions, labels)
    ax.tick_params(axis="x", rotation=25)
    ax.set_ylim(0, 108)
    ax.set_xlabel("Model, ordered by absolute effort gap")
    ax.set_ylabel(metric_label)
    ax.set_title(title)
    ax.yaxis.set_major_formatter(lambda value, _: f"{value:.0f}%")
    ax.grid(axis="y", alpha=0.2)
    ax.legend(frameon=False, ncols=2, loc="lower right")
    _save_figure(fig, output_dir, name)


def _cell_types_in_order(cell_rows: list[dict[str, str]]) -> list[str]:
    observed = {row["cell_type"] for row in cell_rows}
    ordered = [cell_type for cell_type in CELL_TYPE_ORDER if cell_type in observed]
    return ordered + sorted(observed - set(ordered))


def _heatmap(
    runs: list[dict[str, str]],
    cell_rows: list[dict[str, str]],
    value_field: str,
    title: str,
    output_dir: Path,
    name: str,
) -> None:
    cell_types = _cell_types_in_order(cell_rows)
    run_labels = _run_labels(runs)
    by_key = {
        (row["run_id"], row["cell_type"]): _float(row[value_field])
        for row in cell_rows
    }
    values = np.array(
        [
            [
                (
                    np.nan
                    if by_key.get((run["run_id"], cell_type)) is None
                    else 100 * float(by_key[(run["run_id"], cell_type)])
                )
                for cell_type in cell_types
            ]
            for run in runs
        ],
        dtype=float,
    )
    cmap = matplotlib.colormaps["YlGn"].with_extremes(bad=NA_COLOR)
    fig, ax = plt.subplots(
        figsize=(max(7, len(cell_types) * 1.4), max(4.5, len(runs) * 0.55))
    )
    image = ax.imshow(values, cmap=cmap, vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(np.arange(len(cell_types)), cell_types)
    ax.set_yticks(
        np.arange(len(runs)),
        [run_labels[run["run_id"]] for run in runs],
    )
    ax.tick_params(axis="x", rotation=30)
    ax.set_title(title)
    for row_index in range(values.shape[0]):
        for column_index in range(values.shape[1]):
            value = values[row_index, column_index]
            label = "NA" if math.isnan(value) else f"{value:.0f}%"
            text_color = "white" if not math.isnan(value) and value >= 65 else "#1c2826"
            ax.text(
                column_index,
                row_index,
                label,
                ha="center",
                va="center",
                color=text_color,
                fontsize=8,
            )
    colorbar = fig.colorbar(image, ax=ax, fraction=0.025, pad=0.03)
    colorbar.set_label("Rate")
    _save_figure(fig, output_dir, name)


def _write_index(
    output_dir: Path,
    runs: list[dict[str, str]],
    chart_names: Sequence[tuple[str, str, str]],
) -> None:
    campaigns = sorted({run["campaign_id"] for run in runs})
    cards = "\n".join(
        f"""
        <section>
          <h2>{html.escape(title)}</h2>
          <p>{html.escape(description)}</p>
          <a href="{name}.svg"><img src="{name}.svg" alt="{html.escape(title)}"></a>
        </section>
        """
        for name, title, description in chart_names
    )
    campaign_text = ", ".join(html.escape(campaign) for campaign in campaigns)
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Monkeybench campaign analysis</title>
  <style>
    :root {{
      color: #14211f;
      background: #f4f0e8;
      font-family: "Avenir Next", "Trebuchet MS", sans-serif;
    }}
    body {{ margin: 0 auto; max-width: 1280px; padding: 2rem; }}
    header {{ border-bottom: 3px solid #19705b; margin-bottom: 2rem; }}
    h1, h2 {{ font-family: Georgia, serif; }}
    .meta {{ color: #53615e; }}
    section {{
      background: #fffdf8;
      border: 1px solid #d8d1c3;
      box-shadow: 0 5px 20px rgb(44 50 42 / 8%);
      margin: 1.5rem 0;
      padding: 1.25rem;
    }}
    img {{ display: block; width: 100%; height: auto; }}
    code {{ background: #e7e1d6; padding: 0.1rem 0.25rem; }}
  </style>
</head>
<body>
  <header>
    <h1>Monkeybench campaign analysis</h1>
    <p class="meta">{len(runs)} collected runs from {campaign_text}</p>
    <p>
      Agent-active time is Brunner's closest inference-time proxy. It also
      includes provider latency and orchestration, so it is not pure model
      compute time.
    </p>
  </header>
  {cards}
</body>
</html>
"""
    (output_dir / "index.html").write_text(document, encoding="utf-8")


def generate_charts(input_dir: Path, output_dir: Path) -> None:
    runs = _sort_runs(_read_csv(input_dir / "runs.csv"))
    cell_rows = _read_csv(input_dir / "cell_types.csv")
    if not runs:
        raise ValueError(f"No rows found in {input_dir / 'runs.csv'}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in OBSOLETE_CHART_NAMES:
        for suffix in (".png", ".svg"):
            (output_dir / f"{name}{suffix}").unlink(missing_ok=True)

    _chart_detection_counts(runs, output_dir)
    _chart_typing_accuracy(runs, output_dir)
    _chart_performance_by_resource(
        runs,
        output_dir,
        performance_field="detection_f1",
        performance_label="Detection F1",
        resource_field="total_tokens",
        resource_label="Total tokens (log scale)",
        title="Detection performance versus tokens",
        name="detection-vs-tokens",
        log_resource=True,
    )
    _chart_performance_by_resource(
        runs,
        output_dir,
        performance_field="detection_f1",
        performance_label="Detection F1",
        resource_field="inference_time_proxy_seconds",
        resource_label="Agent-active time (minutes)",
        title="Detection performance versus time",
        name="detection-vs-time",
        resource_scale=60,
    )
    _chart_performance_by_resource(
        runs,
        output_dir,
        performance_field="typing_accuracy",
        performance_label="Identification accuracy among matched cells",
        resource_field="total_tokens",
        resource_label="Total tokens (log scale)",
        title="Identification accuracy versus tokens",
        name="identification-vs-tokens",
        log_resource=True,
    )
    _chart_performance_by_resource(
        runs,
        output_dir,
        performance_field="typing_accuracy",
        performance_label="Identification accuracy among matched cells",
        resource_field="inference_time_proxy_seconds",
        resource_label="Agent-active time (minutes)",
        title="Identification accuracy versus time",
        name="identification-vs-time",
        resource_scale=60,
    )
    _chart_effort_gap(
        runs,
        output_dir,
        metric_field="detection_f1",
        metric_label="Detection F1",
        title="Low versus xhigh detection performance",
        name="detection-effort-gap",
    )
    _chart_effort_gap(
        runs,
        output_dir,
        metric_field="typing_accuracy",
        metric_label="Identification accuracy among matched cells",
        title="Low versus xhigh identification accuracy",
        name="identification-effort-gap",
    )
    _heatmap(
        runs,
        cell_rows,
        "localization_recall",
        "Detection recall by true cell type",
        output_dir,
        "localization-recall-by-type",
    )
    _heatmap(
        runs,
        cell_rows,
        "typing_accuracy",
        "Identification accuracy by true cell type",
        output_dir,
        "typing-accuracy-by-type",
    )
    chart_names = (
        (
            "detection-counts",
            "Detection counts",
            "True positives, false positives, and false negatives per run.",
        ),
        (
            "typing-accuracy",
            "Identification accuracy",
            "Correct cell type among correctly localized cells.",
        ),
        (
            "detection-vs-tokens",
            "Detection versus tokens",
            "Detection F1 against total logical input plus output tokens.",
        ),
        (
            "detection-vs-time",
            "Detection versus time",
            "Detection F1 against Brunner agent-active time.",
        ),
        (
            "identification-vs-tokens",
            "Identification versus tokens",
            "Identification accuracy against total logical input plus output tokens.",
        ),
        (
            "identification-vs-time",
            "Identification versus time",
            "Identification accuracy against Brunner agent-active time.",
        ),
        (
            "detection-effort-gap",
            "Detection by effort",
            "Low and xhigh detection F1 joined for each model, ordered by gap.",
        ),
        (
            "identification-effort-gap",
            "Identification by effort",
            "Low and xhigh identification accuracy joined for each model, ordered by gap.",
        ),
        (
            "localization-recall-by-type",
            "Detection recall by type",
            "Detection recall grouped by the known type of each reference cell.",
        ),
        (
            "typing-accuracy-by-type",
            "Identification accuracy by type",
            "Per-type accuracy for matched cells; NA means no evaluated cells.",
        ),
    )
    _write_index(output_dir, runs, chart_names)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate charts from normalized Monkeybench campaign metrics."
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        type=Path,
        default=Path("analysis-output"),
        help="Directory containing runs.csv and cell_types.csv.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Chart output directory; defaults to INPUT_DIR/charts.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output_dir = args.output_dir or args.input_dir / "charts"
    generate_charts(args.input_dir, output_dir)
    print(f"Wrote charts to {output_dir.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
