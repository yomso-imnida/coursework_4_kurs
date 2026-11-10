#!/usr/bin/env python3
"""Compare both schedulers using different heuristics and delays."""

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAPHS = ROOT / "coursework_kret/algo/tests/format_compare_graphs"
FORMAT1 = ROOT / "coursework_kret/algo/tests/format_compare/format1"
COMPARE = ROOT / "scripts/compare_schedules.py"

ALGORITHMS = [
    "misf", "eft", "est", "edfbase",
    "edfb_misf", "edffollow", "edff_misf",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", help="One graph, e.g. triang_small/triang_4")
    parser.add_argument("--algos", nargs="+", default=ALGORITHMS)
    parser.add_argument("--delays", nargs="+", type=int, default=[2, 7])
    parser.add_argument("--random", type=int, default=1234)
    parser.add_argument("--processors", type=int)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp/coursework_heuristics_all"),
    )
    args = parser.parse_args()

    for algo in args.algos:
        if algo not in ALGORITHMS:
            parser.error(f"Unknown algorithm: {algo}")
    for delay in args.delays:
        if not 0 <= delay <= 2**31 - 1:
            parser.error(f"Invalid delay: {delay}")

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    if args.graph:
        graphs = [GRAPHS / f"{args.graph}.txt"]
    else:
        graphs = sorted(GRAPHS.glob("*/*.txt"))

    if not graphs:
        parser.error("No graphs found")

    csv_path = output / "results.csv"
    passed = 0
    failed = 0

    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "graph", "processors", "heuristic",
                "delay", "random", "status", "schedule_time",
            ],
            lineterminator="\n",
        )
        writer.writeheader()

        for graph in graphs:
            if not graph.is_file():
                parser.error(f"Graph not found: {graph}")

            name = graph.relative_to(GRAPHS).with_suffix("").as_posix()
            old_input = FORMAT1 / f"{name}.in"

            try:
                header = old_input.read_text(
                    encoding="utf-8"
                ).splitlines()[0]
                processors = int(header.split()[1])
            except (OSError, ValueError, IndexError) as exc:
                parser.error(f"Cannot read processor count for {name}: {exc}")

            if args.processors is not None:
                if args.processors < 1:
                    parser.error("--processors must be positive")
                processors = args.processors

            for delay in args.delays:
                for algo in args.algos:
                    run_dir = output / algo / f"delay_{delay}"
                    result = subprocess.run(
                        [
                            sys.executable, str(COMPARE),
                            "--graph", name,
                            "--processors", str(processors),
                            "--delay", str(delay),
                            "--algo", algo,
                            "--random", str(args.random),
                            "--output-dir", str(run_dir),
                        ],
                        cwd=ROOT,
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    schedule_time = ""
                    status = "PASS" if result.returncode == 0 else "FAIL"

                    if result.returncode == 0:
                        result_file = (
                            run_dir / name / "normalized_new.json"
                        )
                        schedule = json.loads(
                            result_file.read_text(encoding="utf-8")
                        )
                        schedule_time = schedule["time"]
                        passed += 1
                    else:
                        failed += 1
                        print(
                            result.stdout + result.stderr,
                            file=sys.stderr,
                        )

                    writer.writerow({
                        "graph": name,
                        "processors": processors,
                        "heuristic": algo,
                        "delay": delay,
                        "random": args.random,
                        "status": status,
                        "schedule_time": schedule_time,
                    })
                    file.flush()
                    print(
                        f"{status}: {name} | P={processors} "
                        f"| {algo} | delay={delay} "
                        f"| time={schedule_time}",
                        flush=True,
                    )

    print(f"\nPassed: {passed} | Failed: {failed}")
    print(f"CSV: {csv_path}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
