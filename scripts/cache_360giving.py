#!/usr/bin/env python3
"""Cache small, explicitly partial 360Giving award extracts for GitHub Pages.

360Giving currently does not send permissive browser CORS headers.
Use Actions (server-to-server), then publish a same-origin static snapshot.
This is a capped discovery sample, not a comprehensive list or proof of payments.
"""
import datetime
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ORG_IDS = ["GB-CHC-802052", "GB-CHC-202918", "GB-CHC-288701"]
DIRECTIONS = ("made", "received")
PER_PAGE = 20
MAX_PAGES = 5
OUT = Path("data/360giving")
OUT.mkdir(parents=True, exist_ok=True)
summary = {"updated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "source": "360Giving official API; published awards, not confirmed payments",
           "max_records_per_org_direction": PER_PAGE * MAX_PAGES, "organisations": {}}
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
                with urllib.request.urlopen(request, timeout=30) as response:
                    payload = json.load(response)
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
                time.sleep(0.65)
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
        time.sleep(0.65)

(OUT / "manifest.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
if not any(x.get("updated") for x in summary["organisations"].values()):
    raise SystemExit("No 360Giving data refreshed; preserving existing snapshots")
