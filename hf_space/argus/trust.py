"""Trust coefficient implementation."""

from __future__ import annotations

from .text import bounded


def trust_coeff(f: dict) -> float:
    inflation_pen = bounded(float(f.get("n_inflated", 0.0)) * 0.08, 0.0, 0.5)
    verify_bonus = bounded(float(f.get("n_verified", 0.0)) * 0.04, 0.0, 0.2)
    consist_pen = 0.25 if float(f.get("consistency_flags", 0.0)) else 0.0
    depth_bonus = bounded(
        (float(f.get("tool_density", 0.0)) + float(f.get("metric_density", 0.0))) * 0.075,
        0.0,
        0.15,
    )
    chan = float(f.get("channel_corro", 0.0)) * 0.10
    return bounded(0.80 - inflation_pen - consist_pen + verify_bonus + depth_bonus + chan)

