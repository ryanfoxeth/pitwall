import test from 'node:test';
import { once } from 'node:events';
import assert from 'node:assert/strict';
import express from 'express';
import session from 'express-session';
import { PitwallService, mergeRows, sessionMode } from '../lib/pitwall.js';
import makeRouter, { validateQuery } from '../routes/pitwall.js';
import { timingRows, seconds, escapeHTML } from '../services/pitwall/model.js';
const response = (data, status=200, headers={}) => ({ok:status<400,status,headers:new Headers(headers),json:async()=>data});

test('provider cache coalesces concurrent reads and retains stale provenance on failure',async()=>{
  let now=100,calls=0,fail=false;
  const service=new PitwallService({now:()=>now,wait:async()=>{},env:{},fetchImpl:async()=>{calls++;if(fail)throw Error('network');return response([{lap_number:1}]);}});
  const results=await Promise.all([service.open('laps',{session_key:1},10),service.open('laps',{session_key:1},10)]);
  assert.equal(calls,1);assert.deepEqual(results[0],results[1]);now=200;fail=true;
  const stale=await service.open('laps',{session_key:1},10);assert.equal(stale.stale,true);assert.equal(stale.fetched_at,results[0].fetched_at);
});
test('429 waits and retries; subscription tokens remain server-side and refresh on 401',async()=>{
  let count=0,tokens=0;const waits=[];
  const service=new PitwallService({now:()=>1000,wait:async n=>waits.push(n),env:{OPENF1_USERNAME:'user',OPENF1_PASSWORD:'secret'},fetchImpl:async url=>{
    if(url.endsWith('/token'))return response({access_token:`private-${++tokens}`,expires_in:3600});
    count++;if(count===1)return response({},401);if(count===2)return response({},429,{'retry-after':'3'});return response([]);
  }});
  const data=await service.open('drivers',{session_key:1},100);assert.equal(tokens,2);assert.equal(count,3);assert(waits.includes(3000));assert(!JSON.stringify(data).includes('private-'));
});
test('all filters constrained; high-volume feeds require bounded time windows',()=>{
  assert.throws(()=>validateQuery('unknown',{}));assert.throws(()=>validateQuery('laps',{session_key:'latest'}));assert.throws(()=>validateQuery('car_data',{session_key:'1'}));
  assert.throws(()=>validateQuery('location',{session_key:'1','date>':'2025-01-01T00:00:00Z','date<':'2025-01-01T01:00:00Z'}));
  assert.throws(()=>validateQuery('drivers',{session_key:['1','2']}));
  assert.equal(validateQuery('location',{session_key:'1','date>':'2025-01-01T00:00:00Z','date<':'2025-01-01T00:01:00Z'}).session_key,'1');
});
test('revised laps update existing REST records; out-of-order packets do not regress',()=>{
  const base={session_key:1,driver_number:4,lap_number:3,lap_duration:null};
  const rows=mergeRows('laps',[base],[{...base,lap_duration:90,_id:3},{...base,lap_duration:92,_id:2}]);
  assert.equal(rows.length,1);assert.equal(rows[0].lap_duration,90);
  const s=new PitwallService({env:{}});s.ingest('laps',[{...base,session_key:2},base]);assert.equal(s.liveRows.size,2);
});
test('timing uses completed laps, respects missing tire age and final classification',()=>{
  const f=data=>({data});const feeds={drivers:f([{driver_number:4}]),laps:f([{driver_number:4,lap_number:1,lap_duration:90},{driver_number:4,lap_number:2,lap_duration:null}]),position:f([{driver_number:4,position:2}]),session_result:f([{driver_number:4,position:1}]),stints:f([{driver_number:4,stint_number:1,lap_start:1,lap_end:1,tyre_age_at_start:0}])};
  const row=timingRows(feeds)[0];assert.equal(row.lap.lap_number,1);assert.equal(row.currentLap.lap_number,2);assert.equal(row.tireAge,1);assert.equal(row.position,1);
  feeds.stints.data[0].tyre_age_at_start=null;assert.equal(timingRows(feeds)[0].tireAge,null);assert.equal(seconds(null),'—');assert.equal(seconds(0),'0.000');assert.equal(escapeHTML('<script>'),'&lt;script&gt;');
});
test('session modes include subscription window rather than claiming all past sessions are free',()=>{
 const s={date_start:'2025-01-01T12:00:00Z',date_end:'2025-01-01T14:00:00Z'};
 assert.equal(sessionMode(s,Date.parse('2025-01-01T14:15:00Z')),'live-window');assert.equal(sessionMode(s,Date.parse('2025-01-01T15:00:00Z')),'historical');
});
test('private API rejects anonymous access, supports cookie login and locks again',async()=>{
 const service=new PitwallService({env:{}});const app=express();app.use(session({secret:'test-secret',resave:false,saveUninitialized:false}));app.use('/api/f1',makeRouter({service,key:'test-access'}));
 const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));const base=`http://127.0.0.1:${server.address().port}/api/f1`;
 try{
  assert.equal((await fetch(base+'/status')).status,401);
  assert.equal((await fetch(base+'/auth',{method:'POST',headers:{'Content-Type':'application/json'},body:'{"key":"wrong"}'})).status,401);
  const login=await fetch(base+'/auth',{method:'POST',headers:{'Content-Type':'application/json'},body:'{"key":"test-access"}'});assert.equal(login.status,200);
  const cookie=login.headers.get('set-cookie').split(';')[0];assert.equal((await fetch(base+'/status',{headers:{cookie}})).status,200);
  assert.equal((await fetch(base+'/data/car_data?session_key=1',{headers:{cookie}})).status,400);
  await fetch(base+'/logout',{method:'POST',headers:{cookie}});assert.equal((await fetch(base+'/status',{headers:{cookie}})).status,401);
  assert.equal((await fetch(base+'/status',{headers:{'x-api-key':'test-access'}})).status,200);
 }finally{server.closeAllConnections();await new Promise(r=>server.close(r));}
});

