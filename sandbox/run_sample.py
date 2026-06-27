#!/usr/bin/env python3
"""Small-sample sandbox runner.

Usage:
    python sandbox/run_sample.py --candidates sample_candidates.json --out sandbox_submission.csv
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
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
    args = parser.parse_args()

    records = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
    if len(records) > 100:
        records = records[:100]
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".jsonl", delete=False) as handle:
        for rec in records:
            handle.write(json.dumps(rec) + "\n")
        tmp = handle.name
    rows = rank_candidates(tmp, top_n=min(100, len(records)))
    write_csv(rows, args.out)
    write_xlsx(rows, Path(args.out).with_suffix(".xlsx"))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
