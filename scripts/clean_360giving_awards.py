"""Deduplicate 360Giving award rows across pages, preserving their source data.

The same grant can occur on adjacent API pages. Missing identifiers cannot be
used as reliable identities and are excluded, not converted to fake grants.
"""
def append_unique_awards(rows, seen, output):
    invalid = 0
    duplicate = 0
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("data"), dict):
            invalid += 1
            continue
        grant_id = row.get("grant_id") or row["data"].get("id")
        if not isinstance(grant_id, str) or not grant_id.strip():
            invalid += 1
            continue
        grant_id = grant_id.strip()
        if grant_id in seen:
            duplicate += 1
            continue
        seen.add(grant_id)
        output.append({
            "grant_id": grant_id,
            "data": row["data"],
            "publisher": row.get("publisher"),
            "data_license": row.get("data_license"),
        })
    return invalid, duplicate
