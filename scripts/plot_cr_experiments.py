#!/usr/bin/env python3
"""Plot schedule durations relative to MISF for each CR value."""

import argparse
import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

ROOT = Path(__file__).resolve().parent.parent

PROCESSORS = (4, 8, 16)
DELAYS = (2, 7)
CR_VALUES = (0.2, 0.4, 0.6, 0.8)

HEURISTICS = (
    "misf", "eft", "est", "edfbase",
    "edfb_misf", "edffollow", "edff_misf",
)

HEURISTIC_LABELS = {
    "misf": "MISF",
    "eft": "EFT",
    "est": "EST",
    "edfbase": "EDFBase",
    "edfb_misf": "EDFBase+MISF",
    "edffollow": "EDFFollow",
    "edff_misf": "EDFFollow+MISF",
}

COLORS = (
    "#e8a3b2",  # misf
    "#a7c7e7",  # eft
    "#b9d7b1",  # est
    "#d2b9e8",  # edfbase
    "#f2ce9f",  # edfb_misf
    "#98d5d2",  # edffollow
    "#d4b8a8",  # edff_misf
)


def read_results(path):
    results = {}

    with path.open("r", encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            if row["status"] != "PASS":
                raise ValueError(f"Non-PASS result: {row}")

            key = (
                row["graph"],
                int(row["processors"]),
                float(row["cr"]),
                int(row["delay"]),
                row["heuristic"],
            )

            if key in results:
                raise ValueError(f"Duplicate result: {key}")

            value = float(row["schedule_time"])
            if value <= 0:
                raise ValueError(f"Non-positive schedule duration: {key}")

            results[key] = value

    return results


def plot_one(results, graph, processors, delay, output_dir):
    ratios = {}

    for cr in CR_VALUES:
        baseline_key = (graph, processors, cr, delay, "misf")

        if baseline_key not in results:
            raise ValueError(f"Missing MISF baseline: {baseline_key}")

        baseline = results[baseline_key]

        for heuristic in HEURISTICS:
            key = (graph, processors, cr, delay, heuristic)

            if key not in results:
                raise ValueError(f"Missing result: {key}")

            ratios[(cr, heuristic)] = results[key] / baseline

    fig, ax = plt.subplots(figsize=(13, 6.4))
    fig.patch.set_facecolor("#fffaf8")
    ax.set_facecolor("#fffaf8")

    width = 0.105

    for j, (heuristic, color) in enumerate(zip(HEURISTICS, COLORS)):
        xs = [
            i + (j - 3) * width
            for i in range(len(CR_VALUES))
        ]
        ys = [
            ratios[(cr, heuristic)]
            for cr in CR_VALUES
        ]

        ax.bar(
            xs,
            ys,
            width=width,
            color=color,
            edgecolor="#655d60",
            linewidth=0.5,
            label=HEURISTIC_LABELS[heuristic],
            zorder=3,
        )

    ax.axhline(
        1.0,
        color="#746a74",
        linestyle="--",
        linewidth=1.2,
        alpha=0.8,
        zorder=4,
    )

    ax.set_xticks(list(range(len(CR_VALUES))))
    ax.set_xticklabels(
        [f"{cr:.1f}" for cr in CR_VALUES],
        fontsize=11,
    )
    ax.set_xlabel("CR_bound", fontsize=11, labelpad=10)
    ax.set_ylabel(
        "Длительность / MISF (меньше — лучше)",
        fontsize=11,
    )
    ax.set_title(
        f"{graph}.txt, {processors} "
        f"{'процессора' if processors == 4 else 'процессоров'}, "
        f"задержка межпроцессорной передачи = {delay}",
        fontsize=15,
        fontweight="bold",
        pad=19,
    )

    max_ratio = max(
        value / results[(g, p, cr, d, "misf")]
        for (g, p, cr, d, _), value in results.items()
    )
    upper_limit = max(1.1, math.ceil(max_ratio * 10) / 10)
    ax.set_ylim(0, upper_limit)
    ax.yaxis.set_major_locator(MultipleLocator(0.1))
    ax.yaxis.grid(
        True,
        color="#e6dedf",
        linewidth=0.7,
        zorder=0,
    )

    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#cbbfc3")

    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.17),
        ncol=7,
        frameon=False,
        fontsize=9,
        columnspacing=1.25,
    )

    fig.subplots_adjust(
        left=0.09,
        right=0.98,
        top=0.86,
        bottom=0.25,
    )

    output = (
        output_dir
        / f"{graph}_p{processors}_delay{delay}.png"
    )

    fig.savefig(
        output,
        dpi=220,
        facecolor=fig.get_facecolor(),
    )
    plt.close(fig)

    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "results/cr_experiments.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results/cr_charts",
    )
    parser.add_argument("--graph")
    parser.add_argument(
        "--processors",
        type=int,
        choices=PROCESSORS,
    )
    parser.add_argument(
        "--delay",
        type=int,
        choices=DELAYS,
    )

    args = parser.parse_args()

    results = read_results(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    graphs = sorted({key[0] for key in results})

    if args.graph is not None:
        if args.graph not in graphs:
            parser.error(f"Graph not found in CSV: {args.graph}")
        graphs = [args.graph]

    processors = (
        [args.processors]
        if args.processors
        else PROCESSORS
    )
    delays = [args.delay] if args.delay else DELAYS

    for graph in graphs:
        for p in processors:
            for delay in delays:
                path = plot_one(
                    results,
                    graph,
                    p,
                    delay,
                    args.output_dir,
                )
                print(f"Saved: {path}")


if __name__ == "__main__":
    main()
