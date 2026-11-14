"""Benchmark: parse TOML documents of increasing size (many tables).

Generates synthetic data-warehouse-style metadata catalogs: many [table]
headers each with a handful of key/value pairs, comments and blank lines,
mirroring the reported workload (20k tables, ~1MB document).

Usage:
    python benchmarks/bench_parse.py [--sizes 1000,5000,10000,20000] [--repeat 3]
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tomlkit


def make_document(n_tables: int) -> str:
    """Build a TOML document with ``n_tables`` tables, ~55 bytes per table header."""
    parts: list[str] = [
        "# data warehouse metadata catalog\n",
        'catalog = "warehouse"\n',
        "version = 3\n",
        "\n",
    ]
    for i in range(n_tables):
        parts.append(f"[tables.dw_schema.table_{i:05d}]  # table {i}\n")
        parts.append(f'description = "metadata for table number {i}"\n')
        parts.append(f"row_count = {i * 137}\n")
        parts.append("partitioned = true\n")
        parts.append(f"retention_days = {30 + i % 90}\n")
        parts.append('owner = "team-data"\n')
        parts.append("\n")
    return "".join(parts)


def bench(doc: str, repeat: int) -> float:
    timings = []
    for _ in range(repeat):
        start = time.perf_counter()
        tomlkit.parse(doc)
        timings.append(time.perf_counter() - start)
    return min(timings)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="1000,5000,10000,20000")
    ap.add_argument("--repeat", type=int, default=3)
    args = ap.parse_args()

    sizes = [int(s) for s in args.sizes.split(",")]
    print(f"{'tables':>8} {'bytes':>10} {'best of %d (s)' % args.repeat:>16} {'MB/s':>8}")
    results = {}
    for n in sizes:
        doc = make_document(n)
        t = bench(doc, args.repeat)
        rate = len(doc) / t / 1e6
        results[n] = t
        print(f"{n:>8} {len(doc):>10} {t:>16.4f} {rate:>8.2f}")

    # Sanity: round-trip must be byte-identical.
    doc = make_document(200)
    assert tomlkit.dumps(tomlkit.parse(doc)) == doc, "round-trip mismatch!"
    print("round-trip byte-identical: OK")


if __name__ == "__main__":
    main()
