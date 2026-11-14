#!/usr/bin/env python3
"""Cache small, explicitly partial 360Giving award extracts for GitHub Pages.

360Giving currently does not send permissive browser CORS headers.
Use Actions (server-to-server), then publish a same-origin static snapshot.
This is a capped discovery sample, not a comprehensive list or proof of payments.
"""
import datetime
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from select_360giving_orgs import select_organisations

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
        seen_grants = set()
        reported_total = None
        error = None
        skipped_invalid = 0
        skipped_duplicates = 0
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
                    if not isinstance(row, dict) or not isinstance(row.get("data"), dict):
                        skipped_invalid += 1
                        continue
                    grant_id = row.get("grant_id") or row["data"].get("id")
                    if not isinstance(grant_id, str) or not grant_id.strip():
                        skipped_invalid += 1
                        continue
                    if grant_id in seen_grants:
                        skipped_duplicates += 1
                        continue
                    seen_grants.add(grant_id)
                    all_rows.append({
                        "grant_id": grant_id,
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
            "partial": reported_total is None or len(all_rows) < reported_total
                       or skipped_invalid > 0 or skipped_duplicates > 0,
            "skipped_invalid": skipped_invalid,
            "skipped_duplicates": skipped_duplicates,
            "api_url": f"https://api.threesixtygiving.org/api/v1/org/{org}/grants_{direction}/?limit=20&offset=0",
            "results": all_rows,
        }
        path = OUT / f"{org}-{direction}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        summary["organisations"][f"{org}:{direction}"] = {
            "records_cached": len(all_rows), "reported_count": reported_total,
            "skipped_invalid": skipped_invalid, "skipped_duplicates": skipped_duplicates,
            "updated": True
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

