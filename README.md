# ARGUS Redrob Ranker

Deterministic, offline candidate ranker for the Redrob Senior AI Engineer challenge.

## Reproduce

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
python validate_submission.py ./submission.csv
```

The rank command scans the JSONL once, computes JD-specific feature, trust, availability,
and anomaly signals, then writes both `submission.csv` and `submission.xlsx`.

## Method

The scorer rewards candidates with hands-on production evidence for search, retrieval,
ranking, recommendation, vector infrastructure, and evaluation systems. It down-weights
services-only histories, nontechnical keyword stuffing, stale platform activity,
CV/speech-heavy profiles without NLP/IR evidence, title-chasing, long notice periods,
and honeypot-like consistency failures.

No hosted LLM APIs, GPU runtime, network calls, or candidate-specific manual edits are
used by the ranking step.

## Small Sandbox

```bash
python sandbox/run_sample.py --candidates ./sample_candidates.json --out ./sandbox_submission.csv
```

This runs the same rank path on the included sample candidate file.
