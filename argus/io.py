"""Input loading, candidate normalization, and text helpers."""

from __future__ import annotations

import csv
import gzip
import json
import re
from collections.abc import Iterator
from pathlib import Path


def iter_candidates(path: str | Path) -> Iterator[dict]:
    """Yield normalized candidate records from JSONL, JSON, CSV, or gzipped inputs.

    Redrob records already match the internal schema. Other inputs are mapped from
    common flat fields such as name/title/summary/location/skills/experience.
    """
    p = Path(path)
    suffixes = [s.lower() for s in p.suffixes]
    if suffixes[-2:] in ([".jsonl", ".gz"], [".ndjson", ".gz"]) or p.suffix.lower() in {".jsonl", ".ndjson"}:
        yield from iter_jsonl(p)
        return
    if suffixes[-2:] == [".json", ".gz"] or p.suffix.lower() == ".json":
        yield from iter_json(p)
        return
    if suffixes[-2:] == [".csv", ".gz"] or p.suffix.lower() == ".csv":
        yield from iter_csv(p)
        return
    raise ValueError(f"Unsupported input format for {p}; use .jsonl, .json, .csv, optionally .gz")


def iter_jsonl(path: str | Path) -> Iterator[dict]:
    p = Path(path)
    opener = gzip.open if p.suffix.lower() == ".gz" else open
    with opener(p, "rt", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{p}:{line_no}: invalid JSON: {exc}") from exc
            if is_native_candidate(rec):
                yield rec
            else:
                yield normalize_candidate(rec, line_no)


def iter_json(path: str | Path) -> Iterator[dict]:
    p = Path(path)
    opener = gzip.open if p.suffix.lower() == ".gz" else open
    with opener(p, "rt", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        records = data.get("candidates") or data.get("records") or data.get("data")
        if records is None:
            records = [data]
    else:
        records = data
    if not isinstance(records, list):
        raise ValueError(f"{p}: JSON input must be a record, list, or object with candidates/records/data list")
    for idx, rec in enumerate(records, start=1):
        if not isinstance(rec, dict):
            raise ValueError(f"{p}:{idx}: expected object record")
        yield normalize_candidate(rec, idx)


def iter_csv(path: str | Path) -> Iterator[dict]:
    p = Path(path)
    opener = gzip.open if p.suffix.lower() == ".gz" else open
    with opener(p, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for idx, row in enumerate(reader, start=1):
            yield normalize_candidate(row, idx)


def normalize_candidate(record: dict, index: int = 1) -> dict:
    if "profile" in record and "career_history" in record:
        rec = dict(record)
        rec.setdefault("candidate_id", candidate_id_from(record, index))
        rec.setdefault("education", [])
        rec.setdefault("skills", [])
        rec.setdefault("redrob_signals", {})
        return rec

    name = first(record, "anonymized_name", "name", "full_name", "candidate_name")
    title = first(record, "current_title", "title", "job_title", "role", "headline")
    company = first(record, "current_company", "company", "employer", "organization")
    summary = first(record, "summary", "profile_summary", "bio", "description", "about", "resume_text")
    location = first(record, "location", "city", "current_location")
    country = first(record, "country")
    yoe = to_float(first(record, "years_of_experience", "yoe", "experience_years", "experience"), 0.0)
    industry = first(record, "current_industry", "industry")
    skills = parse_skills(first(record, "skills", "skill_names", "technologies", "tech_stack"))
    role_description = first(record, "career_description", "experience_summary", "work_experience", "description", "summary")
    start_year = first(record, "start_year", "career_start_year")
    duration_months = int(max(0, round(yoe * 12))) if yoe else 0
    career_role = {
        "company": company,
        "title": title,
        "start_date": f"{int(to_float(start_year, 2020)):04d}-01-01" if start_year else "2020-01-01",
        "end_date": None,
        "duration_months": duration_months,
        "is_current": True,
        "industry": industry,
        "company_size": first(record, "current_company_size", "company_size") or "unknown",
        "description": role_description or summary,
    }
    signals = parse_signals(record)
    return {
        "candidate_id": candidate_id_from(record, index),
        "profile": {
            "anonymized_name": name,
            "headline": first(record, "headline") or title,
            "summary": summary,
            "location": location,
            "country": country,
            "years_of_experience": yoe,
            "current_title": title,
            "current_company": company,
            "current_company_size": first(record, "current_company_size", "company_size") or "unknown",
            "current_industry": industry,
        },
        "career_history": [career_role],
        "education": parse_education(record),
        "skills": skills,
        "certifications": [],
        "languages": [],
        "redrob_signals": signals,
    }


def is_native_candidate(record: dict) -> bool:
    return (
        "candidate_id" in record
        and "profile" in record
        and "career_history" in record
        and "skills" in record
        and "redrob_signals" in record
    )


def first(record: dict, *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def candidate_id_from(record: dict, index: int) -> str:
    raw = first(record, "candidate_id", "id", "candidateId", "candidateID")
    if re.fullmatch(r"CAND_\d{7}", raw):
        return raw
    if raw:
        cleaned = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_")
        return cleaned[:32] or f"CAND_{index:07d}"
    return f"CAND_{index:07d}"


def to_float(value: object, default: float) -> float:
    try:
        if value in (None, ""):
            return default
        return float(str(value).replace("+", "").strip())
    except ValueError:
        match = re.search(r"\d+(?:\.\d+)?", str(value))
        return float(match.group(0)) if match else default


def parse_skills(value: object) -> list[dict]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        items = value
    else:
        items = re.split(r"[,;|/]", str(value))
    skills = []
    for item in items:
        if isinstance(item, dict):
            name = item.get("name") or item.get("skill") or ""
            prof = item.get("proficiency") or "intermediate"
            months = int(to_float(item.get("duration_months"), 0))
            endorsements = int(to_float(item.get("endorsements"), 0))
        else:
            name = str(item).strip()
            prof = "intermediate"
            months = 0
            endorsements = 0
        if name:
            skills.append({"name": name, "proficiency": prof, "endorsements": endorsements, "duration_months": months})
    return skills


def parse_education(record: dict) -> list[dict]:
    field = first(record, "field_of_study", "degree_field")
    degree = first(record, "degree", "education")
    if not field and not degree:
        return []
    return [
        {
            "institution": first(record, "institution", "school", "college", "university") or "unknown",
            "degree": degree or "unknown",
            "field_of_study": field,
            "start_year": int(to_float(first(record, "education_start_year"), 2000)),
            "end_year": int(to_float(first(record, "education_end_year", "graduation_year"), 2004)),
            "grade": first(record, "grade", "gpa"),
            "tier": first(record, "tier", "school_tier") or "unknown",
        }
    ]


def parse_signals(record: dict) -> dict:
    nested = record.get("redrob_signals")
    sig = dict(nested) if isinstance(nested, dict) else {}
    for key in (
        "last_active_date",
        "open_to_work_flag",
        "recruiter_response_rate",
        "interview_completion_rate",
        "notice_period_days",
        "willing_to_relocate",
        "saved_by_recruiters_30d",
        "verified_email",
        "verified_phone",
        "linkedin_connected",
        "github_activity_score",
    ):
        if key in record and key not in sig:
            sig[key] = record[key]
    for bool_key in ("open_to_work_flag", "willing_to_relocate", "verified_email", "verified_phone", "linkedin_connected"):
        if isinstance(sig.get(bool_key), str):
            sig[bool_key] = sig[bool_key].strip().lower() in {"1", "true", "yes", "y"}
    return sig


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
