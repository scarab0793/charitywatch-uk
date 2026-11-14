#!/usr/bin/env python3
"""Cache small, explicitly partial 360Giving award extracts for GitHub Pages.

360Giving currently does not send permissive browser CORS headers.
Use Actions (server-to-server), then publish a same-origin static snapshot.
This is a capped discovery sample, not a comprehensive list or proof of payments.
"""
import datetime
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

# Three independently sourced showcase profiles are always included. Add a
# small, deterministic selection of the largest reported institutional grant
# makers; this is a sample, not a complete register of 360Giving publishers.
CORE_ORG_IDS = ["GB-CHC-802052", "GB-CHC-202918", "GB-CHC-288701"]
MAX_ORGS = 12


def select_organisations(source=Path("data/grant-makers-ew.json")):
    selected = list(CORE_ORG_IDS)
    try:
        source_data = json.loads(source.read_text(encoding="utf-8"))
        rows = source_data.get("records", [])
        # Do not assume the file is already sorted by grant amount.
        rows = sorted(rows, key=lambda row: row.get("grants_to_institutions") or 0, reverse=True)
        for row in rows:
            number = str(row.get("number") or "")
            if not re.fullmatch(r"[0-9]{4,9}", number):
                continue
            org = "GB-CHC-" + number
            if org not in selected:
                selected.append(org)
            if len(selected) >= MAX_ORGS:
                break
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        print("Unable to select additional organisations; keeping core set:", exc)
    return selected


ORG_IDS = select_organisations()
DIRECTIONS = ("made", "received")
PER_PAGE = 20
MAX_PAGES = 2
OUT = Path("data/360giving")
OUT.mkdir(parents=True, exist_ok=True)
summary = {"updated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "source": "360Giving official API; published awards, not confirmed payments",
           "max_records_per_org_direction": PER_PAGE * MAX_PAGES,
           "selected_organisations": ORG_IDS,
           "selection": "Three core profiles plus the largest reported CCEW institutional grant makers; sampled, not comprehensive",
           "organisations": {}}
for org in ORG_IDS:
    for direction in DIRECTIONS:
        all_rows = []
        reported_total = None
        error = None
        for page in range(MAX_PAGES):
            offset = page * PER_PAGE
            endpoint = f"https://api.threesixtygiving.org/api/v1/org/{org}/grants_{direction}/?limit={PER_PAGE}&offset={offset}"
            request = urllib.request.Request(endpoint, headers={
                "Accept": "application/json", "User-Agent": "CharityWatchUK-cache/1.0"})
            try:
                payload = None
                for attempt in range(4):
                    try:
                        with urllib.request.urlopen(request, timeout=30) as response:
                            payload = json.load(response)
                        break
                    except urllib.error.HTTPError as exc:
                        if exc.code not in (429, 500, 502, 503, 504) or attempt == 3:
                            raise
                        pause = min(30, 3 * (attempt + 1))
                        print(f"360Giving HTTP {exc.code} for {org}/{direction}; retrying after {pause}s")
                        time.sleep(pause)
                if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
                    raise ValueError("360Giving returned an unexpected schema")
                total = payload.get("count")
                if isinstance(total, int) and total >= 0:
                    reported_total = total
                for row in payload["results"]:
                    if isinstance(row, dict) and isinstance(row.get("data"), dict):
                        all_rows.append({
                            "grant_id": row.get("grant_id"),
                            "data": row["data"],
                            "publisher": row.get("publisher"),
                            "data_license": row.get("data_license"),
                        })
                if not payload.get("next") or not payload["results"]:
                    break
                time.sleep(1.2)
            except (urllib.error.URLError, ValueError, TimeoutError) as exc:
                error = type(exc).__name__ + ": " + str(exc)[:150]
                break
        # Do not overwrite a previously valid published snapshot with a failed request.
        if error:
            print(f"Could not update {org}/{direction}: {error}")
            summary["organisations"][f"{org}:{direction}"] = {"error": error, "updated": False}
            continue
        data = {
            "organisation_id": org, "direction": direction,
            "source": "360Giving published grant awards, not direct evidence of payments",
            "retrieved_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "reported_count": reported_total,
            "records_cached": len(all_rows),
            "partial": reported_total is None or len(all_rows) < reported_total,
            "api_url": f"https://api.threesixtygiving.org/api/v1/org/{org}/grants_{direction}/?limit=20&offset=0",
            "results": all_rows,
        }
        path = OUT / f"{org}-{direction}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        summary["organisations"][f"{org}:{direction}"] = {
            "records_cached": len(all_rows), "reported_count": reported_total, "updated": True
        }
        print(f"{org} {direction}: {len(all_rows)} cached, {reported_total} reported")
        time.sleep(1.2)

successes = sum(bool(item.get("updated")) for item in summary["organisations"].values())
summary["updated_directions"] = successes
summary["status"] = "ok" if successes == len(summary["organisations"]) else ("partial" if successes else "unavailable")
(OUT / "manifest.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
print("360Giving cache status:", summary["status"], "| updated directions:", successes, "/", len(summary["organisations"]))
# Transient provider failures must not turn every scheduled refresh into an
# email notification. Previous valid snapshots are retained; the manifest
# explicitly records problems instead of asserting success.

