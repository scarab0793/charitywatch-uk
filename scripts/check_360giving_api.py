#!/usr/bin/env python3
"""Probe the public 360Giving organisation grant endpoint from GitHub Actions.

Store only API response structure and HTTP/CORS metadata, NOT grant records.
Use this before claiming browser integration is verified.
"""
import datetime
import json
import urllib.error
import urllib.request
from pathlib import Path

ORG_IDS = ("GB-CHC-802052", "GB-CHC-202918")
results = []
for identifier in ORG_IDS:
    url = f"https://api.threesixtygiving.org/api/v1/org/{identifier}/grants_made/?limit=1&offset=0"
    entry = {"organisation_id": identifier, "endpoint": url}
    request = urllib.request.Request(url, headers={
        "Accept": "application/json",
        "Origin": "https://scarab0793.github.io",
        "User-Agent": "CharityWatchUK-API-compatibility-check/1.0",
    })
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            entry["http_status"] = response.status
            entry["cors_allow_origin"] = response.headers.get("Access-Control-Allow-Origin")
            payload = json.load(response)
            entry["root_type"] = type(payload).__name__
            if isinstance(payload, dict):
                entry["root_keys"] = sorted(payload.keys())[:40]
                records = payload.get("results")
                entry["results_array"] = isinstance(records, list)
                if isinstance(records, list) and records:
                    row = records[0]
                    entry["result_keys"] = sorted(row.keys())[:40] if isinstance(row, dict) else []
                    data = row.get("data") if isinstance(row, dict) else None
                    entry["data_keys"] = sorted(data.keys())[:50] if isinstance(data, dict) else []
                entry["reported_count"] = payload.get("count") if isinstance(payload.get("count"), int) else None
    except urllib.error.HTTPError as error:
        entry["http_status"] = error.code
        entry["error"] = "HTTP error"
        entry["cors_allow_origin"] = error.headers.get("Access-Control-Allow-Origin")
    except Exception as error:
        entry["error"] = type(error).__name__ + ": " + str(error)[:160]
    results.append(entry)

report = {
    "checked_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "purpose": "360Giving API endpoint, response shape and browser CORS compatibility",
    "results": results,
}
path = Path("data/diagnostics/360giving-api.json")
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2, ensure_ascii=False))
