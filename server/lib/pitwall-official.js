import WebSocket from 'ws';
// Official SignalR Core timing topics. Same public negotiation used by FastF1.
export class OfficialTiming {
 constructor(){this.info={};this.part=null;this.status=null;this.drivers={};this.session=null;this.lines={};this.laps={};this.lastSeen=0;this.connected=false;this.enabled=false;}
 apply(topic,data){
  if(topic==='SessionInfo'&&data.Key){if(this.session!==String(data.Key)){this.lines={};this.laps={};this.status=null;this.part=null;this.drivers={};this.info={};}this.info={...this.info,...data};this.session=String(data.Key);}
  if(topic==='SessionData')for(const row of Object.values(data.Series??{}))if(row.QualifyingPart)this.part=Number(row.QualifyingPart);
  if(topic==='SessionStatus')this.status=data.Status??this.status;
  if(topic==='DriverList')for(const [id,row] of Object.entries(data))this.drivers[id]={...this.drivers[id],...row};
  if(topic==='LapCount')this.laps={...this.laps,...data};
  if(topic==='TimingData'&&data.Withheld){this.lines={};this.connected=false;return;}
  if(topic==='TimingData'&&data._kf)this.lines={};
  if(topic==='TimingData'&&this.session&&!data.Withheld){for(const [id,row] of Object.entries(data.Lines??{})){const old=this.lines[id]??{};const fields={};for(const key of ['Retired','InPit','Position','Line','GapToLeader','NumberOfLaps'])if(key in row)fields[key]=row[key];if(row.IntervalToPositionAhead&&'Value' in row.IntervalToPositionAhead)fields.interval=row.IntervalToPositionAhead.Value;this.lines[id]={...old,...fields};}}
 }
 snapshot(key){return this.session===String(key)?{lines:this.lines,laps:this.laps,stale:!this.connected||Date.now()-this.lastSeen>30000}:null;}
 async start(){
  this.enabled=true;if(this.socket||this.starting||this.retryTimer)return;this.starting=true;
  try{
   const url='https://livetiming.formula1.com/signalrcore/negotiate';
   const pre=await fetch(url,{method:'OPTIONS',signal:AbortSignal.timeout(15000)});
   let cookie=pre.headers.getSetCookie().map(c=>c.split(';')[0]).join('; ');
   const response=await fetch(url+'?negotiateVersion=1',{method:'POST',headers:{Cookie:cookie},signal:AbortSignal.timeout(15000)});
   if(!response.ok)throw Error('Official timing negotiation unavailable');
   cookie+='; '+response.headers.getSetCookie().map(c=>c.split(';')[0]).join('; ');
   const auth=await response.json();if(!auth.connectionToken)throw Error('No connection token');
   if(!this.enabled)return;
   const ws=new WebSocket('wss://livetiming.formula1.com/signalrcore?id='+encodeURIComponent(auth.connectionToken),{headers:{Cookie:cookie},maxPayload:2_000_000,handshakeTimeout:15000});this.socket=ws;
   const send=x=>{if(ws.readyState===WebSocket.OPEN)ws.send(JSON.stringify(x)+'\x1e');};let subscribed=false;
   ws.on('open',()=>{send({protocol:'json',version:1});this.ping=setInterval(()=>send({type:6}),10000);this.ping.unref?.();});
   ws.on('message',raw=>{this.lastSeen=Date.now();try{for(const part of String(raw).split('\x1e').filter(Boolean)){const msg=JSON.parse(part);if(!subscribed&&!msg.type){subscribed=true;send({type:1,invocationId:'1',target:'Subscribe',arguments:[['SessionInfo','TimingData','LapCount','SessionStatus','DriverList','SessionData']]});}if(msg.type===3&&msg.result){this.apply('SessionInfo',msg.result.SessionInfo??{});for(const topic of ['TimingData','LapCount','SessionStatus','DriverList','SessionData'])if(msg.result[topic])this.apply(topic,msg.result[topic]);this.connected=Boolean(msg.result.TimingData?.Lines)&&!msg.result.TimingData?.Withheld;}if(msg.type===1&&msg.target?.toLowerCase()==='feed'){const [topic,data]=msg.arguments;this.apply(topic,typeof data==='string'?JSON.parse(data):data);}if(msg.type===7)ws.close();}}catch{this.connected=false;}});
   ws.on('error',()=>{this.connected=false;ws.close();});
   ws.on('close',()=>{clearInterval(this.ping);this.connected=false;this.socket=null;this.retry();});
  }catch{this.connected=false;this.retry();}finally{this.starting=false;}
 }
 retry(){if(this.enabled&&!this.retryTimer){this.retryTimer=setTimeout(()=>{this.retryTimer=null;this.start();},10000);this.retryTimer.unref?.();}}
 stop(){this.enabled=false;clearTimeout(this.retryTimer);this.retryTimer=null;clearInterval(this.ping);this.socket?.close();this.connected=false;}
}

export const officialTiming = new OfficialTiming();