test('live SSE filters sessions and releases listener on disconnect',async()=>{
 const service=new PitwallService({env:{}});const app=express();app.use('/api/f1',makeRouter({service,key:'test-access'}));
 const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));
 const controller=new AbortController();
 try{
  const res=await fetch(`http://127.0.0.1:${server.address().port}/api/f1/stream?session_key=1`,{headers:{'x-api-key':'test-access'},signal:controller.signal});
  assert.equal(res.status,200);const reader=res.body.getReader();assert.match(new TextDecoder().decode((await reader.read()).value),/event: status/);
  service.ingest('position',{session_key:2,driver_number:4,position:1,date:'2025-01-01T00:00:00Z'});
  service.ingest('position',{session_key:1,driver_number:4,position:2,date:'2025-01-01T00:00:00Z'});
  const chunk=new TextDecoder().decode((await reader.read()).value);assert.match(chunk,/"session_key":1/);assert.doesNotMatch(chunk,/"session_key":2/);
  const removed=once(service,'removeListener',{signal:AbortSignal.timeout(2000)});controller.abort();await removed;
 }finally{controller.abort();server.closeAllConnections();await new Promise(r=>server.close(r));}
 assert.equal(service.listenerCount('data'),0);
});
test('high-frequency live samples retain newest per driver without unbounded session history',()=>{
 const service=new PitwallService({env:{}});
 for(let i=0;i<100;i++)service.ingest('location',{session_key:1,driver_number:4,date:new Date(1000*i).toISOString(),x:i});
 service.ingest('location',{session_key:1,driver_number:4,date:new Date(0).toISOString(),x:-1});
 assert.equal(service.liveRows.get('1:location').length,1);assert.equal(service.liveRows.get('1:location')[0].x,99);
});

test('OpenF1 404 for a valid query is unpublished data and can be retried after TTL',async()=>{
 let now=0,calls=0;const service=new PitwallService({env:{},now:()=>now,wait:async()=>{},fetchImpl:async()=>++calls===1?response({},404):response([{driver_number:4}])});
 const first=await service.open('pit',{session_key:1},3600000);assert.equal(first.availability,'not_published');assert.deepEqual(first.data,[]);
 now=61000;const next=await service.open('pit',{session_key:1},3600000);assert.equal(next.data.length,1);
});
