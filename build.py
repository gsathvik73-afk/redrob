#!/usr/bin/env python3
"""Offline artifact placeholder.

The released bundle does not include judged labels, so ARGUS uses a deterministic
online scorer. This command exists for repository reproducibility and records
the current no-training artifact state.
"""

from __future__ import annotations

import json
from pathlib import Path

from argus import config as C


def main() -> None:
    Path("artifacts").mkdir(exist_ok=True)
    manifest = {
        "mode": "deterministic_feature_ranker",
        "seed": C.SEED,
        "today": C.TODAY.isoformat(),
        "note": "No hidden labels or hosted LLM calls are required for rank.py.",
    }
    Path("artifacts/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Wrote artifacts/manifest.json")


if __name__ == "__main__":
    main()

