/* 360Giving published grant awards. Do NOT confuse awards with payments.
 * Requests are user-initiated (API rate limit: 2 requests/second/IP).
 * We do not store grants: publisher takedowns and updates stay effective. */
const cwGrantEscape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cwGrantMoney=n=>Number.isFinite(n)?new Intl.NumberFormat('en-GB',{style:'currency',currency:'GBP',maximumFractionDigits:0}).format(n):'Not reported';
const cwGrantEndpoint=(region,number,direction,offset=0)=>{
 if(region!=='ew'||!/^\d{4,9}$/.test(String(number)))return null;
 if(!['made','received'].includes(direction)||!Number.isInteger(offset)||offset<0)return null;
 return 'https://api.threesixtygiving.org/api/v1/org/GB-CHC-'+number+'/grants_'+direction+'/?limit=20&offset='+offset;
};
const cwGrantSourceLink=url=>{
 try{
  const u=new URL(url);
  if(u.protocol!=='https:'||u.username||u.password)return '';
  return '<a href="'+cwGrantEscape(u.href)+'" target="_blank" rel="noopener noreferrer">Publisher data</a>';
 }catch(_){return '';}
};
const cwGrantOrganisation=(value,unnamed)=>{
 const first=Array.isArray(value)?value[0]:null;
 const name=typeof first?.name==='string'&&first.name.trim()?first.name:unnamed;
 const id=typeof first?.id==='string'?first.id:'';
 const matched=/^GB-CHC-(\d{4,9})$/.exec(id);
 return {name,id,registered:matched?.[1]||null};
};
const cwGrantOrganisationLabel=org=>{
 const name=cwGrantEscape(org.name);
 return org.registered?'<a href="#charity/ew/'+org.registered+'">'+name+'</a>':name;
};
const cwGrantCard=(row,direction,apiPageUrl='')=>{
 const g=row?.data;
 if(!g||typeof g!=='object')return '';
 const funder=cwGrantOrganisation(g.fundingOrganization,'Funding organisation not stated');
 const recipient=cwGrantOrganisation(g.recipientOrganization,g.recipientIndividual?'Individual recipient (not named)':'Recipient organisation not stated');
 const amount=g.amountAwarded;
 const currency=typeof g.currency==='string'?g.currency:'';
 const awarded=currency==='GBP'?cwGrantMoney(amount):Number.isFinite(amount)?cwGrantEscape(amount.toLocaleString('en-GB'))+' '+cwGrantEscape(currency||'currency unspecified'):'Not reported';
 const disbursed=g.amountDisbursed;
 const paid=Number.isFinite(disbursed)?'<p class="small muted">Amount disbursed, where separately reported: '+(currency==='GBP'?cwGrantMoney(disbursed):cwGrantEscape(disbursed.toLocaleString('en-GB'))+' '+cwGrantEscape(currency))+'</p>':'';
 const rawSource=g.dataSource||row?.data_source||row?.additional_data?.data_source;
 const providedSource=typeof rawSource==='string'?rawSource:(rawSource?.url||rawSource?.source_url||rawSource?.download_url);
 const source=cwGrantSourceLink(providedSource);
 const additional=cwGrantSourceLink(g.url);
 const apiSource=cwGrantSourceLink(apiPageUrl);
 const identifier=cwGrantEscape(g.id||row.grant_id||'Not provided');
 const title=cwGrantEscape(g.title||'Grant award');
 return '<article class="grant-award"><div class="grant-connection"><div><span class="small muted">Funder</span><b>'+cwGrantOrganisationLabel(funder)+'</b></div><span class="grant-arrow" aria-hidden="true">→</span><div><span class="small muted">Recipient</span><b>'+cwGrantOrganisationLabel(recipient)+'</b></div></div><div class="stat">'+awarded+'</div><p class="small muted">Amount awarded · '+cwGrantEscape(g.awardDate||'Award date not published')+'</p>'+paid+'<p><strong>'+title+'</strong></p>'+(g.description?'<p class="small">'+cwGrantEscape(g.description).slice(0,450)+'</p>':'')+'<p class="small muted">Grant identifier: '+identifier+'</p><p class="small muted">'+(source?'Publisher-provided data: '+source:'Original publisher URL not provided in this record')+(additional?' · Grant details: '+additional:'')+(apiSource?' · 360Giving API results page: '+apiSource:'')+'</p></article>';
};
const cwGrantAccounting=partB=>{
 const amount=partB?.expenditure_grants_institution;
 const value=Number.isFinite(amount)?cwGrantMoney(amount):'Not disclosed';
 const period=partB?.period_end||'Not available';
 return '<div class="grant-accounting"><div class="grant-accounting-col"><span class="small muted">Charity Commission Part B</span><strong>'+value+'</strong><p class="small muted">Grants to institutions reported as expenditure · period ending '+cwGrantEscape(period)+'</p></div><div class="grant-accounting-col"><span class="small muted">360Giving published awards</span><strong id="grantAwardSummary">Not queried</strong><p id="grantAwardComparisonNote" class="small muted">Click below to retrieve grant-award records. An award is not necessarily a payment. The two sources have different coverage and reporting dates.</p></div></div>';
};
const cwGrantControls=(region,number,partB)=>{
 if(region!=='ew'||!/^\d{4,9}$/.test(String(number)))return '';
 return '<section class="grant-details" id="grant-awards"><h3>Published grant awards and recipients</h3><p class="small muted">Source: 360Giving open data, published by grantmakers. <strong>Amount awarded is not necessarily money paid.</strong> This dataset is separate from Charity Commission Part B expenditure and may cover different years. Coverage is incomplete. The cached public award sample is loaded only when you click; it may not include every award.</p>'+cwGrantAccounting(partB)+'<div class="comparison-actions"><button type="button" id="grantMade" data-grant-direction="made">Grants awarded by this charity</button><button type="button" id="grantReceived" data-grant-direction="received">Grants awarded to this charity</button></div><p id="grantAwardStatus" class="small muted" aria-live="polite">Choose a direction to look for published awards.</p><div id="grantAwardRows" class="grant-awards"></div><button type="button" id="grantAwardsMore" hidden>Load 20 more awards</button><p class="small muted">If the API cannot be accessed from this browser, use the direct 360Giving links shown in the error message. The platform does not claim complete tracing of payments.</p></section>';
};
const cwGrantBinder=(region,number)=>{
 const box=document.getElementById('grant-awards');
 if(!box)return;
 let direction=null,cached=[],offset=0,reportedTotal=null;
 const status=document.getElementById('grantAwardStatus');
 const rows=document.getElementById('grantAwardRows');
 const more=document.getElementById('grantAwardsMore');
 const summary=document.getElementById('grantAwardSummary');
 const note=document.getElementById('grantAwardComparisonNote');
 const renderMore=()=>{
  const visible=cached.slice(offset,offset+20);
  rows.insertAdjacentHTML('beforeend',visible.map(r=>cwGrantCard(r,direction,cwGrantEndpoint(region,number,direction))).join(''));
  offset+=visible.length;
  const total=reportedTotal!==null?reportedTotal.toLocaleString('en-GB')+' published awards':'Published awards';
  status.textContent=total+' · '+offset.toLocaleString('en-GB')+' of '+cached.length.toLocaleString('en-GB')+' locally cached records displayed. This is a partial sample, not the full grant history.';
  more.hidden=offset>=cached.length;
 };
 const open=async(nextDirection)=>{
  direction=nextDirection;offset=0;cached=[];rows.innerHTML='';
  more.hidden=true;
  status.textContent='Loading published award snapshot…';
  summary.textContent='Loading…';
  const apiUrl=cwGrantEndpoint(region,number,direction);
  const snapshot='data/360giving/GB-CHC-'+number+'-'+direction+'.json';
  try{
   const response=await fetch(snapshot,{cache:'no-store'});
   if(!response.ok)throw Error('Snapshot not yet available');
   const payload=await response.json();
   if(!Array.isArray(payload.results)||payload.direction!==direction)throw Error('Unexpected snapshot format');
   cached=payload.results;reportedTotal=Number.isInteger(payload.reported_count)?payload.reported_count:null;
   summary.textContent=reportedTotal!==null?reportedTotal.toLocaleString('en-GB')+' published '+(direction==='made'?'outgoing':'incoming')+' awards':'Published awards; total unknown';
   note.textContent='Up to '+cached.length+' source records cached from 360Giving. Award figures are not confirmed payments. Cache date: '+(payload.retrieved_utc||'not available')+'. Original Part B financial periods may differ.';
   if(!cached.length){
    status.textContent='No published grants found in this snapshot; coverage may be incomplete.';
    return;
   }
   renderMore();
  }catch(_){
   summary.textContent='No locally cached records';
   status.innerHTML='This charity has no current local award snapshot. <a href="'+cwGrantEscape(apiUrl)+'" target="_blank" rel="noopener noreferrer">Open 360Giving official API</a> for the original records (the API may not be viewable inside some browsers).';
  }
 };
 for(const button of box.querySelectorAll('[data-grant-direction]')){
  button.addEventListener('click',()=>open(button.dataset.grantDirection));
 }
 more.addEventListener('click',renderMore);
};
