#!/usr/bin/env python3
"""Dependency-free local browser sandbox for ARGUS.

This is intentionally stdlib-only so it runs locally before the hosted
HuggingFace Space is prepared.
"""

from __future__ import annotations

import argparse
import html
import sys
import uuid
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from argus.export import write_csv, write_xlsx
from rank import rank_candidates

OUTPUT_ROOT = ROOT / "sandbox_outputs"
SAMPLE_PATH = ROOT / "sample_candidates.json"
ALLOWED_SUFFIXES = {
    ".csv",
    ".json",
    ".jsonl",
    ".ndjson",
    ".gz",
}


def page(title: str, body: str) -> bytes:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: #f6f7f9; color: #17202a; }}
    main {{ max-width: 1040px; margin: 0 auto; padding: 32px 20px 56px; }}
    h1 {{ margin: 0 0 8px; font-size: 30px; line-height: 1.15; }}
    p {{ color: #4b5563; line-height: 1.55; }}
    form, .panel {{ background: #fff; border: 1px solid #d9dee7; border-radius: 8px; padding: 18px; box-shadow: 0 1px 2px rgba(16,24,40,.04); }}
    label {{ display: block; font-weight: 650; margin: 14px 0 6px; }}
    input[type=file], input[type=number] {{ width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #cfd6e1; border-radius: 6px; background: #fff; }}
    input[type=checkbox] {{ margin-right: 8px; }}
    button, .button {{ display: inline-block; border: 0; border-radius: 6px; background: #1f6feb; color: white; padding: 10px 14px; font-weight: 700; text-decoration: none; cursor: pointer; }}
    .button.secondary {{ background: #374151; }}
    .row {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-top: 16px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; background: white; border: 1px solid #d9dee7; }}
    th, td {{ border-bottom: 1px solid #e5e7eb; padding: 9px 10px; text-align: left; vertical-align: top; font-size: 14px; }}
    th {{ background: #eef2f7; }}
    code {{ background: #eef2f7; padding: 2px 5px; border-radius: 4px; }}
    .error {{ border-color: #fecaca; background: #fff7f7; color: #991b1b; }}
  </style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>""".encode("utf-8")


def home() -> bytes:
    return page(
        "ARGUS Sandbox",
        """<h1>ARGUS Candidate Ranker</h1>
<p>Upload a candidate file and run the same offline ranking path used by <code>rank.py</code>.
Supported formats: CSV, JSON, JSONL/NDJSON, and gzipped variants.</p>
<form method="post" action="/rank" enctype="multipart/form-data">
  <label for="candidate_file">Candidate file</label>
  <input id="candidate_file" name="candidate_file" type="file">
  <label for="top_n">Top N</label>
  <input id="top_n" name="top_n" type="number" min="1" max="1000" value="50">
  <label><input name="use_sample" type="checkbox" value="1">Use bundled sample if no file is uploaded</label>
  <div class="row">
    <button type="submit">Run Ranking</button>
    <a class="button secondary" href="/health">Health Check</a>
  </div>
</form>""",
    )


def safe_suffix(filename: str) -> str:
    suffixes = "".join(Path(filename).suffixes).lower()
    if suffixes.endswith(".jsonl.gz"):
        return ".jsonl.gz"
    if suffixes.endswith(".ndjson.gz"):
        return ".ndjson.gz"
    if suffixes.endswith(".json.gz"):
        return ".json.gz"
    if suffixes.endswith(".csv.gz"):
        return ".csv.gz"
    suffix = Path(filename).suffix.lower()
    return suffix if suffix in ALLOWED_SUFFIXES else ".json"


def render_results(run_id: str, rows: list[dict]) -> bytes:
    preview = "\n".join(
        "<tr>"
        f"<td>{html.escape(str(r['rank']))}</td>"
        f"<td>{html.escape(str(r['candidate_id']))}</td>"
        f"<td>{html.escape(str(r['score']))}</td>"
        f"<td>{html.escape(str(r['reasoning']))}</td>"
        "</tr>"
        for r in rows[:20]
    )
    return page(
        "ARGUS Results",
        f"""<h1>Ranking Complete</h1>
<p>Generated {len(rows)} ranked row(s). Previewing the first {min(20, len(rows))}.</p>
<div class="row">
  <a class="button" href="/download/{run_id}/ranked.csv">Download CSV</a>
  <a class="button" href="/download/{run_id}/ranked.xlsx">Download XLSX</a>
  <a class="button secondary" href="/">Run Another File</a>
</div>
<table>
  <thead><tr><th>Rank</th><th>Candidate ID</th><th>Score</th><th>Reasoning</th></tr></thead>
  <tbody>{preview}</tbody>
</table>""",
    )


def render_error(message: str) -> bytes:
    return page(
        "ARGUS Error",
        f"""<h1>Could not rank candidates</h1>
<div class="panel error"><p>{html.escape(message)}</p></div>
<p><a class="button secondary" href="/">Back</a></p>""",
    )


class SandboxHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            self.send_html(home())
            return
        if self.path == "/health":
            self.send_text("ok\n")
            return
        if self.path.startswith("/download/"):
            self.send_download()
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/rank":
            self.send_error(404)
            return
        try:
            self.handle_rank()
        except Exception as exc:  # keep sandbox user-facing instead of crashing server
            self.send_html(render_error(str(exc)), status=400)

    def handle_rank(self) -> None:
        form, files = self.parse_multipart()
        top_n = int((form.get("top_n") or "50").strip())
        top_n = max(1, min(1000, top_n))
        use_sample = form.get("use_sample") == "1"
        run_id = uuid.uuid4().hex[:12]
        run_dir = OUTPUT_ROOT / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        upload = files.get("candidate_file")
        if upload and upload["filename"]:
            suffix = safe_suffix(upload["filename"])
            input_path = run_dir / f"input{suffix}"
            with open(input_path, "wb") as out:
                out.write(upload["content"])
        elif use_sample:
            input_path = SAMPLE_PATH
        else:
            raise ValueError("Upload a candidate file or select the bundled sample checkbox.")

        rows = rank_candidates(input_path, top_n=top_n)
        csv_path = run_dir / "ranked.csv"
        xlsx_path = run_dir / "ranked.xlsx"
        write_csv(rows, csv_path)
        write_xlsx(rows, xlsx_path)
        self.send_html(render_results(run_id, rows))

    def parse_multipart(self) -> tuple[dict[str, str], dict[str, dict]]:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            raise ValueError("Expected multipart form upload.")
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        raw = (
            f"Content-Type: {content_type}\r\n"
            "MIME-Version: 1.0\r\n\r\n"
        ).encode("utf-8") + body
        message = BytesParser(policy=default).parsebytes(raw)
        fields: dict[str, str] = {}
        files: dict[str, dict] = {}
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if not name:
                continue
            filename = part.get_filename()
            content = part.get_payload(decode=True) or b""
            if filename:
                files[name] = {"filename": filename, "content": content}
            else:
                fields[name] = content.decode(part.get_content_charset() or "utf-8", errors="replace")
        return fields, files

    def send_download(self) -> None:
        parts = [unquote(p) for p in self.path.split("/") if p]
        if len(parts) != 3:
            self.send_error(404)
            return
        _, run_id, filename = parts
        if filename not in {"ranked.csv", "ranked.xlsx"}:
            self.send_error(404)
            return
        path = OUTPUT_ROOT / run_id / filename
        if not path.exists():
            self.send_error(404)
            return
        content_type = "text/csv" if filename.endswith(".csv") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_html(self, body: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    OUTPUT_ROOT.mkdir(exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), SandboxHandler)
    print(f"ARGUS sandbox running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
