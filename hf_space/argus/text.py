"""Text normalization and lexical helpers."""

from __future__ import annotations

import re
from collections.abc import Iterable

WORD_RE = re.compile(r"[a-z0-9+#./-]+")
NUMBER_METRIC_RE = re.compile(
    r"(?i)\b\d+(?:\.\d+)?\s*(?:%|ms|s|sec|seconds|gb|tb|mb|x|k|m|million|billion|qps|rps|latency|users|requests|rows|records)\b"
)


def normalize(text: object) -> str:
    if text is None:
        return ""
    return " ".join(str(text).lower().split())


def tokens(text: object) -> list[str]:
    return WORD_RE.findall(normalize(text))


def contains_any(text: str, terms: Iterable[str]) -> bool:
    return contains_any_norm(normalize(text), terms)


def contains_any_norm(hay: str, terms: Iterable[str]) -> bool:
    return any(term in hay for term in terms)


def count_terms(text: str, terms: Iterable[str]) -> int:
    return count_terms_norm(normalize(text), terms)


def count_terms_norm(hay: str, terms: Iterable[str]) -> int:
    return sum(hay.count(str(term).lower()) for term in terms if term)


def word_count(text: str) -> int:
    return max(1, len(str(text).split()))


def metric_density(text: str) -> float:
    return 100.0 * len(NUMBER_METRIC_RE.findall(text)) / word_count(text)


def term_density(text: str, terms: Iterable[str]) -> float:
    hay = normalize(text)
    return 100.0 * count_terms_norm(hay, terms) / word_count(hay)


def bounded(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))
