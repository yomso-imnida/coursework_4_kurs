#!/usr/bin/env python3
"""Compare schedulers for different graphs, CR values and heuristics."""

import argparse
import csv
import itertools
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

ALGORITHMS = [
    "misf", "eft", "est", "edfbase",
    "edfb_misf", "edffollow", "edff_misf",
]

COLUMNS = [
    "graph", "processors", "cr", "delay", "heuristic",
    "random", "status", "schedule_time", "error",
]


def row_key(row):
    return tuple(row[field] for field in COLUMNS[:6])


def read_results(path):
    if not path.is_file():
        return {}

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != COLUMNS:
            raise ValueError(f"Unexpected CSV columns in {path}")
        return {row_key(row): row for row in reader}


def save_results(path, results):
    temporary = path.with_suffix(".tmp")

    with temporary.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=COLUMNS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(results.values())

    temporary.replace(path)


def run_case(args, graph, processors, cr, delay, algo):
    cr_text = f"{cr:g}"

    case_dir = (
        args.output_dir / "runs" / graph / f"p{processors}"
        / f"cr_{cr_text}" / f"delay_{delay}" / algo
    )
    case_dir.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        str(ROOT / "scripts/compare_schedules.py"),
        "--graph-dir", "graphs_triang",
        "--graph", graph,
        "--processors", str(processors),
        "--cr", cr_text,
        "--delay", str(delay),
        "--algo", algo,
        "--random", str(args.random),
        "--output-dir", str(case_dir),
    ]

    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    log_file = case_dir / "comparison.log"
    log_file.write_text(
        completed.stdout + completed.stderr,
        encoding="utf-8",
    )

    row = {
        "graph": graph,
        "processors": str(processors),
        "cr": cr_text,
        "delay": str(delay),
        "heuristic": algo,
        "random": str(args.random),
        "status": "FAIL",
        "schedule_time": "",
        "error": "",
    }

    if completed.returncode:
        row["error"] = (
            f"Exit code {completed.returncode}; see {log_file}"
        )
        return row

    try:
        path = case_dir / graph / "normalized_new.json"
        schedule = json.loads(path.read_text(encoding="utf-8"))
        value = schedule["time"]

        if isinstance(value, bool) or not isinstance(
            value, (int, float)
        ):
            raise ValueError("Invalid schedule time")

        row["schedule_time"] = str(value)
        row["status"] = "PASS"

    except (OSError, ValueError, KeyError) as exc:
        row["error"] = f"{exc}; see {log_file}"

    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        "--graphs",
        nargs="+",
        default=[
            "triadag10_0",
            "triadag20_0",
            "triadag30_0",
        ],
    )
    parser.add_argument(
        "--processors",
        nargs="+",
        type=int,
        default=[4, 8, 16],
    )
    parser.add_argument(
        "--crs",
        nargs="+",
        type=float,
        default=[0.2, 0.4, 0.6, 0.8],
    )
    parser.add_argument(
        "--delays",
        nargs="+",
        type=int,
        default=[2, 7],
    )
    parser.add_argument(
        "--algos",
        nargs="+",
        default=ALGORITHMS,
    )
    parser.add_argument(
        "--random",
        type=int,
        default=1234,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp/coursework_cr_experiments"),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Repeat successful experiments too",
    )

    args = parser.parse_args()
    args.output_dir = args.output_dir.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    for graph in args.graphs:
        graph_path = ROOT / "graphs_triang" / f"{graph}.txt"
        if Path(graph).name != graph or not graph_path.is_file():
            parser.error(f"Graph not found in graphs_triang: {graph}")

    if any(p <= 0 for p in args.processors):
        parser.error("Processor counts must be positive")

    if any(not 0 <= cr <= 1 for cr in args.crs):
        parser.error("CR values must be between 0 and 1")

    if any(delay < 0 for delay in args.delays):
        parser.error("Delays must be non-negative")

    if any(algo not in ALGORITHMS for algo in args.algos):
        parser.error(
            f"Supported heuristics: {', '.join(ALGORITHMS)}"
        )

    csv_path = args.output_dir / "results.csv"

    try:
        results = read_results(csv_path)
    except ValueError as exc:
        parser.error(str(exc))

    cases = list(itertools.product(
        args.graphs,
        args.processors,
        args.crs,
        args.delays,
        args.algos,
    ))

    skipped = 0
    print(f"Experiments selected: {len(cases)}", flush=True)

    for index, (graph, processors, cr, delay, algo) in enumerate(
        cases, 1
    ):
        row_id = (
            graph,
            str(processors),
            f"{cr:g}",
            str(delay),
            algo,
            str(args.random),
        )

        if (
            not args.force
            and row_id in results
            and results[row_id]["status"] == "PASS"
        ):
            skipped += 1
            print(
                f"[{index}/{len(cases)}] SKIP: {graph}, "
                f"P={processors}, CR={cr:g}, "
                f"delay={delay}, {algo}",
                flush=True,
            )
            continue

        row = run_case(args, graph, processors, cr, delay, algo)

        results[row_id] = row
        save_results(csv_path, results)

        print(
            f"[{index}/{len(cases)}] {row['status']}: "
            f"{graph}, P={processors}, CR={cr:g}, "
            f"delay={delay}, {algo}, "
            f"time={row['schedule_time'] or '-'}",
            flush=True,
        )

    passed = sum(
        results[
            (g, str(p), f"{c:g}", str(d), a, str(args.random))
        ]["status"] == "PASS"
        for g, p, c, d, a in cases
    )

    print(
        f"Finished: {passed}/{len(cases)} PASS; "
        f"skipped: {skipped}"
    )
    print(f"CSV: {csv_path}")

    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
