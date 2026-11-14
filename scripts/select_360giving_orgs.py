#!/usr/bin/env python3
"""Deterministically select a small sample of official institutional grantmakers.

This is not a list of charities guaranteed to publish 360Giving grants.
"""
import json
import re
from pathlib import Path

CORE_ORG_IDS = ("GB-CHC-802052", "GB-CHC-202918", "GB-CHC-288701")
MAX_ORGS = 12


def select_organisations(source=Path("data/grant-makers-ew.json"), limit=MAX_ORGS):
    if limit < len(CORE_ORG_IDS):
        raise ValueError("The cache limit cannot omit core charity profiles")
    selected = list(CORE_ORG_IDS)
    try:
        source_data = json.loads(source.read_text(encoding="utf-8"))
        rows = source_data.get("records", [])
        if not isinstance(rows, list):
            raise ValueError("Official grant data has no records array")
        rows = sorted(
            (row for row in rows if isinstance(row, dict)),
            key=lambda row: row.get("grants_to_institutions")
            if isinstance(row.get("grants_to_institutions"), (int, float))
            and not isinstance(row.get("grants_to_institutions"), bool) else 0,
            reverse=True,
        )
        for row in rows:
            number = str(row.get("number") or "")
            if not re.fullmatch(r"[0-9]{4,9}", number):
                continue
            org = "GB-CHC-" + number
            if org not in selected:
                selected.append(org)
            if len(selected) >= limit:
                break
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print("Additional 360Giving sample selection unavailable; keeping core set:", exc)
    return selected
