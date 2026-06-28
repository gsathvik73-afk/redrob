"""Rule-based anomaly gate for impossible or honeypot-like profiles."""

from __future__ import annotations


def is_gated(f: dict) -> bool:
    if float(f.get("consistency_flags", 0.0)):
        return True
    if float(f.get("stuffer_flag", 0.0)) >= 1.0:
        return True
    if float(f.get("nontech", 0.0)) and float(f.get("core_skill_score", 0.0)) > 0.6:
        return True
    if float(f.get("services_only", 0.0)) and float(f.get("product_ratio", 0.0)) == 0.0:
        return True
    return False


def apply_gate(score: float, f: dict) -> float:
    return score * 0.01 if is_gated(f) else score

