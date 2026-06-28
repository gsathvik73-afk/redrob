PYTHON ?= python3

.PHONY: rank validate sandbox-local sandbox-sample audit

rank:
	$(PYTHON) rank.py --candidates ./candidates.jsonl --out ./submission.csv --validate-redrob

validate:
	$(PYTHON) validate_submission.py ./submission.csv

sandbox-local:
	$(PYTHON) sandbox/app.py --host 127.0.0.1 --port 7860

sandbox-sample:
	$(PYTHON) sandbox/run_sample.py --candidates ./sample_candidates.json --out ./sandbox_submission.csv --top-n 50

audit:
	$(PYTHON) -m compileall -q argus rank.py build.py sandbox/run_sample.py sandbox/app.py
	$(PYTHON) rank.py --candidates tests/generic_candidates.csv --out /tmp/argus_generic_audit.csv --top-n 3
	$(PYTHON) validate_submission.py ./submission.csv
