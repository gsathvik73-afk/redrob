"""Streaming JSONL I/O and schema guards."""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterator
from pathlib import Path


def iter_jsonl(path: str | Path) -> Iterator[dict]:
    p = Path(path)
    opener = gzip.open if p.suffix == ".gz" else open
    with opener(p, "rt", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{p}:{line_no}: invalid JSON: {exc}") from exc
            if "candidate_id" not in rec or "profile" not in rec:
                raise ValueError(f"{p}:{line_no}: missing required candidate keys")
            yield rec


def candidate_text(record: dict) -> str:
    profile = record.get("profile") or {}
    parts = [
        profile.get("headline", ""),
        profile.get("summary", ""),
        profile.get("current_title", ""),
        profile.get("current_company", ""),
        profile.get("current_industry", ""),
    ]
    for role in record.get("career_history") or []:
        parts.extend(
            [
                role.get("company", ""),
                role.get("title", ""),
                role.get("industry", ""),
                role.get("description", ""),
            ]
        )
    for skill in record.get("skills") or []:
        parts.append(skill.get("name", ""))
    return " ".join(str(p) for p in parts if p)

