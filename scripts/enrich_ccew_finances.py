#!/usr/bin/env python3
"""Enrich official CCEW charity JSON shards from the annual return history ZIP.

Both archives must come from the Charity Commission full-register download.
Join via organisation_number, NOT the public registration number.
Only records with a recognised financial period end and actual reported figures
are used. Unknown schemas fail closed.
"""
import argparse,csv,datetime,hashlib,io,json,re,sys,zipfile
from pathlib import Path
from collections import defaultdict

csv.field_size_limit(10**8)

def norm(s):return re.sub('[^a-z0-9]','',str(s).lower())
def field(headers,*names):
 for name in names:
  if norm(name) in headers:return headers[norm(name)]
 return None
def read_zip(path):
 z=zipfile.ZipFile(path)
 names=[n for n in z.namelist() if n.lower().endswith('.txt')]
 if len(names)!=1:raise ValueError('Expected exactly one TXT file: '+str(path))
 stream=io.TextIOWrapper(z.open(names[0]),encoding='utf-8-sig',errors='replace',newline='')
 reader=csv.DictReader(stream,delimiter='\t')
 if not reader.fieldnames:raise ValueError('Missing header')
 return z,stream,reader,{norm(h):h for h in reader.fieldnames}
def money(value):
 value=str(value or '').strip().replace(',','')
 if not value:return None
 try:
  result=float(value)
  if not (-1e15<result<1e15):return None
  return result
 except ValueError:return None
def date(value):
 value=str(value or '').strip()
 if not value:return None
 for fmt in ('%Y-%m-%d','%Y-%m-%d %H:%M:%S','%d/%m/%Y','%d-%m-%Y','%Y/%m/%d'):
  try:return datetime.datetime.strptime(value,fmt).date().isoformat()
  except ValueError:pass
 if len(value)>=10:
  try:return datetime.date.fromisoformat(value[:10]).isoformat()
  except ValueError:pass
 return None
def run(charity_zip,history_zip,out):
 z,stream,rows,headers=read_zip(charity_zip)
 org=field(headers,'organisation_number')
 reg=field(headers,'registered_charity_number','reg_charity_number')
 if not org or not reg:raise ValueError('Charity ZIP lacks organisation_number or registered_charity_number')
 mapping={}
 for row in rows:
  o=(row.get(org) or '').strip();r=(row.get(reg) or '').strip()
  if o and r:mapping[o]=r
 stream.close();z.close()
 if len(mapping)<100000:raise ValueError('Unusually few organisation mappings')
 z,stream,rows,headers=read_zip(history_zip)
 org=field(headers,'organisation_number')
 income=field(headers,'total_gross_income','gross_income','total_income')
 expense=field(headers,'total_gross_expenditure','gross_expenditure','total_expenditure')
 period=field(headers,'fin_period_end_date','financial_period_end_date','financial_period_end','financial_year_end_date','financial_year_end')
 if not all((org,income,expense,period)):
  raise ValueError('Unknown annual history schema: '+', '.join(headers.values()))
 latest={};years=defaultdict(dict)
 counts={'rows':0,'matched_org':0,'valid_date':0,'valid_money':0}
 sample_dates=[]
 for row in rows:
  counts['rows']+=1
  registered=mapping.get((row.get(org) or '').strip())
  if not registered:continue
  counts['matched_org']+=1
  raw_date=row.get(period)
  if len(sample_dates)<4 and raw_date and raw_date not in sample_dates:sample_dates.append(raw_date)
  d=date(raw_date)
  if not d:continue
  counts['valid_date']+=1
  inc=money(row.get(income));exp=money(row.get(expense))
  if inc is None and exp is None:continue
  counts['valid_money']+=1
  item={'year':d,'income':inc,'expenditure':exp}
  years[registered][d]=item
  if registered not in latest or d>latest[registered]['year']:latest[registered]=item
 stream.close();z.close()
 print('Import diagnostics:',counts,'unique charities:',len(latest),'sample date formats:',sample_dates,flush=True)
 if len(latest)<10000:raise ValueError('Too few financial records; refusing publication')
 histories={reg:sorted(periods.values(),key=lambda x:x['year'],reverse=True)[:5] for reg,periods in years.items()}
 del years
 # Stage every changed file before replacing any published data.
 staged=[]
 updated=0
 for folder in (out/'ew',out/'ew'/'numbers'):
  if not folder.exists():raise ValueError('Directory not imported: '+str(folder))
  for file in folder.glob('*.json'):
   items=json.loads(file.read_text(encoding='utf-8'))
   for item in items:
    fin=latest.get(str(item['number']))
    if fin:
     item.update(fin)
     item['history']=histories.get(str(item['number']),[])
     item['financial_source']='CCEW annual return history'
     updated+=1
   staged.append((file,json.dumps(items,ensure_ascii=False,separators=(',',':'))))
 manifest=out/'manifest-ew.json'
 meta=json.loads(manifest.read_text())
 meta['financial_records']=len(latest)
 meta['history_years_max']=5
 meta['financial_source']='CCEW charity_annual_return_history'
 meta['financial_updated_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
 meta['history_sha256']=hashlib.sha256(history_zip.read_bytes()).hexdigest()
 for file,body in staged:
  file.write_text(body,encoding='utf-8')
 manifest.write_text(json.dumps(meta,indent=2))
 print('Financially enriched charities:',len(latest),'shard records updated:',updated)
if __name__=='__main__':
 p=argparse.ArgumentParser()
 p.add_argument('--charity-zip',required=True,type=Path)
 p.add_argument('--history-zip',required=True,type=Path)
 p.add_argument('--output',default='data',type=Path)
 a=p.parse_args();run(a.charity_zip,a.history_zip,a.output)
