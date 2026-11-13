#!/usr/bin/env python3
"""Import the official Charity Commission England/Wales charity TXT ZIP.

Only fields from the main charity extract are used. This importer deliberately
does not infer annual-return history, CEO pay or grant recipients.

Usage:
 python scripts/import_ccew.py --zip publicextract.charity.zip --output data
"""
import argparse,csv,datetime,hashlib,io,json,re,unicodedata,zipfile
from collections import defaultdict
from pathlib import Path

def norm(s):
 return re.sub(r"[^a-z0-9]","",unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode().lower())
def shard(s):
 return (norm(s)+"__")[:2]
def col(headers,*candidates):
 for candidate in candidates:
  if norm(candidate) in headers:return headers[norm(candidate)]
 return None
def number(v):
 try:
  value=str(v).strip().replace(",","").replace("£","")
  return float(value) if value else None
 except ValueError:return None

def run(archive,out):
 digest=hashlib.sha256(archive.read_bytes()).hexdigest()
 with zipfile.ZipFile(archive) as z:
  files=[n for n in z.namelist() if n.lower().endswith(".txt") and not n.startswith("__MACOSX")]
  if len(files)!=1:raise ValueError("Expected exactly one TXT file in the official charity archive")
  with z.open(files[0]) as raw:
   stream=io.TextIOWrapper(raw,encoding="utf-8-sig",errors="replace",newline="")
   reader=csv.DictReader(stream,delimiter="\t")
   if not reader.fieldnames:raise ValueError("Missing headers")
   headers={norm(h):h for h in reader.fieldnames}
   n=col(headers,"reg_charity_number","reg_charity_no","registered_charity_number","charity_number")
   name=col(headers,"charity_name","name")
   if not n or not name:raise ValueError("Unknown schema; available columns: "+", ".join(reader.fieldnames))
   income=col(headers,"latest_income","latest_income_amount")
   spending=col(headers,"latest_expenditure","latest_expenditure_amount")
   year=col(headers,"latest_income_period_end","latest_financial_year_end","financial_year_end")
   names=defaultdict(list);nums=defaultdict(list);seen=set()
   for row in reader:
    num=(row.get(n) or "").strip()
    label=(row.get(name) or "").strip()
    if not num or not label or num in seen:continue
    seen.add(num)
    record={"name":label,"number":num,"jurisdiction":"EW",
      "income":number(row.get(income)) if income else None,
      "expenditure":number(row.get(spending)) if spending else None,
      "year":(row.get(year) or "").strip() or None if year else None,
      "ceo_pay":None,"grants":None}
    names[shard(label)].append(record)
    nums[shard(num)].append(record)
 if len(seen)<100000:raise ValueError(f"Unusually small extract: {len(seen)} charities; refusing publication")
 out.mkdir(parents=True,exist_ok=True)
 for sub,groups in (("ew",names),("ew/numbers",nums)):
  folder=out/sub;folder.mkdir(parents=True,exist_ok=True)
  for old in folder.glob("*.json"):old.unlink()
  for prefix,records in groups.items():
   (folder/(prefix+".json")).write_text(json.dumps(records,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
 manifest={"jurisdiction":"EW","count":len(seen),"shards":sorted(names),
  "number_shards":sorted(nums),"source":"Charity Commission for England and Wales",
  "source_url":"https://register-of-charities.charitycommission.gov.uk/en/register/full-register-download",
  "source_archive":archive.name,"sha256":digest,
  "generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
  "note":"Figures are published only if clearly labelled in the main charity extract; otherwise null. Annual return join not yet implemented."}
 (out/"manifest-ew.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
 print(f"Imported {len(seen)} official England/Wales charity records")

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--zip",required=True,type=Path)
 p.add_argument("--output",type=Path,default=Path("data"))
 a=p.parse_args();run(a.zip,a.output)
