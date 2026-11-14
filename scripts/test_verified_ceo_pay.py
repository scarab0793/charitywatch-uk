#!/usr/bin/env python3
"""Validate evidence references and differing CEO remuneration bases."""
import datetime
import json
import math
import re
from pathlib import Path
from urllib.parse import urlsplit

source = json.loads(Path("data/verified-ceo-pay.json").read_text(encoding="utf-8"))
records = source["records"]
allowed = {"gross_pay", "emoluments", "salary_benefits_employer_ni"}
assert isinstance(records, dict) and records, "Missing verified CEO records"
for key, charity in records.items():
    assert re.fullmatch(r"(ew|sc|ni):[0-9]{4,9}", key), key
    assert charity.get("basis_category") in allowed, key
    assert isinstance(charity.get("measure"), str) and charity["measure"].strip(), key
    assert charity.get("currency") == "GBP", key
    periods = charity.get("periods")
    assert isinstance(periods, list) and periods, key
    seen = set()
    for record in periods:
        date = record.get("period_end")
        datetime.date.fromisoformat(date)
        assert date not in seen, (key, date)
        seen.add(date)
        assert type(record.get("amount")) in (int, float) and math.isfinite(record["amount"]) and 0 <= record["amount"] < 10_000_000, key
        url = urlsplit(record.get("source_url", ""))
        assert url.scheme == "https" and url.hostname and not url.username and not url.password, key
        assert isinstance(record.get("source_label"), str) and record["source_label"].strip(), key
        if "page" in record:
            assert type(record["page"]) is int and record["page"] >= 1, key
print(f"PASS: {len(records)} sourced CEO remuneration records have explicit pay definitions")
