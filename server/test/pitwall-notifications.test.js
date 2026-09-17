import test from 'node:test';
import assert from 'node:assert/strict';
import {SessionAlerts,eventId} from '../lib/pitwall-notifications.js';
const state=()=>({connected:true,lastSeen:Date.now(),session:'123',status:'Inactive',info:{Name:'Race',Meeting:{Name:'Spanish Grand Prix'}},lines:{44:{Position:'1'},63:{Position:'2'},3:{Position:'3'},1:{Position:'4'}},drivers:{44:{FullName:'Lewis Hamilton'},63:{FullName:'George Russell'},3:{FullName:'Max Verstappen'},1:{FullName:'Lando Norris'}}});
test('start, red flag resume, finish, and durable key',()=>{
 const a=new SessionAlerts(),t=state();assert.deepEqual(a.poll(t),[]);
 t.status='Started';let events=a.poll(t);assert.equal(events.length,1);a.acknowledge(events[0]);
 t.status='Aborted';a.poll(t);t.status='Started';assert.deepEqual(a.poll(t),[]);
 t.status='Finished';assert.deepEqual(a.poll(t),[]);
 t.status='Ends';events=a.poll(t);assert.match(events[0].body,/1. Lewis Hamilton · 2. George Russell · 3. Max Verstappen · 4. Lando Norris/);a.acknowledge(events[0]);assert.deepEqual(a.poll(t),[]);
 assert.equal(eventId('123:0:finish'),eventId('123:0:finish'));
});
test('mid-race bootstrap is silent but finish is observed; old finished sessions silent',()=>{
 const a=new SessionAlerts(),t=state();t.status='Started';assert.deepEqual(a.poll(t),[]);
 t.status='Aborted';a.poll(t);t.status='Started';assert.deepEqual(a.poll(t),[]);
 t.status='Finalised';assert.equal(a.poll(t).length,1);
 assert.deepEqual(new SessionAlerts().poll(t),[]);
});
test('qualifying segments have independent notifications',()=>{
 const a=new SessionAlerts(),t=state();t.info.Name='Sprint Qualifying';t.part=1;a.poll(t);t.status='Started';let e=a.poll(t);assert.match(e[0].title,/SQ1 started/);a.acknowledge(e[0]);
 t.status='Ends';e=a.poll(t);assert.match(e[0].body,/is fastest/);a.acknowledge(e[0]);
 t.part=2;t.status='Started';e=a.poll(t);assert.match(e[0].title,/SQ2 started/);
});
test('withheld, stale and missing winner suppress alerts',()=>{
 const a=new SessionAlerts(),t=state();a.poll(t);t.status='Started';a.poll(t);t.status='Ends';t.connected=false;assert.deepEqual(a.poll(t),[]);t.connected=true;t.lines={};assert.deepEqual(a.poll(t),[]);
});
