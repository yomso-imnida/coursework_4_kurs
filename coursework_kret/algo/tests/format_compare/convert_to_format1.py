#!/usr/bin/env python3
"""Independent conversion: RS2 graphs -> legacy .in, with matching P x P delays.

The Python parser converts only the graph; build_format1 (C++) creates the
P x N duration matrix, copies the delays, and writes the legacy file.
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from convert_graph import read_rs2

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
GRAPHS = ROOT / "tests" / "format_compare_graphs"


def absolute(path):
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def read_matrix(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.split():
            rows.append([int(x) for x in line.split()])
    if not rows or any(len(row) != len(rows) for row in rows):
        raise ValueError("delay matrix is not square")
    return rows


def make_matrix(path, processors):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(
        " ".join("0" if i == j else "2" for j in range(processors)) + "\n"
        for i in range(processors)
    ), encoding="utf-8")


def verify_output(output, ids_file, source, matrix):
    ids, weights, edges = read_rs2(source)
    saved_ids = json.loads(ids_file.read_text(encoding="utf-8"))["original_ids"]
    if saved_ids != ids:
        raise ValueError("original IDs were changed")
    values = [int(token) for token in output.read_text(encoding="utf-8").split()]
    if len(values) < 3:
        raise ValueError("incomplete .in file")
    n, p, m = values[:3]
    if (n, p, m) != (len(weights), len(matrix), len(edges)):
        raise ValueError("incorrect N/P/M in .in file")
    if len(values) != 3 + p*n + p*p + 2*m:
        raise ValueError("unexpected number of values in .in file")
    offset = 3
    for _ in range(p):
        if values[offset:offset+n] != weights:
            raise ValueError("task weights were changed")
        offset += n
    for row in matrix:
        if values[offset:offset+p] != row:
            raise ValueError("delay matrix was changed")
        offset += p
    actual_edges = [(values[i], values[i+1]) for i in range(offset, len(values), 2)]
    if actual_edges != edges:
        raise ValueError("graph edges were changed")
    return n, p, m


def relative_graph_path(graph):
    try:
        return graph.relative_to(GRAPHS.resolve())
    except ValueError:
        return Path("custom") / graph.name


def convert_one(graph, output, matrix_path, processors, builder):
    if not graph.is_file():
        raise ValueError(f"missing RS2 graph: {graph}")
    if not builder.is_file():
        raise ValueError(f"missing C++ builder: {builder}")

    if matrix_path is None:
        matrix_path = HERE / "matrices" / relative_graph_path(graph)
        make_matrix(matrix_path, processors)
    elif not matrix_path.is_file():
        raise ValueError(f"missing matrix: {matrix_path}")
    matrix = read_matrix(matrix_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="format_convert_") as td:
        intermediate = Path(td) / "graph.graph"
        for command in (
            [sys.executable, str(HERE / "convert_graph.py"),
             "--input", str(graph), "--output", str(intermediate)],
            [str(builder), str(intermediate), str(matrix_path), str(output)],
        ):
            proc = subprocess.run(command, capture_output=True, text=True, check=False)
            if proc.returncode != 0:
                raise ValueError(proc.stderr.strip() or proc.stdout.strip() or "conversion failed")

        ids_file = intermediate.with_suffix(".ids.json")
        n, p, m = verify_output(output, ids_file, graph, matrix)
        shutil.copyfile(ids_file, output.with_suffix(".ids.json"))
    print(f"OK: {relative_graph_path(graph)}  N={n}, P={p}, M={m}")
    return matrix_path


def processor_counts(text):
    try:
        values = [int(x.strip()) for x in text.split(",")]
        if not values or any(x < 1 for x in values):
            raise ValueError
        return values
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--processors must be positive integers, e.g. 2,3,4") from exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--input", type=Path, help="one RS2 graph")
    inputs.add_argument("--all", action="store_true", help="all graphs under format_compare_graphs")
    matrix_opts = parser.add_mutually_exclusive_group(required=True)
    matrix_opts.add_argument("--processors", type=processor_counts,
                             help="one P for --input, or cyclic list P1,P2,... for --all")
    matrix_opts.add_argument("--matrix", type=Path, help="existing common matrix")
    parser.add_argument("--output", type=Path, help=".in output (only with --input)")
    parser.add_argument("--builder", type=Path, default=HERE / "build_format1")
    args = parser.parse_args()
    if args.all and args.output:
        parser.error("--output can only be used with --input")
    if args.input and args.processors and len(args.processors) != 1:
        parser.error("use exactly one processor count with --input")
    try:
        if args.all:
            graphs = sorted(GRAPHS.glob("*/*.txt"))
            if not graphs:
                raise ValueError(f"no RS2 graphs under {GRAPHS}")
        else:
            graphs = [absolute(args.input)]
        matrix_path = absolute(args.matrix) if args.matrix else None
        builder = absolute(args.builder)
        for i, graph in enumerate(graphs):
            graph = graph.resolve()
            output = (absolute(args.output) if args.output else
                      HERE / "format1" / relative_graph_path(graph).with_suffix(".in"))
            p = args.processors[i % len(args.processors)] if args.processors else None
            convert_one(graph, output, matrix_path, p, builder)
        print(f"Converted and verified: {len(graphs)} graph(s)")
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
