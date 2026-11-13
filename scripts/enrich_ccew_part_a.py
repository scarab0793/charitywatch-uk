#!/usr/bin/env python3
"""Join verified CCEW annual return Part A fields to the imported EW directory.

Source: official publicextract.charity_annual_return_parta.zip.
Do not interpret salary bands as CEO remuneration, government grant income as
grants paid, or trustee payment flags as monetary amounts.
"""
import argparse
import csv
import datetime
import io
import json
import re
import zipfile
from pathlib import Path

csv.field_size_limit(100000000)

SALARY_BANDS = [
    "60001_70000", "70001_80000", "80001_90000", "90001_100000",
    "100001_110000", "110001_120000", "120001_130000",
    "130001_140000", "140001_150000", "150001_200000",
    "200001_250000", "250001_300000", "300001_350000",
    "350001_400000", "400001_450000", "450001_500000",
    "over_500000"
]
FLAGS = (
    "grant_making_is_main_activity",
    "charity_receives_govt_funding_contracts",
    "charity_receives_govt_funding_grants",
    "does_trustee_receive_any_benefit",
    "trustee_payments_acting_as_trustee",
    "trustee_receives_payments_services",
    "trustee_receives_other_benefit",
)
AMOUNTS = ("income_from_government_contracts", "income_from_government_grants")
COUNTS = ("count_govt_contracts", "count_govt_grants", "count_volunteers")


def parse_date(raw):
    value = str(raw or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    try:
        return datetime.date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def parse_number(raw, integer=False):
    value = str(raw or "").replace(",", "").replace("£", "").strip()
    if not value or value.lower() in {"n/a", "na", "null", "none", "-", "unknown"}:
        return None
    try:
        v = float(value)
        if not (-1e15 < v < 1e15):
            return None
        if integer:
            if not v.is_integer() or v < 0:
                return None
            return int(v)
        return v
    except ValueError:
        return None


def flag(raw):
    value = str(raw or "").strip().lower()
    if value in {"y", "yes", "true", "1"}:
        return True
    if value in {"n", "no", "false", "0"}:
        return False
    return None


def import_details(archive, data_dir):
    manifest_path = data_dir / "manifest-ew.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("count", 0) < 100000:
        raise ValueError("Directory has not been imported or is too small")

    with zipfile.ZipFile(archive) as z:
        tables = [name for name in z.namelist() if name.lower().endswith(".txt")]
        if len(tables) != 1:
            raise ValueError("Expected exactly one Part A table")
        with z.open(tables[0]) as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline="", errors="replace"), delimiter="\t")
            required = {
                "registered_charity_number", "fin_period_end_date",
                "income_from_government_grants", "income_from_government_contracts",
                "count_salary_band_60001_70000", "count_salary_band_over_500000",
            }
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise ValueError("Official Part A schema has changed: " + ", ".join(sorted(missing)))
            by_number = {}
            raw_rows = 0
            for row in reader:
                raw_rows += 1
                number = (row.get("registered_charity_number") or "").strip()
                period = parse_date(row.get("fin_period_end_date"))
                if not number or not period:
                    continue
                details = {"period_end": period}
                for column in AMOUNTS:
                    details[column] = parse_number(row.get(column))
                for column in COUNTS:
                    details[column] = parse_number(row.get(column), integer=True)
                details["salary_bands"] = {
                    band: parse_number(row.get("count_salary_band_" + band), integer=True)
                    for band in SALARY_BANDS
                }
                for column in FLAGS:
                    details[column] = flag(row.get(column))
                previous = by_number.get(number)
                if previous is None or period > previous["period_end"]:
                    by_number[number] = details

    if len(by_number) < 10000:
        raise ValueError("Unexpectedly few Part A records; declining to write")
    staged = []
    matched_numbers = set()
    for folder in (data_dir / "ew", data_dir / "ew" / "numbers"):
        if not folder.is_dir():
            raise ValueError("Missing imported folder: " + str(folder))
        for path in folder.glob("*.json"):
            records = json.loads(path.read_text(encoding="utf-8"))
            for record in records:
                details = by_number.get(str(record.get("number", "")))
                if details:
                    record["annual_return_part_a"] = details
                    matched_numbers.add(str(record["number"]))
                else:
                    record.pop("annual_return_part_a", None)
            staged.append((path, json.dumps(records, ensure_ascii=False, separators=(",", ":"))))

    if len(matched_numbers) < 10000:
        raise ValueError("Too few linked records; declining to write")
    manifest["annual_return_part_a_records"] = len(matched_numbers)
    manifest["annual_return_part_a_source"] = "CCEW publicextract.charity_annual_return_parta.zip"
    manifest["annual_return_part_a_updated_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for path, content in staged:
        path.write_text(content, encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Part A rows read:", raw_rows)
    print("Part A organisations found:", len(by_number))
    print("Charities successfully linked:", len(matched_numbers))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()
    import_details(args.zip, args.output)
