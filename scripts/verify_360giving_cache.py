#!/usr/bin/env python3
"""Validate 360Giving cached award snapshots before publishing.

Only successfully refreshed directions must match the new manifest. Failed
requests preserve older snapshots and are reported as unavailable/partial.
These are published awards, not proof of disbursements.
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path


def validate(root):
    errors = []
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    entries = manifest.get("organisations")
    limit = manifest.get("max_records_per_org_direction")
    if not isinstance(entries, dict) or not entries:
        return ["Manifest has no organisation directions"]
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1 or limit > 100:
        errors.append("Unsafe record cap")
        limit = 40
    selected = manifest.get("selected_organisations")
    if selected is not None:
        if not isinstance(selected, list) or not 1 <= len(selected) <= 12 or len(selected) != len(set(selected)):
            errors.append("Invalid selected organisation list")
        elif set(entries) != {org + ":" + direction for org in selected for direction in ("made", "received")}:
            errors.append("Manifest direction keys do not match selected organisations")
    successes = 0
    for key, detail in entries.items():
        match = re.fullmatch(r"(GB-CHC-[0-9]{4,9}):(made|received)", key)
        if not match or not isinstance(detail, dict):
            errors.append("Malformed organisation-direction entry: " + str(key))
            continue
        org, direction = match.groups()
        if detail.get("updated") is not True:
            if detail.get("updated") is not False:
                errors.append(key + ": missing update outcome")
            continue
        successes += 1
        path = root / f"{org}-{direction}.json"
        try:
            snap = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(key + ": missing/invalid successful snapshot: " + str(exc))
            continue
        rows = snap.get("results")
        n = snap.get("records_cached")
        reported = snap.get("reported_count")
        if snap.get("organisation_id") != org or snap.get("direction") != direction:
            errors.append(key + ": snapshot organisation/direction mismatch")
        if not isinstance(rows, list) or not isinstance(n, int) or n != len(rows) or n > limit:
            errors.append(key + ": snapshot record count mismatch or over limit")
        if detail.get("records_cached") != n or detail.get("reported_count") != reported:
            errors.append(key + ": manifest snapshot counts disagree")
        invalid = snap.get("skipped_invalid", 0)
        duplicates = snap.get("skipped_duplicates", 0)
        if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in (invalid, duplicates)):
            errors.append(key + ": invalid skipped-row counts")
            invalid, duplicates = 0, 0
        if detail.get("skipped_invalid", invalid) != invalid or detail.get("skipped_duplicates", duplicates) != duplicates:
            errors.append(key + ": skipped-row statistics disagree")
        if isinstance(rows, list):
            ids = [row.get("grant_id") for row in rows if isinstance(row, dict)]
            usable = [v for v in ids if isinstance(v, str) and v.strip()]
            if len(usable) != len(rows) or len(set(usable)) != len(usable):
                errors.append(key + ": missing or duplicate grant identifiers")
        if reported is not None and (not isinstance(reported, int) or isinstance(reported, bool) or not isinstance(n, int) or reported < n):
            errors.append(key + ": reported total below stored records")
        if not isinstance(rows, list) or any(not isinstance(row, dict) or not isinstance(row.get("data"), dict) for row in rows):
            errors.append(key + ": malformed award rows")
        if isinstance(n, int) and isinstance(reported, (int, type(None))) and snap.get("partial") != (reported is None or n < reported or invalid > 0 or duplicates > 0):
            errors.append(key + ": incomplete-data flag is inaccurate")
        try:
            datetime.datetime.fromisoformat(snap["retrieved_utc"])
        except (KeyError, TypeError, ValueError):
            errors.append(key + ": invalid retrieval timestamp")
    if manifest.get("updated_directions") != successes:
        errors.append("Manifest success count mismatch")
    expected_status = "ok" if successes == len(entries) else ("partial" if successes else "unavailable")
    if manifest.get("status") != expected_status:
        errors.append("Manifest health status does not reflect actual outcomes")
    print(f"360Giving cache validation: {successes}/{len(entries)} directions updated; status={expected_status}")
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, default=Path("data/360giving"))
    args = parser.parse_args()
    try:
        errors = validate(args.directory)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        errors = [str(exc)]
    if errors:
        for error in errors:
            print("FAIL:", error, file=sys.stderr)
        return 1
    print("PASS: published grant snapshots and manifest are internally consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
