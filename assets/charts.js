/* CharityWatch UK: local, dependency-free, accessible SVG financial charts. */
const chartAmt=n=>new Intl.NumberFormat('en-GB',{notation:'compact',maximumFractionDigits:1,style:'currency',currency:'GBP'}).format(n);
const cwFinanceChart=record=>{
 const periods=Array.isArray(record.history)&&record.history.length?record.history:[{year:record.year,income:record.income,expenditure:record.expenditure}];
 const byDate=new Map();
 for(const p of periods){const date=String(p.year||'').slice(0,10);if(date&&!byDate.has(date))byDate.set(date,p);}
 const rows=[...byDate].sort((a,b)=>a[0].localeCompare(b[0])).slice(-8);
 const valid=rows.filter(([,p])=>Number.isFinite(p.income)||Number.isFinite(p.expenditure));
 if(valid.length<2)return '<p class="chart-empty">At least two annual reporting periods are needed to draw the financial chart.</p>';
 const max=Math.max(1,...rows.flatMap(([,p])=>[p.income,p.expenditure].filter(n=>Number.isFinite(n)&&n>=0)));
 const W=760,H=292,L=80,R=15,T=18,B=52,PH=H-T-B,slot=(W-L-R)/rows.length,base=T+PH;
 let shapes='';
 for(let i=0;i<=4;i++){const y=T+PH*i/4;shapes+='<line x1="'+L+'" y1="'+y+'" x2="'+(W-R)+'" y2="'+y+'" stroke="#dce7f0"/><text x="'+(L-8)+'" y="'+(y+4)+'" text-anchor="end" class="chart-axis">'+chartAmt(max*(1-i/4))+'</text>';}
 rows.forEach(([date,row],i)=>{
  const middle=L+(i+.5)*slot,bw=Math.min(30,slot*.30);
  [['income','#1677b8',-bw-2],['expenditure','#e1a23d',2]].forEach(([field,color,offset])=>{
   const n=row[field];if(!Number.isFinite(n)||n<0)return;
   const height=n/max*PH;
   shapes+='<rect x="'+(middle+offset)+'" y="'+(base-height)+'" width="'+bw+'" height="'+Math.max(1,height)+'" rx="2" fill="'+color+'"><title>'+escapeHTML(date+' · '+field+': '+money(n))+'</title></rect>';
  });
  shapes+='<text x="'+middle+'" y="'+(base+21)+'" text-anchor="middle" class="chart-axis">'+escapeHTML(date.slice(0,7))+'</text>';
 });
 return '<div class="chart-wrap"><h4>Income and expenditure over time</h4><svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Financial income and expenditure by reporting period for '+escapeHTML(record.name)+'">'+shapes+'</svg><div class="chart-legend"><span><i class="chart-key" style="background:#1677b8"></i>Gross income</span><span><i class="chart-key" style="background:#e1a23d"></i>Gross expenditure</span></div><p class="chart-caption">Nominal GBP. Hover or focus on bars for exact reported amounts. Missing values are omitted, not treated as zero. Source: official annual return history.</p></div>';
};
const cwCEOChart=entry=>{
 const points=[...(entry.periods||[])].filter(p=>Number.isFinite(p.amount)&&p.period_end).sort((a,b)=>a.period_end.localeCompare(b.period_end));
 if(points.length<2)return '<p class="chart-empty">At least two sourced CEO pay disclosures are needed for a remuneration chart.</p>';
 const W=720,H=265,L=85,R=25,T=25,B=58;
 const amounts=points.map(p=>p.amount),min=Math.min(...amounts),max=Math.max(...amounts),d=Math.max(1,max-min);
 const low=Math.max(0,min-d*.25),high=max+d*.25;
 const y=n=>T+(high-n)/(high-low)*(H-T-B),x=i=>L+i*(W-L-R)/(points.length-1);
 let shapes='';
 for(let i=0;i<=4;i++){const amount=low+(high-low)*(4-i)/4,yy=y(amount);shapes+='<line x1="'+L+'" y1="'+yy+'" x2="'+(W-R)+'" y2="'+yy+'" stroke="#dce7f0"/><text x="'+(L-8)+'" y="'+(yy+4)+'" text-anchor="end" class="chart-axis">'+chartAmt(amount)+'</text>';}
 const path=points.map((p,i)=>(i?'L':'M')+x(i)+' '+y(p.amount)).join(' ');
 shapes+='<path d="'+path+'" stroke="#0866a4" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>';
 points.forEach((p,i)=>{shapes+='<circle cx="'+x(i)+'" cy="'+y(p.amount)+'" r="5" fill="#0866a4" stroke="#fff" stroke-width="2"><title>'+escapeHTML(p.period_end+': '+money(p.amount))+'</title></circle><text x="'+x(i)+'" y="'+(H-B+24)+'" text-anchor="middle" class="chart-axis">'+escapeHTML(p.period_end.slice(0,7))+'</text>';});
 return '<div class="chart-wrap"><h4>Verified CEO remuneration history</h4><svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="CEO remuneration by reporting period">'+shapes+'</svg><p class="chart-caption">Nominal GBP. Vertical axis may start above zero; consult the exact values and annual-report links below. Remuneration definitions may differ between charities.</p></div>';
};

