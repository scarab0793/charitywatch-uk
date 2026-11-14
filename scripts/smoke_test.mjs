#!/usr/bin/env node
// Automated, dependency-free CharityWatch UK smoke tests.
// Run with: node scripts/smoke_test.mjs
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const html=fs.readFileSync('index.html','utf8');
const charts=fs.readFileSync('assets/charts.js','utf8');
const grants=fs.readFileSync('assets/grant-links.js','utf8');
const inline=[...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/gi)]
  .map(m=>m[1]).filter(Boolean);
assert.equal(inline.length,1,'Expected one inline application script');
new vm.Script(charts,{filename:'assets/charts.js'});
new vm.Script(grants,{filename:'assets/grant-links.js'});
assert.ok(html.includes('assets/grant-links.js'),'360Giving grant viewer script not loaded');
assert.ok(html.includes('cwGrantControls(region,record.number,record.annual_return_part_b)'),'Published grant viewer missing from profiles');
assert.ok(html.includes('cwGrantBinder(region,record.number)'),'Published grants controls are not wired');
new vm.Script(inline[0],{filename:'index.html:inline'});
for(const id of ['searchForm','q','region','results','suggestions','charityProfile',
  'profileBody','comparison','verifiedPayList','dataStatus','ceoPaySearch','ceoPaySort','grantsExplorer','grantFilter','grantYear','grantOrder','grantResults','grantNext']){
 assert.ok(html.includes('id="'+id+'"'),'Missing UI element: '+id);
}
assert.ok(html.includes('assets/charts.js'),'Charts script not loaded');
assert.ok(html.includes('await Promise.all(rows.map(x=>attachSalaryData(x,searchRegion,searchManifest)))'),
 'Search result cards must load official salary shards');
assert.ok(html.includes('salarySnippet(x)'),'Search result cards must show salary bands');
assert.ok(html.includes('cwComparisonChart(arr,comparisonMetric)'),'Comparison charts unavailable');
assert.ok(html.includes('String(r.period_end).slice(0,4)===year'),'Grant year filter must respect source reporting dates');
assert.ok(html.includes('Recipient organisations are not identified'),'Grant UI must not imply named recipients');

const model={income:120000,expenditure:70000,year:'2025-03-31',
 name:'Example charity',history:[
  {year:'2024-03-31',income:100000,expenditure:50000},
  {year:'2025-03-31',income:120000,expenditure:70000}
]};
const format=v=>String(v);
const context={Intl,Map,Set,Math,Number,String,Array,Date,
 escapeHTML:format, money:v=>'£'+v, console};
vm.createContext(context);
const test=`
${charts}
const finance=cwFinanceChart(${JSON.stringify(model)});
if(!finance.includes('<svg')||!finance.includes('£120000')||!finance.includes('2025-03'))throw Error('Finance chart failed');
const unknown=cwFinanceChart({name:'Incomplete',history:[{year:'2025-01-01',income:null,expenditure:null}]});
if(unknown.includes('<svg'))throw Error('Unknowns must not be charted as zero');
const ceo=cwCEOChart({periods:[{period_end:'2024-03-31',amount:115000},{period_end:'2025-03-31',amount:120000}]});
if(!ceo.includes('<svg')||!ceo.includes('2025-03'))throw Error('CEO trend failed');
const compare=cwComparisonChart([${JSON.stringify(model)}],'income');
if(!compare.includes('<svg')||!compare.includes('2024'))throw Error('Multi-charity comparison failed');
const missing=cwComparisonChart([{name:'Incomplete',history:[{year:'2025-01-01',income:null}]}],'income');
if(missing.includes('<svg'))throw Error('Missing comparison must not render fictitious bars');
`;
new vm.Script(test,{filename:'chart-tests'}).runInContext(context);
const grantTest=`
${grants}
const url=cwGrantEndpoint('ew','802052','made',0);
if(!url.includes('GB-CHC-802052/grants_made/'))throw Error('360Giving endpoint invalid');
if(cwGrantEndpoint('ew','802052','invalid')!==null)throw Error('Invalid grant direction accepted');
const result=cwGrantCard({data:{recipientOrganization:[{name:'Sample Recipient',id:'GB-CHC-123456'}],amountAwarded:1000,currency:'GBP',awardDate:'2025-01-01',title:'Sample award',dataSource:'https://example.org/data.csv'}},'made');
if(!result.includes('Sample Recipient')||!result.includes('£1,000')||!result.includes('Grant identifier'))throw Error('Grant attribution failed');
if(result.includes('money paid'))throw Error('Award incorrectly represented as paid amount');
if(!result.includes('Funder')||!result.includes('Recipient')||!result.includes('#charity/ew/123456'))throw Error('Relationship display or recipient registration link missing');
const panel=cwGrantControls('ew','802052',{period_end:'2025-06-30',expenditure_grants_institution:240000});
if(!panel.includes('£240,000')||!panel.includes('Part B')||!panel.includes('Not queried'))throw Error('Part B grant comparison missing');
`;
new vm.Script(grantTest,{filename:'grant-tests'}).runInContext(context);
const pay=JSON.parse(fs.readFileSync('data/verified-ceo-pay.json','utf8'));
assert.ok(Object.keys(pay.records).length>=1,'CEO primary-source catalogue missing');
for(const [id,record] of Object.entries(pay.records)){
 assert.ok(record.periods?.length,id+' missing pay periods');
 for(const p of record.periods)assert.ok(p.source_url?.startsWith('https://')&&Number.isFinite(p.amount),id+' missing cited amount');
}
const manifest=JSON.parse(fs.readFileSync('data/manifest-ew.json','utf8'));
assert.ok(manifest.count>100000,'Charity registry missing');
assert.ok(manifest.annual_return_part_a_records>10000,'Part A salaries missing');
assert.ok(manifest.salary_shards?.length,'Part A salary shards missing');
assert.ok(manifest.annual_return_part_b_records>10000,'Part B spending data missing');
const first=manifest.salary_shards[0];
const payRows=JSON.parse(fs.readFileSync('data/pay/ew/'+first+'.json','utf8'));
assert.ok(payRows.length>0&&payRows[0].salary_bands,'Salary shard payload invalid');
console.log('PASS: HTML/JS syntax, required controls, all three chart types, no false-zero visuals, verified CEO data, Part A/Part B payloads.');
