"""Feature-grounded reasoning strings."""

from __future__ import annotations


def reasoning_for(f: dict, rank: int) -> str:
    title = str(f.get("current_title") or "candidate")
    company = str(f.get("current_company") or "current employer")
    bits = [f"{float(f.get('yoe', 0)):.1f}y experience as {title} at {company}"]
    if float(f.get("built_system_hits", 0)) > 0:
        bits.append("career evidence shows shipped search/ranking/retrieval or matching systems")
    elif float(f.get("core_skill_score", 0)) > 0.5:
        bits.append("skills align with retrieval/ranking infrastructure")
    if float(f.get("product_ratio", 0)) > 0.6:
        bits.append("mostly product-company background")
    elif float(f.get("services_only", 0)):
        bits.append("services-only background is a fit concern")
    if float(f.get("pre_llm_ranking_evidence", 0)) > 0:
        bits.append("has pre-LLM-era ranking/retrieval evidence")
    if float(f.get("eval_score", 0)) > 0:
        bits.append("mentions ranking evaluation or A/B/offline metrics")
    if float(f.get("n_verified", 0)) > 0:
        bits.append(f"assessments verify {int(float(f.get('n_verified', 0)))} claimed skill(s)")
    if float(f.get("n_inflated", 0)) > 0:
        bits.append(f"{int(float(f.get('n_inflated', 0)))} skill claim(s) test below stated level")
    if float(f.get("avail_coeff", 0)) < 0.3:
        bits.append("availability is weak from recent activity/response signals")
    elif float(f.get("avail_coeff", 0)) > 0.65:
        bits.append("recent platform signals suggest reachable")
    if float(f.get("geo_fit", 0)) > 0:
        bits.append("location or relocation fits Pune/Noida-flexible requirement")
    if float(f.get("cv_speech_penalty", 0)) > 0.55:
        bits.append("CV/speech-heavy profile is less central to this NLP/IR role")
    if rank > 75 and not any("concern" in b or "weak" in b or "less central" in b for b in bits):
        bits.append("included as a lower-ranked adjacent fit after stronger system builders")
    out: list[str] = []
    for bit in bits:
        candidate = "; ".join(out + [bit])
        if len(candidate) > 235:
            break
        out.append(bit)
    return "; ".join(out)
