#!/usr/bin/env python3
"""ARGUS online ranking entrypoint.

Reproduce command:
    python rank.py --candidates ./candidates.jsonl --out ./submission.csv
"""

from __future__ import annotations

import argparse
import heapq
import random
import sys
from pathlib import Path

from argus import config as C
from argus.anomaly import apply_gate
from argus.export import write_csv, write_xlsx
from argus.features import extract_features, raw_score
from argus.io import iter_candidates
from argus.reasoning import reasoning_for
from argus.trust import trust_coeff


def final_score(features: dict) -> float:
    base = raw_score(features)
    score = base * (0.55 + 0.45 * float(features.get("avail_coeff", 0.0)))
    score *= 0.75 + 0.25 * trust_coeff(features)
    return apply_gate(score, features)


def rank_candidates(candidates_path: str | Path, top_n: int = C.TOP_N) -> list[dict]:
    random.seed(C.SEED)
    heap_size = max(top_n * 8, 800)
    heap: list[tuple[float, str, dict]] = []
    seen = 0
    for rec in iter_candidates(candidates_path):
        f = extract_features(rec)
        score = final_score(f)
        cid = str(f["candidate_id"])
        item = (score, cid, f)
        if len(heap) < heap_size:
            heapq.heappush(heap, item)
        elif item > heap[0]:
            heapq.heapreplace(heap, item)
        seen += 1
    if seen == 0:
        raise RuntimeError("No candidates found in input")
    ordered = sorted(heap, key=lambda x: (-x[0], x[1]))[:top_n]
    top_raw = ordered[0][0]
    bottom_raw = ordered[-1][0]
    span = max(1e-9, top_raw - bottom_raw)
    rows = []
    prev = 1.0
    for rank, (score, cid, f) in enumerate(ordered, start=1):
        calibrated = 0.35 + 0.64 * ((score - bottom_raw) / span)
        calibrated = min(prev, calibrated)
        prev = calibrated
        rows.append(
            {
                "candidate_id": cid,
                "rank": rank,
                "score": f"{calibrated:.6f}",
                "reasoning": reasoning_for(f, rank),
            }
        )
    return rows


def validate_or_die(out_path: Path) -> None:
    try:
        from validate_submission import validate_submission
    except Exception as exc:
        raise RuntimeError(f"Could not import bundled validator: {exc}") from exc
    errors = validate_submission(out_path)
    if errors:
        raise RuntimeError("Validator failed:\n- " + "\n- ".join(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True, help="Path to candidates input: .jsonl, .json, .csv, optionally .gz")
    parser.add_argument("--out", required=True, help="CSV output path")
    parser.add_argument("--xlsx", help="Optional XLSX output path; defaults to --out with .xlsx suffix")
    parser.add_argument("--top-n", type=int, default=C.TOP_N, help="Number of candidates to rank; default 100")
    parser.add_argument(
        "--validate-redrob",
        action="store_true",
        help="Run the bundled strict Redrob validator; requires exactly 100 CAND_XXXXXXX rows",
    )
    args = parser.parse_args(argv)

    out_path = Path(args.out)
    rows = rank_candidates(args.candidates, top_n=args.top_n)
    write_csv(rows, out_path)
    xlsx_path = Path(args.xlsx) if args.xlsx else out_path.with_suffix(".xlsx")
    write_xlsx(rows, xlsx_path)
    if args.validate_redrob:
        validate_or_die(out_path)
    print(f"Wrote {out_path} and {xlsx_path} ({len(rows)} rows).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
