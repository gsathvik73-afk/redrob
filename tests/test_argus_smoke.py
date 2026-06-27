from argus.features import availability_coeff, extract_features
from argus.reasoning import reasoning_for


def test_availability_floor():
    assert availability_coeff({}) >= 0.05


def test_feature_reasoning_smoke():
    rec = {
        "candidate_id": "CAND_9999999",
        "profile": {
            "current_title": "Senior ML Engineer",
            "current_company": "ProductCo",
            "summary": "Built vector search and ranking evaluation with NDCG.",
            "location": "Pune",
            "years_of_experience": 7,
        },
        "career_history": [
            {
                "company": "ProductCo",
                "title": "Senior ML Engineer",
                "start_date": "2020-01-01",
                "end_date": None,
                "duration_months": 78,
                "industry": "SaaS",
                "description": "Shipped retrieval ranking system with embeddings and A/B evaluation.",
            }
        ],
        "skills": [{"name": "Python", "proficiency": "advanced", "endorsements": 1, "duration_months": 60}],
        "education": [],
        "redrob_signals": {"last_active_date": "2026-06-01", "open_to_work_flag": True},
    }
    f = extract_features(rec)
    assert f["yoe_band_fit"] == 1.0
    assert f["built_system_hits"] > 0
    assert "7.0y experience" in reasoning_for(f, 1)

