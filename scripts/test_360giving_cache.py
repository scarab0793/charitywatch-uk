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
    snapshot["skipped_invalid"]=2
    snapshot["skipped_duplicates"]=1
    source.write_text(json.dumps(snapshot),encoding="utf-8")
    assert not validate(folder), "Valid cleaned snapshot rejected"
    manifest["organisations"][key]["skipped_invalid"]=2
    manifest["organisations"][key]["skipped_duplicates"]=1
    path.write_text(json.dumps(manifest),encoding="utf-8")
    assert not validate(folder), "Manifest accounting for excluded rows rejected"
    # Skipping duplicate/invalid source rows must remain partial even when
    # the number cached equals the published API count.
    snapshot["reported_count"]=1
    manifest["organisations"][key]["reported_count"]=1
    path.write_text(json.dumps(manifest),encoding="utf-8")
    source.write_text(json.dumps(snapshot),encoding="utf-8")
    assert not validate(folder), "Exclusions must permit a partial snapshot even at the reported cap"
    snapshot["partial"]=False
    source.write_text(json.dumps(snapshot),encoding="utf-8")
    assert any("incomplete-data flag" in message for message in validate(folder))
    snapshot["partial"]=True
    snapshot["reported_count"]=10
    manifest["organisations"][key]["reported_count"]=10
    path.write_text(json.dumps(manifest),encoding="utf-8")
    source.write_text(json.dumps(snapshot),encoding="utf-8")
    # Python bool is an int subclass: never accept True as a record count.
    snapshot["records_cached"]=True
    source.write_text(json.dumps(snapshot),encoding="utf-8")
    assert any("snapshot record count" in message for message in validate(folder))
    snapshot["records_cached"]=1
    snapshot["reported_count"]=True
    manifest["organisations"][key]["reported_count"]=True
    source.write_text(json.dumps(snapshot),encoding="utf-8")
    path.write_text(json.dumps(manifest),encoding="utf-8")
    assert any("reported total" in message for message in validate(folder))
    snapshot["reported_count"]=-1
    manifest["organisations"][key]["reported_count"]=-1
    source.write_text(json.dumps(snapshot),encoding="utf-8")
    path.write_text(json.dumps(manifest),encoding="utf-8")
    assert any("reported total" in message for message in validate(folder))
    snapshot["reported_count"]=10
    manifest["organisations"][key]["reported_count"]=10
    source.write_text(json.dumps(snapshot),encoding="utf-8")
    path.write_text(json.dumps(manifest),encoding="utf-8")
    snapshot["partial"]="true"
    source.write_text(json.dumps(snapshot),encoding="utf-8")
    assert any("incomplete-data flag" in message for message in validate(folder))
    snapshot["partial"]=True
    source.write_text(json.dumps(snapshot),encoding="utf-8")
    manifest["updated_directions"]=True
    path.write_text(json.dumps(manifest),encoding="utf-8")
    assert any("Manifest success count" in message for message in validate(folder))
    manifest["updated_directions"]=1
    manifest["organisations"][key]["records_cached"]=True
    path.write_text(json.dumps(manifest),encoding="utf-8")
    assert any("manifest snapshot counts" in message for message in validate(folder))
    manifest["organisations"][key]["records_cached"]=1
    manifest["organisations"][key]["skipped_invalid"]=True
    path.write_text(json.dumps(manifest),encoding="utf-8")
    assert any("skipped-row statistics" in message for message in validate(folder))
    manifest["organisations"][key]["skipped_invalid"]=2
    path.write_text(json.dumps(manifest),encoding="utf-8")
    # A corrupt selection list must return validation errors, never crash.
    manifest["selected_organisations"]=[["invalid", "nested"]]
    path.write_text(json.dumps(manifest),encoding="utf-8")
    assert any("Invalid selected organisation list" in message for message in validate(folder))
    manifest.pop("selected_organisations")
    path.write_text(json.dumps(manifest),encoding="utf-8")
    # A non-string manifest key must be rejected without regular-expression errors.
    manifest["organisations"]["invalid:key"]={"updated":False}
    manifest["status"]="partial"
    path.write_text(json.dumps(manifest),encoding="utf-8")
    assert any("Malformed organisation-direction entry" in message for message in validate(folder))
    manifest["organisations"].pop("invalid:key")
    manifest["status"]="ok"
    path.write_text(json.dumps(manifest),encoding="utf-8")
    snapshot["results"].append({"grant_id":"test","data":{"id":"test"}})
    snapshot["records_cached"]=2
    manifest["organisations"][key]["records_cached"]=2
    path.write_text(json.dumps(manifest),encoding="utf-8")
    source.write_text(json.dumps(snapshot),encoding="utf-8")
    assert any("duplicate grant identifiers" in message for message in validate(folder))
    snapshot["results"].pop()
    snapshot["records_cached"]=1
    manifest["organisations"][key]["records_cached"]=1
    source.write_text(json.dumps(snapshot),encoding="utf-8")
    path.write_text(json.dumps(manifest),encoding="utf-8")
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
