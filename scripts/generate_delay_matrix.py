#!/usr/bin/env python3
"""Generate a shared processor-to-processor delay matrix."""

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processors", type=int, required=True)
    parser.add_argument("--delay", type=int, default=2)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.processors < 1:
        parser.error("--processors must be positive")
    if not 0 <= args.delay <= 2**31 - 1:
        parser.error("--delay must be between 0 and 2147483647")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open("w", encoding="utf-8") as out:
        for i in range(args.processors):
            row = [
                "0" if i == j else str(args.delay)
                for j in range(args.processors)
            ]
            out.write(" ".join(row) + "\n")

    print(f"OK: {args.output} ({args.processors}x{args.processors})")


if __name__ == "__main__":
    main()
