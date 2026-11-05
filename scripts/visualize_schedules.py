#!/usr/bin/env python3
"""Visualize two schedules as stacked Gantt charts."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch

COLORS = (
    "#bfd8f2", "#d5eacb", "#f8d5be", "#ead0e8",
    "#f6e9af", "#c9e7e4", "#f1cbd3", "#cbd4ef",
    "#e3dac3", "#c9e1bd", "#e3c9b3", "#d9d4f3",
)


def draw_schedule(ax, schedule, title, palette, limit):
    procs = schedule["procs"]
    proc_ids = sorted(procs, key=lambda key: int(key))
    end = float(schedule["time"])

    for row, proc_id in enumerate(proc_ids):
        # Заштрихованный фон обозначает простои.
        ax.barh(
            row, end, left=0, height=0.76,
            color="#f7f8fa", edgecolor="#d3d9e1",
            hatch="///", linewidth=0.4, zorder=1,
        )

        tasks = sorted(
            procs[proc_id] or [],
            key=lambda task: task["start"],
        )

        for task in tasks:
            start = float(task["start"])
            duration = float(task["duration"])

            if (start < 0 or duration <= 0
                    or start + duration > end + 1e-6):
                raise ValueError(f"Invalid task: {task}")

            ax.barh(
                row, duration, left=start, height=0.76,
                color=palette[str(task["id"])],
                edgecolor="#798a9b", linewidth=0.7,
                zorder=2,
            )

            if duration >= max(15, limit * 0.065):
                ax.text(
                    start + duration / 2, row,
                    str(task["id"]),
                    ha="center", va="center",
                    fontsize=9, color="#23334b",
                    zorder=3,
                )

    ax.set_title(
        f"{title} — время {schedule['time']}",
        loc="left", fontsize=12, fontweight="bold",
        pad=12,
    )
    ax.set_yticks(range(len(proc_ids)))
    ax.set_yticklabels([f"P{p}" for p in proc_ids])
    ax.set_ylim(-0.65, len(proc_ids) - 0.35)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.18)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(axis="y", length=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--new", type=Path, required=True)
    parser.add_argument("--old", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    new = json.loads(args.new.read_text(encoding="utf-8"))
    old = json.loads(args.old.read_text(encoding="utf-8"))

    ids = sorted({
        str(task["id"])
        for data in (new, old)
        for tasks in data["procs"].values()
        for task in tasks or []
    })

    palette = {
        task_id: COLORS[i % len(COLORS)]
        for i, task_id in enumerate(ids)
    }

    limit = max(float(new["time"]), float(old["time"]))
    rows = max(len(new["procs"]), len(old["procs"]))

    fig, axes = plt.subplots(
        2, 1,
        figsize=(13, max(6, 0.85 * rows * 2 + 2)),
        sharex=True,
    )

    draw_schedule(
        axes[0], new, "Новая программа (RS2)",
        palette, limit,
    )
    draw_schedule(
        axes[1], old, "Старая программа (.in)",
        palette, limit,
    )

    axes[1].set_xlim(0, limit * 1.01 if limit else 1)
    axes[1].set_xlabel("Время")

    fig.legend(
        handles=[
            Patch(
                facecolor="#bfd8f2",
                edgecolor="#798a9b",
                label="Работа",
            ),
            Patch(
                facecolor="#f7f8fa",
                edgecolor="#d3d9e1",
                hatch="///",
                label="Простой",
            ),
        ],
        loc="lower center", ncol=2, frameon=False,
    )
    fig.subplots_adjust(bottom=0.13, hspace=0.36)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=180, facecolor="white")
    plt.close(fig)

    print(f"OK: {args.output}")


if __name__ == "__main__":
    main()
