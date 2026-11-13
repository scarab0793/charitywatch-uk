#!/usr/bin/env python3
"""Validate the generated pay index against the charity directory and manifest."""
import json
import random
from pathlib import Path
import sys

root = Path("data")
manifest = json.loads((root / "manifest-ew.json").read_text(encoding="utf-8"))
salary_dir = root / "pay" / "ew"
if manifest.get("salary_storage") != "separate_shards_v1":
    raise SystemExit("FAIL: Salary index not published in manifest")
shards = manifest.get("salary_shards", [])
if not shards:
    raise SystemExit("FAIL: No salary shards listed")
seen = set()
positive = 0
with_counts = 0
for prefix in shards:
    path = salary_dir / (prefix + ".json")
    if not path.is_file():
        raise SystemExit("FAIL: Missing pay shard " + prefix)
    items = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(items, list):
        raise SystemExit("FAIL: Invalid shard " + prefix)
    for row in items:
        number = str(row.get("number", ""))
        if not number or (number.lower() + "__")[:2] != prefix:
            raise SystemExit("FAIL: Wrong shard assignment " + number)
        if number in seen:
            raise SystemExit("FAIL: Duplicate charity " + number)
        seen.add(number)
        bands = row.get("salary_bands")
        if not isinstance(bands, dict) or len(bands) != 17:
            raise SystemExit("FAIL: Invalid pay bands " + number)
        counts = [n for n in bands.values() if isinstance(n, int) and not isinstance(n, bool)]
        if any(n < 0 for n in counts):
            raise SystemExit("FAIL: Negative employee count " + number)
        if counts:
            with_counts += 1
            positive += sum(counts)
if len(seen) != manifest["annual_return_part_a_records"]:
    raise SystemExit("FAIL: Pay shard coverage mismatch")
if with_counts != manifest["salary_band_reporting_charities"]:
    raise SystemExit("FAIL: Salary disclosure count mismatch")
if positive != manifest["salary_band_reported_employees_over_60k"]:
    raise SystemExit("FAIL: Total above-60k employees mismatch")
if not 1000 <= len(seen) <= manifest["count"]:
    raise SystemExit("FAIL: Implausible pay coverage")
print(f"PASS: {len(seen):,} charities linked, {with_counts:,} report salary bands, {positive:,} banded employees")
