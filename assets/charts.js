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
