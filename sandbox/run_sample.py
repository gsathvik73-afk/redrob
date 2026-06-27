#!/usr/bin/env python3
"""Small-sample sandbox runner.

Usage:
    python sandbox/run_sample.py --candidates sample_candidates.json --out sandbox_submission.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rank import rank_candidates
from argus.export import write_csv, write_xlsx


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", default="sample_candidates.json")
    parser.add_argument("--out", default="sandbox_submission.csv")
    parser.add_argument("--top-n", type=int, default=100)
    args = parser.parse_args()

    rows = rank_candidates(args.candidates, top_n=args.top_n)
    write_csv(rows, args.out)
    write_xlsx(rows, Path(args.out).with_suffix(".xlsx"))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
