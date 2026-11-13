#!/usr/bin/env python3
"""Validate manually verified chief executive pay disclosures before publishing.

Records must come with a real primary-source URL and a named accounting
period. This script never scrapes or guesses amounts from salary bands.
"""
import datetime
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

APPROVED_HOST_SUFFIXES = (
    "charitycommission.gov.uk",
    "bbcchildreninneed.co.uk",
    "oxfam.org.uk",
    "wateraid.org",
)
FILE = Path(__file__).resolve().parents[1] / "data" / "verified-ceo-pay.json"


def valid_source(url):
    if not isinstance(url, str):
        return False
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    return (
        parsed.scheme == "https"
        and parsed.username is None and parsed.password is None
        and bool(parsed.path)
        and any(host == suffix or host.endswith("." + suffix)
                for suffix in APPROVED_HOST_SUFFIXES)
    )


def validate(data):
    errors = []
    if not isinstance(data.get("records"), dict):
        return ["records must be a mapping"]
    for key, record in data["records"].items():
        if not re.fullmatch(r"(ew|sc|ni):[A-Za-z0-9]{3,20}", key):
            errors.append(f"{key}: invalid charity key")
        if not isinstance(record, dict):
            errors.append(f"{key}: invalid entry")
            continue
        if record.get("currency") != "GBP":
            errors.append(f"{key}: currency must be GBP")
        if not isinstance(record.get("measure"), str) or not record["measure"].strip():
            errors.append(f"{key}: missing pay definition")
        periods = record.get("periods")
        if not isinstance(periods, list) or not periods:
            errors.append(f"{key}: no reporting periods")
            continue
        seen = set()
        for item in periods:
            period = item.get("period_end", "")
            try:
                dt = datetime.date.fromisoformat(period)
                if dt > datetime.date.today():
                    errors.append(f"{key}: financial period in the future: {period}")
            except (TypeError, ValueError):
                errors.append(f"{key}: invalid period {period!r}")
            if period in seen:
                errors.append(f"{key}: duplicate period {period}")
            seen.add(period)
            amount = item.get("amount")
            if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not 0 < amount < 10000000:
                errors.append(f"{key}: invalid disclosed pay amount in {period}")
            if not valid_source(item.get("source_url")):
                errors.append(f"{key}: unapproved or invalid primary source in {period}")
            if not item.get("source_label"):
                errors.append(f"{key}: missing source label for {period}")
    return errors


def main():
    data = json.loads(FILE.read_text(encoding="utf-8"))
    errors = validate(data)
    if errors:
        print("\n".join("ERROR: " + e for e in errors), file=sys.stderr)
        return 1
    print("Verified CEO pay catalogue checked:", len(data["records"]), "charities,",
          sum(len(r["periods"]) for r in data["records"].values()), "periods")
    return 0


if __name__ == "__main__":
    sys.exit(main())
