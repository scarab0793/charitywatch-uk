#!/usr/bin/env python3
"""Choose a bounded sample of grant makers and periodically retry prior 404s.

A 404 is not proof that a charity never awards grants. We prioritise fresh
candidates to improve coverage while reserving one slot for a previous 404.
"""
import datetime
import json
import re
from pathlib import Path

CORE_ORG_IDS = ("GB-CHC-802052", "GB-CHC-202918", "GB-CHC-288701")
MAX_ORGS = 12


def previous_404s(manifest_path):
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = manifest.get("organisations", {})
        if not isinstance(entries, dict):
            return []
        stored = manifest.get("unavailable_organisations", [])
        failed = {org for org in stored if isinstance(org, str) and re.fullmatch(r"GB-CHC-[0-9]{4,9}", org)} if isinstance(stored, list) else set()
        for key, value in entries.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                continue
            match = re.fullmatch(r"(GB-CHC-[0-9]{4,9}):(made|received)", key)
            if match and value.get("updated") is False and "HTTP Error 404" in str(value.get("error", "")):
                failed.add(match.group(1))
        return sorted(failed)
    except (OSError, ValueError, TypeError, AttributeError):
        return []


def select_organisations(source=Path("data/grant-makers-ew.json"), limit=MAX_ORGS,
                         previous_manifest=Path("data/360giving/manifest.json"),
                         retry_index=None):
    if not isinstance(limit, int) or isinstance(limit, bool) or not len(CORE_ORG_IDS) <= limit <= MAX_ORGS:
        raise ValueError("Selection limit must include core profiles and stay within MAX_ORGS")
    selected = list(CORE_ORG_IDS)
    excluded = [org for org in previous_404s(previous_manifest) if org not in CORE_ORG_IDS]
    # Deterministic within each week and rotating across weeks.
    if retry_index is None:
        retry_index = datetime.date.today().toordinal() // 7
    if not isinstance(retry_index, int) or isinstance(retry_index, bool):
        raise ValueError("Invalid retry rotation")
    retry = excluded[retry_index % len(excluded)] if excluded else None
    reserve = 1 if retry and limit > len(CORE_ORG_IDS) else 0
    try:
        source_data = json.loads(source.read_text(encoding="utf-8"))
        rows = source_data.get("records", [])
        if not isinstance(rows, list):
            raise ValueError("Official grant data has no records array")
        rows = sorted(
            (row for row in rows if isinstance(row, dict)),
            key=lambda row: row.get("grants_to_institutions")
            if type(row.get("grants_to_institutions")) in (int, float) else 0,
            reverse=True,
        )
        for row in rows:
            number = str(row.get("number") or "")
            if not re.fullmatch(r"[0-9]{4,9}", number):
                continue
            org = "GB-CHC-" + number
            if org not in selected and org not in excluded:
                selected.append(org)
            if len(selected) >= limit - reserve:
                break
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print("Additional 360Giving sample selection unavailable; keeping core set:", exc)
    if retry and len(selected) < limit and retry not in selected:
        selected.append(retry)
    return selected
