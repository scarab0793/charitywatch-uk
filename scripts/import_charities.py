#!/usr/bin/env python3
"""Import a regulator CSV export into small static JSON search shards.

Usage:
 python scripts/import_charities.py --input exports/charities.csv --jurisdiction EW

The CSV must contain a name and registration number. Other columns are optional.
Column names vary by regulator: inspect and map explicitly when necessary.
No guessed income, spending, CEO pay or grants.
"""
import argparse,csv,json,re,unicodedata
from pathlib import Path

ALIASES={
 "name":["charity_name","name","registered_charity_name","charity name"],
 "number":["reg_charity_number","charity_number","registered_number","registration_number","charity number"],
 "income":["latest_income","income","total_income","annual_income"],
 "expenditure":["latest_expenditure","expenditure","total_expenditure","annual_expenditure"],
 "year":["financial_year","financial_year_end","year_end","accounting_reference_date"],
}
def normal(s):
 return re.sub(r"[^a-z0-9]+","_",str(s).strip().lower()).strip("_")
def find(headers,field,override):
 if override:
  if normal(override) not in headers: raise ValueError("Missing specified column: "+override)
  return headers[normal(override)]
 for alias in ALIASES[field]:
  if normal(alias) in headers:return headers[normal(alias)]
 return None
def amount(v):
 if not v or str(v).strip().lower() in ("n/a","null","-"):return None
 try:return float(str(v).replace(",","").replace("£","").strip())
 except ValueError:return None
def key(name):
 a=unicodedata.normalize("NFKD",name).encode("ascii","ignore").decode().lower()
 a=re.sub(r"[^a-z0-9]","",a)
 return (a+"__")[:2]
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--input",required=True)
 p.add_argument("--jurisdiction",choices=["EW","SC","NI"],required=True)
 p.add_argument("--output",default="data")
 for f in ALIASES:p.add_argument("--"+f+"-column")
 args=p.parse_args()
 out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
 buckets={};seen=set();count=0
 with open(args.input,encoding="utf-8-sig",newline="") as fp:
  reader=csv.DictReader(fp)
  if not reader.fieldnames:raise ValueError("Empty CSV")
  headers={normal(h):h for h in reader.fieldnames}
  cols={f:find(headers,f,getattr(args,f+"_column")) for f in ALIASES}
  if not cols["name"] or not cols["number"]:raise ValueError("Name and registration number columns required; use --name-column and --number-column")
  for row in reader:
   name=(row.get(cols["name"]) or "").strip()
   number=(row.get(cols["number"]) or "").strip()
   if not name or not number or (args.jurisdiction,number) in seen:continue
   seen.add((args.jurisdiction,number))
   def value(field):
    return (row.get(cols[field]) or "").strip() if cols[field] else ""
   item={"name":name,"number":number,"jurisdiction":args.jurisdiction,
         "income":amount(value("income")),"expenditure":amount(value("expenditure")),
         "year":value("year") or None,"ceo_pay":None,"grants":None}
   buckets.setdefault(key(name),[]).append(item);count+=1
 for bucket,items in buckets.items():
  path=out/args.jurisdiction.lower()/ (bucket+".json")
  path.parent.mkdir(parents=True,exist_ok=True)
  path.write_text(json.dumps(items,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
 (out/("manifest-"+args.jurisdiction.lower()+".json")).write_text(json.dumps({"jurisdiction":args.jurisdiction,"count":count,"shards":sorted(buckets),"source_file":Path(args.input).name},indent=2),encoding="utf-8")
 print(f"Imported {count} unique records into {len(buckets)} shards. Check accounting definitions before publication.")
if __name__=="__main__":main()
