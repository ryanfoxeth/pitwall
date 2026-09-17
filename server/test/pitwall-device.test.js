import test from 'node:test';
import assert from 'node:assert/strict';
import { deviceFeed } from '../lib/pitwall-device.js';
test('device polling shares bootstrap and uses only matching session positions',async()=>{
 let calls=0;
 const session={session_key:10,location:'Test',session_name:'Race',date_start:new Date(Date.now()-60000).toISOString(),date_end:new Date(Date.now()+60000).toISOString()};
 const service={liveRows:new Map([['10:location',[{driver_number:4,session_key:10,x:1,y:2}]],['11:location',[{driver_number:4,x:999,y:999}]]]),status:()=>({session_stale:false}),startLive:async()=>{},data:async(topic)=>{calls++;return{data:topic==='sessions'?[session]:topic==='drivers'?[{driver_number:4,name_acronym:'NOR'}]:[]};}};
 const get=deviceFeed(service);const first=await get();const before=calls;const second=await get();
 assert.equal(second.cars[0].location.x,1);assert.equal(first.cars.length,1);assert.equal(calls-before,1);assert.deepEqual(second.track,[]);
});

test('Rabbit key authorizes only the device feed',async()=>{
 const {default:express}=await import('express');const {default:router}=await import('../routes/pitwall.js');
 const old=process.env.PITWALL_DEVICE_KEY;process.env.PITWALL_DEVICE_KEY='test-rabbit-device-key';
 const s={liveRows:new Map(),status:()=>({}),startLive:async()=>{},data:async topic=>({data:topic==='sessions'?[{session_key:1,date_start:'2026-01-01T00:00:00Z',date_end:'2026-01-01T01:00:00Z',session_name:'Race'}]:[]})};
 const app=express();app.use(router({service:s,key:'master-test'}));const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));const base=`http://127.0.0.1:${server.address().port}`;
 try{assert.equal((await fetch(base+'/device')).status,401);const headers={Authorization:'Bearer test-rabbit-device-key'};assert.equal((await fetch(base+'/device',{headers})).status,200);assert.equal((await fetch(base+'/status',{headers})).status,401);}finally{await new Promise(r=>server.close(r));if(old===undefined)delete process.env.PITWALL_DEVICE_KEY;else process.env.PITWALL_DEVICE_KEY=old;}
});

test('bootstrap fills unchanged race positions before sparse live overtakes arrive',async()=>{
 const s={session_key:10,date_start:new Date(Date.now()-3600000).toISOString(),date_end:new Date(Date.now()+3600000).toISOString(),session_name:'Race'};
 const service={liveRows:new Map([['10:position',[{driver_number:3,position:17,date:'2026-09-13T13:59:00Z'}]]]),status:()=>({}),startLive:async()=>{},data:async(topic,q)=>{
 if(['position','intervals'].includes(topic))assert.ok(Date.parse(q['date<'])-Date.parse(q['date>'])<=14400000);
 return{data:topic==='sessions'?[s]:topic==='drivers'?[{driver_number:1},{driver_number:2},{driver_number:3}]:topic==='position'?[{driver_number:1,position:1,date:'2026-09-13T13:00:00Z'},{driver_number:2,position:3,date:'2026-09-13T13:00:00Z'},{driver_number:3,position:18,date:'2026-09-13T13:00:00Z'}]:topic==='intervals'?[{driver_number:2,gap_to_leader:8.869999999999999,date:'2026-09-13T13:00:00Z'}]:[]};}};
 const data=await deviceFeed(service)();assert.deepEqual(data.cars.map(c=>c.position),[1,3,17]);assert.equal(data.cars[1].gap,'8.870');
});

