#!/usr/bin/env python3
"""Compare schedules on all prepared test graphs."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAPHS = ROOT / "coursework_kret/algo/tests/format_compare_graphs"
FORMAT1 = ROOT / "coursework_kret/algo/tests/format_compare/format1"
COMPARE = ROOT / "scripts/compare_schedules.py"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--delay", type=int, default=2)
    parser.add_argument("--algo", default="misf")
    parser.add_argument("--random", type=int, default=1234)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp/coursework_compare_all"),
    )
    args = parser.parse_args()

    if not 0 <= args.delay <= 2**31 - 1:
        parser.error("--delay must be between 0 and 2147483647")

    graphs = sorted(GRAPHS.glob("*/*.txt"))
    if not graphs:
        parser.error("No test graphs found")

    passed = 0
    failed = 0

    for graph in graphs:
        name = graph.relative_to(GRAPHS).with_suffix("").as_posix()
        old_input = FORMAT1 / f"{name}.in"

        try:
            header = old_input.read_text(encoding="utf-8").splitlines()[0]
            processors = int(header.split()[1])
            if processors < 1:
                raise ValueError("Invalid processor count")
        except (OSError, IndexError, ValueError) as exc:
            print(f"FAIL: {name} — {exc}", flush=True)
            failed += 1
            continue

        result = subprocess.run(
            [
                sys.executable,
                str(COMPARE),
                "--graph", name,
                "--processors", str(processors),
                "--delay", str(args.delay),
                "--algo", args.algo,
                "--random", str(args.random),
                "--output-dir", str(args.output_dir),
            ],
            cwd=ROOT,
            check=False,
        )

        if result.returncode == 0:
            passed += 1
        else:
            failed += 1

    print(f"\nPassed: {passed} | Failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
