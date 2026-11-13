#!/usr/bin/env python3
"""Convert a locally downloaded UK register CSV into static searchable JSON.

Input columns: countrycode,charitynumber,name (as in the public OpenCharities
CSV); optionally income,expenditure,year. Never fabricate financial values.
For authoritative financial amounts, import regulator-sourced verified exports.
Usage: python scripts/import_uk_register.py --input charities.csv
"""
import argparse,csv,json,re,unicodedata,datetime
from pathlib import Path

def key(s):
 s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode().lower()
 return (re.sub("[^a-z0-9]","",s)+"__")[:2]
def money(s):
 try:
  if not str(s).strip():return None
  return float(str(s).replace(",","").replace("£",""))
 except (ValueError,TypeError):return None

def run(path,destination):
 groups={};numbers={};counts={x:0 for x in ("ew","sc","ni")};seen=set()
 with open(path,encoding="utf-8-sig",newline="") as f:
  for row in csv.DictReader(f):
   region=(row.get("countrycode") or "").strip().lower()
   number=(row.get("charitynumber") or "").strip()
   name=(row.get("name") or "").strip()
   if region not in counts or not number or not name or (region,number) in seen:continue
   seen.add((region,number))
   item={"name":name,"number":number,"jurisdiction":region.upper(),
         "income":money(row.get("income")),"expenditure":money(row.get("expenditure")),
         "year":row.get("year") or None,"ceo_pay":None,"grants":None}
   groups.setdefault((region,key(name)),[]).append(item)
   number_key=(re.sub("[^a-z0-9]","",number.lower())+"__")[:2]
   numbers.setdefault((region,number_key),[]).append(item)
   counts[region]+=1
 for (region,shard),records in groups.items():
  target=destination/region/(shard+".json")
  target.parent.mkdir(parents=True,exist_ok=True)
  target.write_text(json.dumps(records,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
 for (region,shard),records in numbers.items():
  target=destination/region/"numbers"/(shard+".json")
  target.parent.mkdir(parents=True,exist_ok=True)
  target.write_text(json.dumps(records,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
 for region,count in counts.items():
  manifest={"jurisdiction":region.upper(),"count":count,
    "shards":sorted(shard for reg,shard in groups if reg==region),
    "number_shards":sorted(shard for reg,shard in numbers if reg==region),
    "source_file":path.name,"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "notes":"Income/expenditure are only populated when supplied in input; this import does not verify their provenance."}
  (destination/("manifest-"+region+".json")).write_text(json.dumps(manifest,indent=2),encoding="utf-8")
 print("Imported",counts)

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--input",required=True,type=Path)
 p.add_argument("--output",default="data",type=Path)
 args=p.parse_args();run(args.input,args.output)
