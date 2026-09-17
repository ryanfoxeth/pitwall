import test from 'node:test';
import assert from 'node:assert/strict';
import {OfficialTiming} from '../lib/pitwall-official.js';
import {deviceFeed} from '../lib/pitwall-device.js';
test('official timing merges sparse updates and isolates session changes',()=>{
 const f=new OfficialTiming();f.apply('SessionInfo',{Key:1});f.apply('TimingData',{Lines:{44:{Retired:true,InPit:true,Position:'22',IntervalToPositionAhead:{Value:'+3.1'}}}});f.apply('TimingData',{Lines:{44:{InPit:false}}});assert.equal(f.lines[44].Retired,true);assert.equal(f.lines[44].InPit,false);assert.equal(f.lines[44].interval,'+3.1');assert.equal(f.snapshot(2),null);f.apply('SessionInfo',{Key:2});assert.deepEqual(f.lines,{});
});
test('OUT and IN PIT come from official flags, never stopped movement',async()=>{
 const f=new OfficialTiming();f.apply('SessionInfo',{Key:1});f.apply('TimingData',{Lines:{44:{Retired:true,InPit:true,Position:'22'},18:{Retired:false,InPit:false,Stopped:true,Position:'21'},11:{Retired:false,InPit:true,Position:'20'}}});f.connected=true;f.lastSeen=Date.now();
 const s={liveRows:new Map(),status:()=>({}),startLive:async()=>{},data:async topic=>({data:topic==='sessions'?[{session_key:1,date_start:'2026-01-01',date_end:'2026-01-02',session_name:'Race'}]:topic==='drivers'?[{driver_number:44},{driver_number:18},{driver_number:11}]:[]})};
 const result=await deviceFeed(s,f)();assert.equal(result.cars.find(c=>c.number===44).status,'OUT');assert.equal(result.cars.find(c=>c.number===18).status,null);assert.equal(result.cars.find(c=>c.number===11).status,'IN PIT');assert.deepEqual(result.cars.map(c=>c.position),[20,21,22]);f.connected=false;const stale=await deviceFeed(s,f)();assert.equal(stale.status_feed,'Unavailable');assert.equal(stale.cars.find(c=>c.number===44).status,null);
});
