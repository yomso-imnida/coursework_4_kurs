#!/usr/bin/env python3
"""Draw the same graph in RS2 and legacy .in side-by-side as one SVG picture.

Uses only Python's standard library. Node labels show original ID and weight.
"""
import argparse
import json
from collections import Counter, defaultdict, deque
from html import escape
from pathlib import Path

from convert_graph import read_rs2


def read_legacy(path):
    values = [int(v) for v in path.read_text(encoding="utf-8").split()]
    if len(values) < 3:
        raise ValueError("incomplete legacy input")
    n, p, m = values[:3]
    if n < 1 or p < 1 or m < 0 or len(values) != 3 + n*p + p*p + 2*m:
        raise ValueError("invalid format-1 input size")
    weights = values[3:3+n]
    for i in range(1, p):
        if values[3+i*n:3+(i+1)*n] != weights:
            raise ValueError("duration rows differ between processors; cannot compare with RS2 weights")
    start = 3 + p*n + p*p
    edges = [(values[i], values[i+1]) for i in range(start, len(values), 2)]
    if any(a < 0 or b < 0 or a >= n or b >= n for a, b in edges):
        raise ValueError("invalid edge index in legacy input")
    return weights, edges


def layout(ids, edges):
    n = len(ids)
    parents = [0]*n
    following = [[] for _ in range(n)]
    for u, v in edges:
        parents[v] += 1
        following[u].append(v)
    todo = deque(i for i in range(n) if parents[i] == 0)
    layer = [0]*n
    seen = 0
    while todo:
        u = todo.popleft()
        seen += 1
        for v in following[u]:
            layer[v] = max(layer[v], layer[u]+1)
            parents[v] -= 1
            if parents[v] == 0:
                todo.append(v)
    if seen != n:
        raise ValueError("the RS2 graph has a directed cycle")
    groups = defaultdict(list)
    for idx, lvl in enumerate(layer):
        groups[lvl].append(idx)
    max_width = max(len(g) for g in groups.values())
    width = max(650, max_width*115 + 110)
    height = max(340, (max(groups)+1)*120 + 90)
    coords = {}
    for lvl, group in groups.items():
        for offset, idx in enumerate(group):
            coords[idx] = (width*(offset+1)/(len(group)+1), 80+120*lvl)
    return width, height, coords


def panel(title, ids, weights, edges, coords, offset, width, height):
    items = [f'<g transform="translate({offset},0)">',
             f'<text x="{width/2:.1f}" y="32" text-anchor="middle" font-size="21" font-weight="700" fill="#26364b">{escape(title)}</text>']
    for u, v in edges:
        if u in coords and v in coords:
            x1,y1=coords[u];x2,y2=coords[v]
            items.append(f'<line x1="{x1:.1f}" y1="{y1+22:.1f}" x2="{x2:.1f}" y2="{y2-24:.1f}" stroke="#72859b" stroke-width="1.8" marker-end="url(#arrow)"/>')
    for i, (x,y) in coords.items():
        items.append(f'<rect x="{x-35:.1f}" y="{y-23:.1f}" width="70" height="46" rx="10" fill="#f0f5ff" stroke="#5276ae" stroke-width="1.7"/>')
        items.append(f'<text x="{x:.1f}" y="{y-3:.1f}" text-anchor="middle" font-size="14" font-weight="700" fill="#182a40">{ids[i]}</text>')
        items.append(f'<text x="{x:.1f}" y="{y+14:.1f}" text-anchor="middle" font-size="12" fill="#52667d">w={weights[i]}</text>')
    items.append('</g>')
    return '\n'.join(items)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rs2", type=Path, required=True)
    parser.add_argument("--format1", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="SVG image path")
    parser.add_argument("--ids", type=Path, help="Mapping JSON, default <format1>.ids.json")
    args = parser.parse_args()
    ids, w2, e2 = read_rs2(args.rs2)
    w1, e1 = read_legacy(args.format1)
    ids_path = args.ids or args.format1.with_suffix('.ids.json')
    old_ids = json.loads(ids_path.read_text(encoding="utf-8"))["original_ids"]
    if len(ids) != len(w1) or len(old_ids) != len(w1):
        raise ValueError("different number of nodes")
    old_idx = {value:i for i,value in enumerate(old_ids)}
    if len(old_idx) != len(old_ids) or set(old_ids) != set(ids):
        raise ValueError("original IDs do not match")
    sorted_old_weights = [w1[old_idx[v]] for v in ids]
    old_edges = [(ids.index(old_ids[u]), ids.index(old_ids[v])) for u,v in e1]
    equal = w2 == sorted_old_weights and Counter(e2) == Counter(old_edges)
    width, height, coords = layout(ids, e2)
    gap=30
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width*2+gap}" height="{height}" viewBox="0 0 {width*2+gap} {height}">',
           '<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L7,3 z" fill="#72859b"/></marker></defs>',
           f'<rect width="100%" height="100%" fill="#ffffff"/>',
           f'<line x1="{width+gap/2}" x2="{width+gap/2}" y1="15" y2="{height-20}" stroke="#e1e7ee" stroke-width="2"/>',
           panel('Формат 2 — RS2', ids, w2, e2, coords, 0, width, height),
           panel('Формат 1 — .in', ids, sorted_old_weights, old_edges, coords, width+gap, width, height),
           f'<text x="{width}" y="{height-17}" text-anchor="middle" font-size="15" fill="{"#16824f" if equal else "#b42318"}">{"OK: узлы, веса и связи совпадают" if equal else "FAIL: найдены различия"}</text>',
           '</svg>']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text('\n'.join(svg), encoding='utf-8')
    print(f'{"PASS" if equal else "FAIL"}: {args.output}')
    return 0 if equal else 1


if __name__ == '__main__':
    raise SystemExit(main())
