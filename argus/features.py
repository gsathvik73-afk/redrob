"""Feature extraction for the Redrob Senior AI Engineer JD."""

from __future__ import annotations

import math
from datetime import date

from . import config as C
from .io import candidate_text
from .text import bounded, contains_any, count_terms, metric_density, normalize, term_density


def parse_date(value: object, default: date | None = None) -> date | None:
    if not value:
        return default
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return default


def triangular_yoe(yoe: float) -> float:
    if yoe < 3 or yoe > 11:
        return 0.0
    if 6 <= yoe <= 8:
        return 1.0
    if yoe < 6:
        return bounded((yoe - 3) / 3)
    return bounded((11 - yoe) / 3)


def availability_coeff(sig: dict, today: date = C.TODAY) -> float:
    last = parse_date(sig.get("last_active_date"), date(2000, 1, 1))
    days = (today - last).days if last else 9999
    recency = math.exp(-max(0, days) / 120.0)
    resp = bounded(float(sig.get("recruiter_response_rate", 0.0) or 0.0))
    icr = bounded(float(sig.get("interview_completion_rate", 0.0) or 0.0))
    otw = 1.0 if sig.get("open_to_work_flag") else 0.7
    notice = 1.0 - bounded(float(sig.get("notice_period_days", 90) or 90) / 180.0) * 0.3
    base = 0.45 * recency + 0.30 * resp + 0.15 * icr + 0.10 * notice
    return bounded(base * otw, 0.05, 1.0)


def product_ratio(record: dict) -> float:
    roles = record.get("career_history") or []
    total = sum(max(0, int(r.get("duration_months") or 0)) for r in roles) or len(roles) or 1
    product_months = 0
    for role in roles:
        months = max(1, int(role.get("duration_months") or 0))
        company = normalize(role.get("company"))
        industry = normalize(role.get("industry"))
        if is_services_company(company) or "services" in industry or "consulting" in industry:
            continue
        if contains_any(industry, C.PRODUCT_INDUSTRY_HINTS) or company:
            product_months += months
    return bounded(product_months / total)


def services_only(record: dict) -> float:
    roles = record.get("career_history") or []
    if not roles:
        return 0.0
    for role in roles:
        company = normalize(role.get("company"))
        industry = normalize(role.get("industry"))
        if not is_services_company(company) and "services" not in industry and "consulting" not in industry:
            return 0.0
    return 1.0


def is_services_company(company: str) -> bool:
    return any(firm in company for firm in C.SERVICES_FIRMS)


def built_system_hits(text: str) -> int:
    hits = 0
    chunks = [c.strip() for c in text.replace(";", ".").split(".") if c.strip()]
    for chunk in chunks:
        verb_present = contains_any(chunk, C.BUILDER_VERBS)
        if not verb_present:
            continue
        term_hits = count_terms(chunk, C.SYSTEM_TERMS)
        if term_hits:
            hits += min(3, term_hits)
    return hits


def hands_on_recency(record: dict, today: date = C.TODAY) -> tuple[float, float]:
    hands = ("built", "implemented", "coded", "developed", "shipped", "owned", "designed", "debugged")
    best_months = 999.0
    for role in record.get("career_history") or []:
        role_text = normalize(f"{role.get('title','')} {role.get('description','')}")
        if not contains_any(role_text, hands):
            continue
        end = parse_date(role.get("end_date")) or today
        months = max(0.0, (today - end).days / 30.4)
        best_months = min(best_months, months)
    return bounded(math.exp(-best_months / 24.0)), best_months


def title_chaser(record: dict) -> float:
    roles = record.get("career_history") or []
    if len(roles) < 3:
        return 0.0
    short = sum(1 for r in roles if int(r.get("duration_months") or 0) < 18)
    senior_words = sum(1 for r in roles if contains_any(r.get("title", ""), {"senior", "staff", "principal", "lead", "head"}))
    return bounded((short / len(roles)) * (0.5 + 0.5 * bounded(senior_words / len(roles))))


def claim_assessment(skills: list[dict], assess: dict) -> dict[str, float]:
    gaps = []
    n_inf = 0
    n_ver = 0
    for sk in skills:
        name = sk.get("name")
        if name not in assess:
            continue
        prof = C.PROFICIENCY.get(normalize(sk.get("proficiency")), 50.0)
        gap = prof - float(assess.get(name) or 0.0)
        gaps.append(gap)
        if gap > 30:
            n_inf += 1
        if gap <= 0:
            n_ver += 1
    return {
        "claim_assess_gap": sum(gaps) / len(gaps) if gaps else 0.0,
        "n_inflated": float(n_inf),
        "n_verified": float(n_ver),
        "measured": float(len(gaps)),
    }


def channel_corro(sig: dict) -> float:
    icr = bounded(float(sig.get("interview_completion_rate", 0) or 0))
    saved = math.log1p(float(sig.get("saved_by_recruiters_30d", 0) or 0)) / math.log1p(50)
    verified = sum(1 for key in ("verified_email", "verified_phone", "linkedin_connected") if sig.get(key)) / 3.0
    gh = max(float(sig.get("github_activity_score", -1) or -1), 0.0) / 100.0
    return bounded(0.45 * icr + 0.25 * min(saved, 1) + 0.25 * verified + 0.05 * gh)


