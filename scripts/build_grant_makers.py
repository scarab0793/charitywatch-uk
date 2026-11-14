#!/usr/bin/env python3
"""Publish grant-making *totals* reported in Charity Commission Part B.

This is NOT a grantee directory. Part B contains institutional grant spend,
not the receiving organisations. The output is designed to avoid implying
unsupported organisation-to-organisation money transfers.
"""
from pathlib import Path
import datetime
import json
import sys

root = Path("data")
manifest = json.loads((root / "manifest-ew.json").read_text(encoding="utf-8"))
if manifest.get("annual_return_part_b_records", 0) < 10000:
    raise SystemExit("Part B dataset not published")

entries = {}
with_amount = 0
for file in sorted((root / "ew").glob("*.json")):
    for item in json.loads(file.read_text(encoding="utf-8")):
        p = item.get("annual_return_part_b")
        if not isinstance(p, dict):
            continue
        amount = p.get("expenditure_grants_institution")
        if not isinstance(amount, (int, float)) or isinstance(amount, bool) or not 0 < amount < 1e14:
            continue
        reg = str(item.get("number", "")).strip()
        name = item.get("name")
        period = p.get("period_end")
        if not reg or not isinstance(name, str) or not name or not isinstance(period,str):
            continue
        record = {
            "number": reg, "name": name, "region": "ew",
            "period_end": period,
            "grants_to_institutions": amount,
            "total_expenditure": p.get("expenditure_total") if isinstance(p.get("expenditure_total"),(int,float)) else None,
            "source": "CCEW annual return Part B"
        }
        prior = entries.get(reg)
        if prior is None or record["period_end"] > prior["period_end"]:
            entries[reg] = record

if len(entries) < 200:
    raise SystemExit("Grant-making records unexpectedly sparse")

records = sorted(entries.values(), key=lambda r: (-r["grants_to_institutions"], r["number"]))
for row in records:
    if row["grants_to_institutions"] <= 0:
        raise SystemExit("Bad grant amount")
target = root / "grant-makers-ew.json"
target.write_text(json.dumps({
    "source": "CCEW annual return Part B: expenditure_grants_institution",
    "scope": "Reported expenditure on grants to institutions; no recipients are identified by this dataset.",
    "updated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "record_count": len(records),
    "records": records
}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
metadata = {
    "source": "CCEW annual return Part B",
    "field": "expenditure_grants_institution",
    "record_count": len(records),
    "total_reported_across_distinct_periods": sum(r["grants_to_institutions"] for r in records),
    "most_recent_period_end": max(r["period_end"] for r in records),
    "earliest_period_end": min(r["period_end"] for r in records),
    "year_end_counts": {},
    "updated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "caution": "Do not treat the combined total as a single-year statistic. Dates differ and grants may flow between charities; recipients are not listed."
}
for item in records:
    year = item["period_end"][:4]
    metadata["year_end_counts"][year] = metadata["year_end_counts"].get(year, 0) + 1
(root / "grant-makers-meta-ew.json").write_text(
    json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
print("Published", len(records), "charities reporting positive institutional grants")
print("Reporting period end years:", sorted(metadata["year_end_counts"].items()))

