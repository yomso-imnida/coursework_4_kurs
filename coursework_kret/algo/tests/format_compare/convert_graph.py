#!/usr/bin/env python3
"""Convert RS2 graphs into indexed graph data for the format-1 builder.

The output *.graph has:
  N M
  w0 w1 ... w(N-1)
  u0 v0
  ... M edges with zero-based *internal* indices

The companion *.ids.json stores the original RS2 node IDs in index order.
"""

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
GRAPH_ROOT = HERE.parent / "format_compare_graphs"
OUTPUT_ROOT = HERE / "intermediate"
CATEGORIES = ("layered", "rand", "triang")
MAX_SIZE_T = (1 << 64) - 1


def unsigned_number(token, path, line_number):
    if not re.fullmatch(r"[0-9]+", token):
        raise ValueError(f"{path}:{line_number}: invalid unsigned number: {token!r}")
    value = int(token)
    if value > MAX_SIZE_T:
        raise ValueError(f"{path}:{line_number}: number exceeds 64-bit size_t")
    return value


def read_rs2(path):
    with path.open("r", encoding="utf-8-sig") as f:
        header = f.readline()
        if header.split() != ["node", "size", "children"]:
            raise ValueError(f"{path}: invalid RS2 header")

        nodes = {}
        for line_number, line in enumerate(f, start=2):
            fields = line.split()
            if not fields:
                continue
            if len(fields) < 2:
                raise ValueError(f"{path}:{line_number}: missing weight")

            node_id = unsigned_number(fields[0], path, line_number)
            weight = unsigned_number(fields[1], path, line_number)
            children = [unsigned_number(t, path, line_number) for t in fields[2:]]

            if node_id in nodes:
                raise ValueError(f"{path}:{line_number}: duplicate node {node_id}")
            nodes[node_id] = (weight, children)

    if not nodes:
        raise ValueError(f"{path}: graph has no nodes")

    original_ids = sorted(nodes)
    id_to_index = {node_id: i for i, node_id in enumerate(original_ids)}
    weights = [nodes[node_id][0] for node_id in original_ids]
    edges = []

    for node_id in original_ids:
        for child in nodes[node_id][1]:
            if child not in id_to_index:
                raise ValueError(f"{path}: undefined child {child} of node {node_id}")
            edges.append((id_to_index[node_id], id_to_index[child]))

    return original_ids, weights, edges


def convert(path, output):
    original_ids, weights, edges = read_rs2(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", encoding="utf-8", newline="\n") as f:
        f.write(f"{len(weights)} {len(edges)}\n")
        f.write(" ".join(map(str, weights)) + "\n")
        for source, target in edges:
            f.write(f"{source} {target}\n")

    ids_path = output.with_suffix(".ids.json")
    ids_path.write_text(
        json.dumps({"original_ids": original_ids}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"OK: {path} -> {output} (N={len(weights)}, M={len(edges)})")


def default_destination(graph):
    try:
        relative = graph.resolve().relative_to(GRAPH_ROOT.resolve())
    except ValueError:
        relative = Path("custom") / graph.name
    return OUTPUT_ROOT / relative.with_suffix(".graph")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--all", action="store_true", help="Convert all graphs in the three test folders")
    mode.add_argument("--input", type=Path, help="Convert one RS2 graph")
    parser.add_argument("--output", type=Path, help="Output *.graph path (only with --input)")
    args = parser.parse_args()

    try:
        if args.all:
            if args.output is not None:
                parser.error("--output can only be used with --input")
            graphs = [p for category in CATEGORIES
                      for p in sorted((GRAPH_ROOT / category).glob("*.txt"))]
            if not graphs:
                raise ValueError(f"no graph files found in {GRAPH_ROOT}")
            for graph in graphs:
                convert(graph, default_destination(graph))
            print(f"Converted {len(graphs)} graph(s)")
        else:
            graph = args.input
            convert(graph, args.output or default_destination(graph))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()
