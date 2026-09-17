import { createHash } from 'node:crypto';
import { officialTiming } from './pitwall-official.js';

export function eventId(key) {
 const h=createHash('sha256').update(`pitwall:${key}`).digest('hex');
 return `${h.slice(0,8)}-${h.slice(8,12)}-5${h.slice(13,16)}-a${h.slice(17,20)}-${h.slice(20,32)}`;
}
// Only observed official transitions produce alerts; bootstrapping an old feed is silent.
export class SessionAlerts {
 constructor(){this.key=null;this.previous=null;this.armed=false;this.sent=new Set();}
 poll(t){
  if(!t.connected||Date.now()-t.lastSeen>30000||!t.session||!t.status)return [];
  const qualifying=/qualifying|shootout/i.test(t.info.Name??'');
  if(qualifying&&![1,2,3].includes(t.part))return [];
  const key=`${t.session}:${qualifying?t.part:0}`;
  const status=t.status;
  if(this.key!==key){const sameSession=this.key?.split(':')[0]===String(t.session);this.key=key;this.previous=sameSession?'Inactive':null;this.armed=false;}
  const events=[];
  const label=qualifying?`${/sprint/i.test(t.info.Name)?'SQ':'Q'}${t.part}`:t.info.Name;
  const meeting=t.info.Meeting?.Name??'Formula 1';
  if(status==='Started'){
   this.armed=true;
   if(!this.previous)this.sent.add(`${key}:start`);
   if(this.previous&&this.previous!=='Started'&&!this.sent.has(`${key}:start`))events.push({key:`${key}:start`,title:`Pitwall · ${label} started`,body:`${meeting} is underway.`});
  }
  // Ends follows the chequered flag and allows final flying laps to finish.
  if(this.armed&&['Ends','Finalised'].includes(status)&&!this.sent.has(`${key}:finish`)){
   const leader=Object.entries(t.lines).find(([,v])=>Number(v.Position??v.Line)===1);
   const driver=leader&&t.drivers[leader[0]];
   const name=driver?.FullName||[driver?.FirstName,driver?.LastName].filter(Boolean).join(' ');
   const grandPrix=/^race$/i.test(t.info.Name??'');
   const topFour=[1,2,3,4].map(position=>{
    const entry=Object.entries(t.lines).find(([,v])=>Number(v.Position??v.Line)===position);
    const d=entry&&t.drivers[entry[0]];
    const fullName=d?.FullName||[d?.FirstName,d?.LastName].filter(Boolean).join(' ');
    return fullName?`${position}. ${fullName}`:null;
   });
   if(name&&(!grandPrix||topFour.every(Boolean)))events.push({key:`${key}:finish`,title:`Pitwall · ${label} finished`,body:grandPrix?`${meeting}: ${topFour.join(' · ')}. Provisional classification.`:`${name} ${/race|sprint/i.test(t.info.Name)&&!qualifying?'wins':'is fastest'} at ${meeting}. Result subject to official amendments.`});
  }
  this.previous=status;
  return events;
 }
 acknowledge(event){this.sent.add(event.key);}
}
