# ARGUS Local Sandbox

Run a local browser sandbox before deploying to HuggingFace:

```bash
python sandbox/app.py --host 127.0.0.1 --port 7860
```

Then open:

```text
http://127.0.0.1:7860
```

The app accepts `.csv`, `.json`, `.jsonl`, `.ndjson`, and gzipped variants. It
uses the same `rank_candidates()` path as `rank.py`, then provides CSV/XLSX
downloads. If no file is uploaded, use the sample checkbox to rank
`sample_candidates.json`.

For HuggingFace Spaces, this can be wrapped in Gradio later; the ranking logic
does not need to change.
