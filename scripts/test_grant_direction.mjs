#!/usr/bin/env node
// Reproduce out-of-order 360Giving responses without a browser or network.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync('assets/grant-links.js', 'utf8');
const elements = new Map();
const node = id => {
  if (!elements.has(id)) elements.set(id, {
    innerHTML: '', textContent: '', hidden: false,
    listeners: {},
    addEventListener(event, callback) { this.listeners[event] = callback; },
    insertAdjacentHTML(_position, html) { this.innerHTML += html; },
    querySelectorAll() { return []; },
  });
  return elements.get(id);
};
const outgoing = node('grantMade');
const incoming = node('grantReceived');
outgoing.dataset = {grantDirection:'made'};
incoming.dataset = {grantDirection:'received'};
node('grant-awards').querySelectorAll = () => [outgoing, incoming];

const deferred = new Map();
const mockFetch = url => new Promise(resolve => {
  const match = /-(made|received)\.json$/.exec(url);
  assert.ok(match, 'Unexpected URL: ' + url);
  deferred.set(match[1], resolve);
});
const context = {document:{getElementById:node}, fetch:mockFetch, URL, Intl, Number, console};
vm.createContext(context);
new vm.Script(source + '\n;globalThis.bindForTest = cwGrantBinder;', {filename:'grant-links.js'}).runInContext(context);
context.bindForTest('ew','802052');

function answer(direction,title){
  deferred.get(direction)({
    ok:true,
    json:async()=>({
      direction,
      organisation_id:'GB-CHC-802052',
      retrieved_utc:'2026-11-14T00:00:00+00:00',
      reported_count:1,
      records_cached:1,
      partial:false,
      results:[{data:{title, currency:'GBP', amountAwarded:100}}],
    }),
  });
}
const flush = async()=>{for(let i=0;i<5;i++)await Promise.resolve();};

outgoing.listeners.click();
incoming.listeners.click();
answer('received','MOST RECENT INCOMING AWARD');
await flush();
answer('made','STALE OUTGOING AWARD');
await flush();
assert.match(node('grantAwardRows').innerHTML,/MOST RECENT INCOMING AWARD/);
assert.doesNotMatch(node('grantAwardRows').innerHTML,/STALE OUTGOING AWARD/);
assert.match(node('grantAwardSummary').textContent,/incoming awards/);

incoming.listeners.click();
outgoing.listeners.click();
answer('made','NEW OUTGOING AWARD');
await flush();
answer('received','STALE INCOMING AWARD');
await flush();
assert.match(node('grantAwardRows').innerHTML,/NEW OUTGOING AWARD/);
assert.doesNotMatch(node('grantAwardRows').innerHTML,/STALE INCOMING AWARD/);
assert.match(node('grantAwardSummary').textContent,/outgoing awards/);
console.log('PASS: stale 360Giving responses cannot overwrite the latest selected grant direction');
