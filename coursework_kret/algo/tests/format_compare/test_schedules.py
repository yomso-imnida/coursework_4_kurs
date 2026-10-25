#!/usr/bin/env python3
"""Compare pre-converted .in files on ORIGINAL sched with RS2 on MODIFIED sched.

Conversion and matrix generation are a separate step; this script never
changes input files, only creates outputs under results/.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from convert_graph import read_rs2
from convert_to_format1 import read_matrix, verify_output

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
GRAPHS = ROOT / "tests" / "format_compare_graphs"
RESULTS = HERE / "results"


class TestError(Exception):
    pass


def abs_path(path):
    return path.resolve() if path.is_absolute() else (ROOT / path).resolve()


def run(cmd, log_path=None, timeout=180):
    try:
        proc = subprocess.run([str(v) for v in cmd], cwd=ROOT, text=True,
                              capture_output=True, errors="replace", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise TestError(f"cannot run {cmd[0]}: {exc}") from exc
    if log_path:
        log_path.write_text(f"$ {' '.join(map(str, cmd))}\nexit: {proc.returncode}\n"
                            f"{proc.stdout}\n{proc.stderr}", encoding="utf-8")
    if proc.returncode:
        message = (proc.stderr.strip() or proc.stdout.strip()).splitlines()[-5:]
        raise TestError(f"exit {proc.returncode}: {' | '.join(message)}")


def normalized(path, ids, is_old):
    data = json.loads(path.read_text(encoding="utf-8"))
    procs, seen = {}, []
    for proc, tasks in data["procs"].items():
        records = []
        for task in (tasks or []):
            job = task["task_no"]
            if is_old:
                if type(job) is not int or not 0 <= job < len(ids):
                    raise TestError(f"bad internal task ID: {job}")
                job = ids[job]
            seen.append(job)
            records.append({"id": job, "start": task["task_start"],
                            "duration": task["task_dur"]})
        procs[str(proc)] = sorted(records, key=lambda t: (t["start"], t["id"]))
    if sorted(seen) != sorted(ids):
        raise TestError(f"missing, repeated or unknown task IDs in {path}")
    return {"time": data["time"], "procs": procs}


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False,
                               sort_keys=True) + "\n", encoding="utf-8")


def test_graph(graph, args):
    rel = graph.relative_to(GRAPHS)
    old_in = HERE / "format1" / rel.with_suffix(".in")
    ids_file = old_in.with_suffix(".ids.json")
    matrix_file = HERE / "matrices" / rel
    for file in (old_in, ids_file, matrix_file):
        if not file.is_file():
            raise TestError(f"missing prepared input: {file}; run convert_to_format1.py --all --processors 2,3,4")
    ids = json.loads(ids_file.read_text(encoding="utf-8"))["original_ids"]
    expected_ids, _, _ = read_rs2(graph)
    if ids != expected_ids:
        raise TestError("old input ID mapping does not match source RS2")
    verify_output(old_in, ids_file, graph, read_matrix(matrix_file))

    dest = RESULTS / rel.with_suffix("")
    dest.mkdir(parents=True, exist_ok=True)
    old_json = dest / "original.json"
    new_json = dest / "modified.json"
    common = ["--conf", args.conf, "--command", args.algo,
              "--random", str(args.random)]
    run([args.original, "--input", old_in, "--output", old_json, *common],
        dest / "original.log", args.timeout)
    run([args.modified, "--graph", graph, "--matrix", matrix_file,
         "--output", new_json, *common], dest / "modified.log", args.timeout)
    old_norm = dest / "normalized_original.json"
    new_norm = dest / "normalized_modified.json"
    write_json(old_norm, normalized(old_json, ids, True))
    write_json(new_norm, normalized(new_json, ids, False))
    diff = subprocess.run(["diff", "-u", str(old_norm), str(new_norm)],
                          cwd=ROOT, capture_output=True, text=True, errors="replace")
    (dest / "schedule.diff").write_text(diff.stdout + diff.stderr, encoding="utf-8")
    if diff.returncode not in (0, 1):
        raise TestError(f"diff failed: {diff.stderr}")
    return diff.returncode == 0, dest / "schedule.diff"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--original", type=Path, default=ROOT / "build-original" / "sched")
    p.add_argument("--modified", type=Path, default=ROOT / "build" / "sched")
    p.add_argument("--conf", type=Path, default=ROOT / "config.toml")
    p.add_argument("--algo", default="misf")
    p.add_argument("--random", type=int, default=1234)
    p.add_argument("--timeout", type=int, default=180)
    p.add_argument("--category", help="test one folder, e.g. triang_small")
    p.add_argument("--limit", type=int)
    args = p.parse_args()
    for key in ("original", "modified", "conf"):
        value = abs_path(getattr(args, key))
        setattr(args, key, value)
        if not value.is_file():
            p.error(f"missing {key}: {value}")
    if args.limit is not None and args.limit < 1:
        p.error("--limit must be positive")
    if args.timeout < 1:
        p.error("--timeout must be positive")
    graphs = sorted((GRAPHS / args.category).glob("*.txt")) if args.category else sorted(GRAPHS.glob("*/*.txt"))
    if args.limit:
        graphs = graphs[:args.limit]
    if not graphs:
        p.error("no RS2 graphs found")
    passed = failed = errors = 0
    print(f"Original: {args.original}\nModified: {args.modified}\nTests: {len(graphs)}", flush=True)
    for i, graph in enumerate(graphs, 1):
        name = str(graph.relative_to(GRAPHS).with_suffix(""))
        try:
            equal, path = test_graph(graph, args)
            if equal:
                passed += 1
                print(f"[{i:02d}/{len(graphs):02d}] {name:<28} PASS", flush=True)
            else:
                failed += 1
                print(f"[{i:02d}/{len(graphs):02d}] {name:<28} FAIL: {path}", flush=True)
        except (TestError, OSError, ValueError, KeyError, IndexError) as exc:
            errors += 1
            print(f"[{i:02d}/{len(graphs):02d}] {name:<28} ERROR: {exc}", flush=True)
    print(f"\nPassed: {passed}/{len(graphs)} | Failed: {failed} | Errors: {errors}")
    return 0 if failed == 0 and errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
