"""CSV/XLSX export helpers."""

from __future__ import annotations

import csv
from pathlib import Path


HEADER = ["candidate_id", "rank", "score", "reasoning"]


def write_csv(rows: list[dict], path: str | Path) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in HEADER})


def write_xlsx(rows: list[dict], path: str | Path) -> None:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ranked Candidates"
    ws.append(HEADER)
    for row in rows:
        ws.append([row["candidate_id"], row["rank"], round(float(row["score"]), 6), row["reasoning"]])
    for col, width in {"A": 16, "B": 6, "C": 10, "D": 90}.items():
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(path)

