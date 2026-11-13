#!/usr/bin/env python3
"""Produce small, separately loadable Charity Commission Part A pay disclosures.

This avoids rewriting hundreds of thousands of full charity records. Only
official disclosed employee pay bands and their reporting dates are exported.
No estimate of named CEO remuneration is made.
"""
import argparse
import csv
import datetime
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(100000000)
BANDS = (
    "60001_70000", "70001_80000", "80001_90000",
    "90001_100000", "100001_110000", "110001_120000",
    "120001_130000", "130001_140000", "140001_150000",
    "150001_200000", "200001_250000", "250001_300000",
    "300001_350000", "350001_400000", "400001_450000",
    "450001_500000", "over_500000",
)


def date(value):
    value = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def count(value):
    text = str(value or "").replace(",", "").strip()
    if not text:
        return None
    try:
        numeric = float(text)
        return int(numeric) if numeric.is_integer() and 0 <= numeric < 10000000 else None
    except ValueError:
        return None


def run(archive, root):
    manifest_path = root / "manifest-ew.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("count", 0) < 100000:
        raise ValueError("Official charity directory must be imported first")
    # Restrict processing to registration numbers already published on the site.
    # Keep only the latest and the matching financial period, not every
    # historical filing: this avoids a potentially huge by_period dictionary.
    requested = {}
    for shard in sorted((root / "ew").glob("*.json")):
        for record in json.loads(shard.read_text(encoding="utf-8")):
            reg = str(record.get("number") or "")
            if reg:
                requested[reg] = record.get("year")
    if len(requested) < 100000:
        raise ValueError("Too few registered charities in the published name shards")
    latest = {}
    exact = {}
    rows = 0
    with zipfile.ZipFile(archive) as z:
        names = [name for name in z.namelist() if name.lower().endswith(".txt")]
        if len(names) != 1:
            raise ValueError("Expected one official Part A TXT file")
        with z.open(names[0]) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline="", errors="replace"), delimiter="\t")
            required = {"registered_charity_number", "fin_period_end_date", "count_salary_band_60001_70000", "count_salary_band_over_500000"}
            if not required.issubset(reader.fieldnames or []):
                raise ValueError("Unexpected official Part A salary schema")
            for row in reader:
                rows += 1
                reg = (row.get("registered_charity_number") or "").strip()
                if reg not in requested:
                    continue
                ending = date(row.get("fin_period_end_date"))
                if not ending:
                    continue
                # The same charity can have many historical Part A returns.
                # Retain the latest record and an exact financial-period match.
                is_latest = reg not in latest or ending > latest[reg][0]
                is_exact = requested[reg] == ending
                if not is_latest and not is_exact:
                    continue
                values = [count(row.get("count_salary_band_" + band)) for band in BANDS]
                item = (ending, values)
                if is_exact:
                    exact[reg] = item
                if is_latest:
                    latest[reg] = item
    if len(latest) < 10000:
        raise ValueError("Too few official Part A rows, refusing publication")
    buckets = defaultdict(list)
    matched = 0
    reporting = 0
    aligned = len(exact)
    total = 0
    for reg in requested:
        entry = exact.get(reg) or latest.get(reg)
        if not entry:
            continue
        ending, values = entry
        matched += 1
        bands = dict(zip(BANDS, values))
        buckets[(reg.lower() + "__")[:2]].append(
            {"number": reg, "period_end": ending, "salary_bands": bands}
        )
        if any(isinstance(v, int) for v in values):
            reporting += 1
            total += sum(v for v in values if isinstance(v, int))
    if matched < 10000 or aligned < 1000:
        raise ValueError("Too few linked official pay disclosures")
    output = root / "pay" / "ew"
    output.mkdir(parents=True, exist_ok=True)
    for path in output.glob("*.json"):
        path.unlink()
    for shard, entries in buckets.items():
        (output / (shard + ".json")).write_text(
            json.dumps(entries, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
    manifest.update({
        "annual_return_part_a_records": matched,
        "annual_return_part_a_aligned_periods": aligned,
        "salary_band_reporting_charities": reporting,
        "salary_band_reported_employees_over_60k": total,
        "salary_shards": sorted(buckets),
        "salary_storage": "separate_shards_v1",
        "annual_return_part_a_source": "CCEW publicextract.charity_annual_return_parta.zip",
        "annual_return_part_a_updated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    })
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Part A rows: {rows}; charity matches: {matched}; reporting salary bands: {reporting}; exact period matches: {aligned}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--output", default="data", type=Path)
    args = parser.parse_args()
    run(args.zip, args.output)
