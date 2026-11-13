#!/usr/bin/env python3
"""Join official Charity Commission Annual Return Part B financial disclosures.

Part B components may overlap. Preserve original fields and never sum
charitable expenditure, institutional grants, governance or support costs.
Records are keyed by registered charity number and most recent financial
period end, with identical periods preferred to headline annual figures.
"""
import argparse
import csv
import datetime
import io
import json
import zipfile
from pathlib import Path

csv.field_size_limit(100000000)

MONEY_FIELDS = (
    "income_donations_and_legacies",
    "income_other_trading_activities",
    "income_charitable_activities",
    "income_investments",
    "income_other",
    "income_total_income_and_endowments",
    "expenditure_raising_funds",
    "expenditure_charitable_expenditure",
    "expenditure_other",
    "expenditure_total",
    "expenditure_investment_management",
    "expenditure_grants_institution",
    "expenditure_governance",
    "expenditure_support_costs",
    "expenditure_depreciation",
    "reserves",
    "assets_cash",
    "assets_total_fixed",
    "assets_total_liabilities",
    "funds_unrestricted",
    "funds_restricted",
    "funds_total",
)
COUNT_FIELDS = ("count_employees",)


def date(value):
    value = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    try:
        return datetime.date.fromisoformat(value[:10]).isoformat()
    except ValueError:
        return None


def number(value, integer=False):
    value = str(value or "").strip().replace(",", "").replace("£", "")
    if not value or value.lower() in {"null", "none", "-", "n/a", "na", "unknown"}:
        return None
    try:
        result = float(value)
        if not -1e15 < result < 1e15:
            return None
        if integer:
            return int(result) if result >= 0 and result.is_integer() else None
        return result
    except ValueError:
        return None


def run(archive, data_dir):
    manifest_file = data_dir / "manifest-ew.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("count", 0) < 100000:
        raise ValueError("Missing valid England and Wales charity database")
    with zipfile.ZipFile(archive) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".txt")]
        if len(names) != 1:
            raise ValueError("Expected one official Part B TXT table")
        with z.open(names[0]) as raw:
            reader = csv.DictReader(
                io.TextIOWrapper(raw, encoding="utf-8-sig", errors="replace", newline=""),
                delimiter="\t",
            )
            expected = {
                "registered_charity_number", "fin_period_end_date",
                "expenditure_raising_funds",
                "expenditure_charitable_expenditure",
                "expenditure_grants_institution",
                "expenditure_support_costs",
                "expenditure_governance",
                "expenditure_total",
                "reserves",
            }
            missing = expected - set(reader.fieldnames or [])
            if missing:
                raise ValueError("Unexpected Part B schema: " + ", ".join(sorted(missing)))
            latest = {}
            by_period = {}
            rows = 0
            for record in reader:
                rows += 1
                reg = str(record.get("registered_charity_number") or "").strip()
                period = date(record.get("fin_period_end_date"))
                if not reg or not period:
                    continue
                amounts = {field: number(record.get(field)) for field in MONEY_FIELDS}
                counts = {field: number(record.get(field), integer=True) for field in COUNT_FIELDS}
                if all(v is None for v in amounts.values()):
                    continue
                item = {"period_end": period, **amounts, **counts}
                by_period[(reg, period)] = item
                previous = latest.get(reg)
                if previous is None or period > previous["period_end"]:
                    latest[reg] = item
    if len(latest) < 10000:
        raise ValueError("Too few Part B organisations - refusing publication")
    staged = []
    joined = set()
    aligned = set()
    for folder in (data_dir / "ew", data_dir / "ew" / "numbers"):
        if not folder.is_dir():
            raise ValueError("Missing imported shards folder: " + str(folder))
        for path in folder.glob("*.json"):
            records = json.loads(path.read_text(encoding="utf-8"))
            for record in records:
                reg = str(record.get("number", ""))
                wanted_period = record.get("year")
                partb = by_period.get((reg, wanted_period)) if wanted_period else None
                if partb is None:
                    partb = latest.get(reg)
                if partb:
                    record["annual_return_part_b"] = partb
                    joined.add(reg)
                    if record.get("year") == partb["period_end"]:
                        aligned.add(reg)
                else:
                    record.pop("annual_return_part_b", None)
            staged.append((path, json.dumps(records, ensure_ascii=False, separators=(",", ":"))))
    if len(joined) < 10000 or len(joined) > manifest["count"]:
        raise ValueError("Part B join coverage invalid - refusing publication")
    if len(aligned) < 1000:
        raise ValueError("Too few period-aligned Part B records - refusing publication")
    manifest["annual_return_part_b_records"] = len(joined)
    manifest["annual_return_part_b_aligned_periods"] = len(aligned)
    manifest["annual_return_part_b_source"] = "CCEW publicextract.charity_annual_return_partb.zip"
    manifest["annual_return_part_b_updated_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for path, value in staged:
        path.write_text(value, encoding="utf-8")
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Part B raw rows:", rows)
    print("Part B distinct organisations:", len(latest))
    print("Part B matched charities:", len(joined))
    print("Matching headline financial periods:", len(aligned))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()
    run(args.zip, args.output)
