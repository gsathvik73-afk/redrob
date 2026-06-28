# ARGUS Portable Candidate Ranker

Deterministic, offline candidate ranker for the Redrob Senior AI Engineer challenge.
It still reproduces the Redrob submission, but the input layer now accepts
different candidate datasets as long as they provide broadly recognizable
candidate fields.

## Redrob Reproduce

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv --validate-redrob
python validate_submission.py ./submission.csv
```

The rank command scans the JSONL once, computes JD-specific feature, trust, availability,
and anomaly signals, then writes both `submission.csv` and `submission.xlsx`.

## Generic Inputs

```bash
python rank.py --candidates ./my_candidates.csv --out ./ranked.csv --top-n 50
python rank.py --candidates ./my_candidates.json --out ./ranked.csv --top-n 100
python rank.py --candidates ./my_candidates.jsonl.gz --out ./ranked.csv --top-n 100
```

Supported input formats:

- `.jsonl` / `.ndjson`, optionally `.gz`
- `.json`, either a list, one record, or an object with `candidates`, `records`, or `data`
- `.csv`, optionally `.gz`

For non-Redrob data, the loader maps common field names into the internal schema:

- IDs: `candidate_id`, `id`, `candidateId`
- Profile: `name`, `full_name`, `headline`, `summary`, `bio`, `description`, `resume_text`
- Role: `current_title`, `title`, `job_title`, `role`
- Company/industry: `current_company`, `company`, `employer`, `industry`
- Experience/location: `years_of_experience`, `yoe`, `experience`, `location`, `city`, `country`
- Skills: `skills`, `skill_names`, `technologies`, `tech_stack`
- Signals, when present: `last_active_date`, `open_to_work_flag`, `recruiter_response_rate`,
  `interview_completion_rate`, `notice_period_days`, `willing_to_relocate`

Generic runs skip the strict Redrob validator by default because external datasets may
not use `CAND_XXXXXXX` IDs or exactly 100 rows. Add `--validate-redrob` only when
producing an official Redrob submission.

## Method

The scorer rewards candidates with hands-on production evidence for search, retrieval,
ranking, recommendation, vector infrastructure, and evaluation systems. It down-weights
services-only histories, nontechnical keyword stuffing, stale platform activity,
CV/speech-heavy profiles without NLP/IR evidence, title-chasing, long notice periods,
and honeypot-like consistency failures.

No hosted LLM APIs, GPU runtime, network calls, or candidate-specific manual edits are
used by the ranking step.

## Small Sandbox

Browser app:

```bash
python sandbox/app.py --host 127.0.0.1 --port 7860
```

Then open:

```text
http://127.0.0.1:7860
```

The browser sandbox accepts uploaded CSV/JSON/JSONL/NDJSON files and returns
downloadable CSV/XLSX rankings. It has no hosted-LLM or network dependency.

CLI sample runner:

```bash
python sandbox/run_sample.py --candidates ./sample_candidates.json --out ./sandbox_submission.csv --top-n 50
```

This runs the same rank path on the included sample candidate file.

## Make Targets

```bash
make rank          # full Redrob run + strict validation
make validate      # validate submission.csv
make sandbox-local # start local browser sandbox on 127.0.0.1:7860
make audit         # compile and smoke-test generic input + current submission
```
