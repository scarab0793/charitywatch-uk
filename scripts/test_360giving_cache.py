#!/usr/bin/env python3
"""Offline tests of cache snapshot consistency and incomplete-source handling."""
import datetime
import json
import tempfile
from pathlib import Path
from verify_360giving_cache import validate

org="GB-CHC-802052"
key=org+":made"
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
with tempfile.TemporaryDirectory() as tmp:
    folder=Path(tmp)
    snapshot={
        "organisation_id":org,"direction":"made","retrieved_utc":now,
        "reported_count":10,"records_cached":1,"partial":True,
        "results":[{"grant_id":"test","data":{"id":"test","amountAwarded":100}}],
    }
    manifest={
        "max_records_per_org_direction":40,
        "organisations":{key:{"updated":True,"records_cached":1,"reported_count":10}},
        "updated_directions":1,"status":"ok",
    }
    source=folder/(org+"-made.json")
    source.write_text(json.dumps(snapshot),encoding="utf-8")
    path=folder/"manifest.json"
    path.write_text(json.dumps(manifest),encoding="utf-8")
    assert not validate(folder), "Valid partial award sample rejected"
    snapshot["partial"]=False
    source.write_text(json.dumps(snapshot),encoding="utf-8")
    assert any("incomplete-data flag" in message for message in validate(folder))
    snapshot["partial"]=True
    source.write_text(json.dumps(snapshot),encoding="utf-8")
    manifest["organisations"][key]={"updated":False,"error":"provider unavailable"}
    manifest["updated_directions"]=0
    manifest["status"]="unavailable"
    path.write_text(json.dumps(manifest),encoding="utf-8")
    assert not validate(folder), "Unavailable external source should retain past cache"
    manifest["status"]="ok"
    path.write_text(json.dumps(manifest),encoding="utf-8")
    assert any("health status" in message for message in validate(folder))
print("PASS: valid grant snapshots, rejected mismatches and provider outages handled")
