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
const cwGrantCard=(row,direction)=>{
 const g=row?.data;
 if(!g||typeof g!=='object')return '';
 const who=direction==='made'?g.recipientOrganization?.[0]:g.fundingOrganization?.[0];
 const orgName=who?.name||'Recipient organisation not stated';
 const award=g.amountAwarded;
 const orgId=who?.id||'';
 const registered=/^GB-CHC-(\d{4,9})$/.exec(orgId);
 const name=cwGrantEscape(orgName);
 const heading=registered?'<a href="#charity/ew/'+registered[1]+'">'+name+'</a>':name;
 const amount=g.currency==='GBP'?cwGrantMoney(award):Number.isFinite(award)?cwGrantEscape(award)+' '+cwGrantEscape(g.currency||'currency unspecified'):'Not reported';
 const source=cwGrantSourceLink(g.dataSource);
 return '<article class="grant-award"><b>'+heading+'</b><strong>'+amount+'</strong><p class="small muted">Awarded '+cwGrantEscape(g.awardDate||'date not published')+' · '+cwGrantEscape(g.title||'Grant')+'</p>'+(g.description?'<p class="small">'+cwGrantEscape(g.description).slice(0,450)+'</p>':'')+'<p class="small muted">Grant ID: '+cwGrantEscape(g.id||row.grant_id||'Not provided')+(source?' · '+source:'')+'</p></article>';
};
const cwGrantControls=(region,number)=>{
 if(region!=='ew'||!/^\d{4,9}$/.test(String(number)))return '';
 return '<section class="grant-details" id="grant-awards"><h3>Published grant awards and recipients</h3><p class="small muted">Source: 360Giving open data, published by grantmakers. <strong>Amount awarded is not necessarily money paid.</strong> This dataset is separate from Charity Commission Part B expenditure and may cover different years. Coverage is incomplete. The API is queried only when you click.</p><div class="comparison-actions"><button type="button" id="grantMade" data-grant-direction="made">Grants awarded by this charity</button><button type="button" id="grantReceived" data-grant-direction="received">Grants awarded to this charity</button></div><p id="grantAwardStatus" class="small muted" aria-live="polite">Choose a direction to look for published awards.</p><div id="grantAwardRows" class="grant-awards"></div><button type="button" id="grantAwardsMore" hidden>Load 20 more awards</button><p class="small muted">If the API cannot be accessed from this browser, use the direct 360Giving links shown in the error message. The platform does not claim complete tracing of payments.</p></section>';
};
const cwGrantBinder=(region,number)=>{
 const box=document.getElementById('grant-awards');
 if(!box)return;
 let direction=null,offset=0,request=0,loading=false;
 const status=document.getElementById('grantAwardStatus');
 const rows=document.getElementById('grantAwardRows');
 const more=document.getElementById('grantAwardsMore');
 const fetchPage=async(reset=false)=>{
  if(loading)return;
  const url=cwGrantEndpoint(region,number,direction,offset);
  if(!url)return;
  const token=++request;
  loading=true;more.hidden=true;
  status.textContent='Checking published grants…';
  try{
   const response=await fetch(url,{headers:{Accept:'application/json'}});
   if(response.status===404){rows.innerHTML='';status.textContent='No organisation record was found in the 360Giving dataset. This does not mean the charity has no grants.';return;}
   if(!response.ok)throw Error('360Giving returned HTTP '+response.status);
   const payload=await response.json();
   if(token!==request||!Array.isArray(payload.results))return;
   const cards=payload.results.map(r=>cwGrantCard(r,direction)).filter(Boolean);
   if(reset)rows.innerHTML='';
   rows.insertAdjacentHTML('beforeend',cards.join(''));
   offset+=payload.results.length;
   const total=typeof payload.count==='number'?payload.count:null;
   status.textContent=(total!==null?total.toLocaleString('en-GB')+' published awards':'Published awards')+' · '+offset+' records loaded. Reporting coverage is not exhaustive.';
   if(!cards.length&&reset)rows.innerHTML='<p class="muted">No published organisation grants found for this query.</p>';
   more.hidden=!payload.next||payload.results.length===0;
  }catch(e){
   const external=cwGrantEndpoint(region,number,direction,offset);
   status.innerHTML='Direct 360Giving API request unavailable (network, rate limit or browser access restrictions). <a href="'+cwGrantEscape(external)+'" target="_blank" rel="noopener noreferrer">View these published records at 360Giving</a>.';
  }finally{loading=false;}
 };
 for(const button of box.querySelectorAll('[data-grant-direction]')){
  button.addEventListener('click',()=>{
   if(loading)return;
   direction=button.dataset.grantDirection;
   offset=0;rows.innerHTML='';
   fetchPage(true);
  });
 }
 more.addEventListener('click',()=>fetchPage());
};