def consistency_flags(record: dict, today: date = C.TODAY) -> int:
    flags = 0
    roles = record.get("career_history") or []
    tenure = sum(int(h.get("duration_months") or 0) for h in roles)
    starts = [parse_date(h.get("start_date")) for h in roles if h.get("start_date")]
    starts = [d for d in starts if d]
    if starts:
        span = (today - min(starts)).days / 30.4
        if tenure > span + 6:
            flags |= 1
        yoe = float((record.get("profile") or {}).get("years_of_experience") or 0)
        if abs(yoe - ((today - min(starts)).days / 365.25)) > 6:
            flags |= 4
    for skill in record.get("skills") or []:
        if normalize(skill.get("proficiency")) == "expert" and int(skill.get("duration_months") or 0) == 0:
            flags |= 2
    return flags


def education_signal(record: dict) -> float:
    tiers = {"tier_1": 1.0, "tier_2": 0.65, "tier_3": 0.3, "tier_4": 0.0, "unknown": 0.15}
    return max((tiers.get(e.get("tier", "unknown"), 0.15) for e in record.get("education") or []), default=0.15)


def extract_features(record: dict) -> dict[str, float | str]:
    profile = record.get("profile") or {}
    sig = record.get("redrob_signals") or {}
    text = normalize(candidate_text(record))
    skills_text = " ".join(normalize(s.get("name")) for s in record.get("skills") or [])
    title = normalize(profile.get("current_title"))
    yoe = float(profile.get("years_of_experience") or 0.0)
    ai_skill_count = count_terms(skills_text, C.NLP_IR_TERMS | C.RECENT_LLM_ONLY)
    nontech = 1.0 if contains_any(title, C.NONTECH_TITLE_TERMS) else 0.0
    tech_title = 1.0 if contains_any(title, C.TECH_TITLE_TERMS) else 0.0
    built_hits = built_system_hits(text)
    hands_on, hands_on_months = hands_on_recency(record)
    terms_total = max(1, len((record.get("skills") or [])) + len(text.split()) / 80)
    core_hits = count_terms(text + " " + skills_text, C.CORE_MUST_HAVE)
    nlp_hits = count_terms(text + " " + skills_text, C.NLP_IR_TERMS)
    cv_hits = count_terms(text + " " + skills_text, C.CV_SPEECH_ROBOTICS)
    pre_llm = 0
    for role in record.get("career_history") or []:
        start = parse_date(role.get("start_date"))
        if start and start.year < 2022 and contains_any(role.get("description", ""), C.SYSTEM_TERMS):
            pre_llm += 1
    assess = claim_assessment(record.get("skills") or [], sig.get("skill_assessment_scores") or {})
    avail = availability_coeff(sig)
    ch = channel_corro(sig)
    flags = consistency_flags(record)
    prod = product_ratio(record)
    svc_only = services_only(record)
    cv_pen = bounded(cv_hits / max(1, nlp_hits + cv_hits))
    recent_llm_only = 1.0 if count_terms(text, C.RECENT_LLM_ONLY) >= 2 and pre_llm == 0 and built_hits == 0 else 0.0
    stuffer = 1.0 if nontech and ai_skill_count >= 4 else 0.0
    notice = float(sig.get("notice_period_days", 90) or 90)
    f: dict[str, float | str] = {
        "candidate_id": record.get("candidate_id", ""),
        "current_title": profile.get("current_title", ""),
        "current_company": profile.get("current_company", ""),
        "location": profile.get("location", ""),
        "yoe": yoe,
        "yoe_band_fit": triangular_yoe(yoe),
        "tech_title": tech_title,
        "nontech": nontech,
        "core_skill_score": bounded(core_hits / 12.0),
        "nlp_ir_affinity": bounded(nlp_hits / terms_total),
        "built_system_hits": float(built_hits),
        "built_system_score": bounded(built_hits / 5.0),
        "eval_score": bounded(count_terms(text, {"ndcg", "mrr", "map", "a/b", "ab test", "evaluation", "offline benchmark"}) / 4.0),
        "vector_score": bounded(count_terms(text, {"embedding", "embeddings", "vector", "faiss", "milvus", "qdrant", "pinecone", "weaviate", "opensearch", "elasticsearch"}) / 5.0),
        "pre_llm_ranking_evidence": bounded(pre_llm / 2.0),
        "product_ratio": prod,
        "services_only": svc_only,
        "hands_on": hands_on,
        "hands_on_months": hands_on_months,
        "metric_density": bounded(metric_density(text) / 2.0),
        "tool_density": bounded(term_density(text, C.TECH_LEXICON) / 5.0),
        "geo_fit": 1.0 if contains_any(profile.get("location", ""), C.TARGET_CITIES) or sig.get("willing_to_relocate") else 0.0,
        "avail_coeff": avail,
        "response_rate": bounded(float(sig.get("recruiter_response_rate", 0) or 0)),
        "interview_completion": bounded(float(sig.get("interview_completion_rate", 0) or 0)),
        "channel_corro": ch,
        "title_chaser": title_chaser(record),
        "cv_speech_penalty": cv_pen,
        "recent_llm_only": recent_llm_only,
        "stuffer_flag": stuffer,
        "notice_penalty": bounded((notice - 30.0) / 150.0),
        "manager_drift": 1.0 if contains_any(title, {"manager", "architect", "director", "head"}) and hands_on < 0.45 else 0.0,
        "consistency_flags": float(flags),
        "education": education_signal(record),
        **assess,
    }
    return f


def raw_score(f: dict[str, float | str]) -> float:
    w = C.WEIGHTS
    score = 0.0
    for key, weight in w.items():
        feature_key = key.removesuffix("_penalty")
        score += weight * float(f.get(feature_key, 0.0) or 0.0)
    score += min(10.0, float(f.get("built_system_hits", 0.0) or 0.0) * 1.2)
    score += min(4.0, float(f.get("n_verified", 0.0) or 0.0) * 0.8)
    score -= min(5.0, float(f.get("n_inflated", 0.0) or 0.0) * 0.6)
    return score