/* Shared annual comparison: labels are financial-period END years, not
 * identical accounting periods. Missing observations are gaps. */
const cwComparisonChart=(records,metric)=>{
 const chosen=['income','expenditure'].includes(metric)?metric:'income';
 const colors=['#0b6aa8','#d1822f','#567c3a'];
 const series=(records||[]).slice(0,3).map((r,i)=>{
  const periods=Array.isArray(r.history)&&r.history.length?r.history:[{year:r.year,income:r.income,expenditure:r.expenditure}];
  const years=new Map();
  for(const p of periods){
   const end=String(p.year||'').slice(0,10),y=end.slice(0,4),value=p[chosen];
   if(!/^\d{4}$/.test(y)||!Number.isFinite(value)||value<0)continue;
   const prior=years.get(y);
   if(!prior||end>prior.date)years.set(y,{date:end,value});
  }
  return {name:r.name,number:r.number,color:colors[i],years};
 });
 const allYears=[...new Set(series.flatMap(s=>[...s.years.keys()]))].sort().slice(-8);
 if(!allYears.length)return '<p class="chart-empty">No usable financial history for the selected charities.</p>';
 const n=series.reduce((sum,s)=>sum+allYears.filter(y=>s.years.has(y)).length,0);
 if(n<2)return '<p class="chart-empty">At least two reported financial periods are required for a comparison chart.</p>';
 const max=Math.max(1,...series.flatMap(s=>allYears.map(y=>s.years.get(y)?.value).filter(v=>Number.isFinite(v))));
 const W=780,H=300,L=85,R=22,T=25,B=68,base=H-B,PH=base-T;
 const slot=(W-L-R)/allYears.length,barW=Math.min(24,slot/Math.max(3,series.length+1)),clusters=series.length;
 let svg='';
 for(let step=0;step<=4;step++){
  const y=T+step*PH/4;
  svg+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+y+'" y2="'+y+'" stroke="#dce7f0"/><text x="'+(L-7)+'" y="'+(y+4)+'" text-anchor="end" class="chart-axis">'+chartAmt(max*(1-step/4))+'</text>';
 }
 allYears.forEach((year,i)=>{
  const mid=L+(i+.5)*slot;
  series.forEach((serie,j)=>{
   const point=serie.years.get(year);
   if(!point)return;
   const h=point.value/max*PH,x=mid+(j-(clusters-1)/2)*(barW+3)-barW/2;
   svg+='<rect x="'+x+'" y="'+(base-h)+'" width="'+barW+'" height="'+Math.max(1,h)+'" rx="2" fill="'+serie.color+'"><title>'+escapeXML(serie.name)+' — period ending '+escapeXML(point.date)+': '+escapeXML(chartAmt(point.value))+'</title></rect>';
  });
  svg+='<text x="'+mid+'" y="'+(base+22)+'" text-anchor="middle" class="chart-axis">'+year+'</text>';
 });
 const legend=series.map(s=>'<span><i class="chart-key" style="background:'+s.color+'"></i>'+escapeXML(s.name)+'</span>').join('');
 return '<div class="chart-wrap"><h4>'+ (chosen==='income'?'Gross annual income':'Gross annual expenditure')+' by financial year-end</h4><svg role="img" aria-label="Comparison of '+(chosen==='income'?'income':'expenditure')+' across selected charities and financial years" viewBox="0 0 '+W+' '+H+'">'+svg+'</svg><div class="chart-legend">'+legend+'</div><p class="chart-caption">GBP, nominal. Years indicate the calendar year in which the accounts end; charities may have different year-end dates and reporting periods. Exact dates and amounts are available by hovering over bars. Missing periods are left blank, not shown as zero. If more than one period ends in the same year, the latest is shown.</p></div>';
};
const escapeXML=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
