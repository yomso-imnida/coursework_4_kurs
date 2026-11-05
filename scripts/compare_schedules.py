#!/usr/bin/env python3
"""Run both schedulers on the same graph and compare schedules."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "coursework_kret/algo/tests/format_compare"
GRAPHS = ROOT / "coursework_kret/algo/tests/format_compare_graphs"

sys.path.insert(0, str(TOOLS))
from test_schedules import normalized  # noqa: E402


def run(command, log_path):
    result = subprocess.run(
        [str(arg) for arg in command],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    log_path.write_text(
        result.stdout + result.stderr,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed (exit {result.returncode}). "
            f"See {log_path}"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", required=True)
    parser.add_argument("--processors", type=int, required=True)
    parser.add_argument("--delay", type=int, default=2)
    parser.add_argument("--algo", default="misf")
    parser.add_argument("--random", type=int, default=1234)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/tmp/coursework_compare"),
    )
    args = parser.parse_args()

    graph = (GRAPHS / f"{args.graph}.txt").resolve()
    if not graph.is_relative_to(GRAPHS) or not graph.is_file():
        parser.error(f"Graph not found: {graph}")

    output = (args.output_dir / args.graph).resolve()
    output.mkdir(parents=True, exist_ok=True)

    matrix = output / "matrix.txt"
    old_input = output / "graph.in"
    old_json = output / "old.json"
    new_json = output / "new.json"

    old_exe = ROOT / "coursework_kret/algo/build/sched"
    new_exe = ROOT / "my_coursework/algo/build/sched"

    for executable in (old_exe, new_exe):
        if not executable.is_file():
            parser.error(f"Executable not found: {executable}")

    try:
        run([
            sys.executable, ROOT / "scripts/generate_delay_matrix.py",
            "--processors", args.processors,
            "--delay", args.delay,
            "--output", matrix,
        ], output / "generate.log")

        run([
            sys.executable, TOOLS / "convert_to_format1.py",
            "--input", graph,
            "--matrix", matrix,
            "--output", old_input,
        ], output / "convert.log")

        run([
            old_exe,
            "--input", old_input,
            "--output", old_json,
            "--conf", ROOT / "coursework_kret/algo/config.toml",
            "--command", args.algo,
            "--random", args.random,
        ], output / "old.log")

        run([
            new_exe,
            "--graph", graph,
            "--matrix", matrix,
            "--output", new_json,
            "--conf", ROOT / "my_coursework/algo/config.toml",
            "--command", args.algo,
            "--random", args.random,
        ], output / "new.log")

        ids_file = old_input.with_suffix(".ids.json")
        ids = json.loads(
            ids_file.read_text(encoding="utf-8")
        )["original_ids"]

        old = normalized(old_json, ids, True)
        new = normalized(new_json, ids, False)

        for name, schedule in (("old", old), ("new", new)):
            (output / f"normalized_{name}.json").write_text(
                json.dumps(schedule, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        if old != new:
            print(f"FAIL: schedules differ. Results: {output}")
            return 1

        print(f"PASS: {args.graph}")
        print(f"Processors: {args.processors}, delay: {args.delay}")
        print(f"Schedule time: {old['time']}")
        print(f"Results: {output}")
        return 0

    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
