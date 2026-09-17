import { officialTiming } from './pitwall-official.js';
import { sessionMode, mergeRows } from './pitwall.js';
import { timingRows } from '../services/pitwall/model.js';

// One shared bootstrap per session; device polling reads MQTT memory, not the provider.
export function deviceFeed(service, official = officialTiming) {
 let cached=null,pending=null,expires=0;
 return async (requested)=>{
  const sessions=(await service.data('sessions',{year:String(new Date().getFullYear())})).data;
  const eligible=sessions.filter(s=>Date.parse(s.date_start)<=Date.now()).sort((a,b)=>Date.parse(a.date_start)-Date.parse(b.date_start));
  const selected=requested?sessions.find(s=>String(s.session_key)===requested):eligible.at(-1);
  if(!selected)throw new Error('No session available');
  const key=String(selected.session_key);
  if(sessionMode(selected)==='live-window'){await service.startLive();if(service.configured && service.env?.PITWALL_OFFICIAL_ENABLED === "true")void official.start();}
  if(!cached||cached.key!==key||Date.now()>expires){
   if(!pending){pending=(async()=>{
    const feeds={};await Promise.all(['drivers','position','intervals','laps','stints','weather','race_control','pit','session_result','starting_grid','team_radio','overtakes','championship_drivers','championship_teams'].map(async topic=>{try{feeds[topic]=['championship_drivers','championship_teams'].includes(topic)&&selected.session_name!=='Race'?{data:[]}:await service.data(topic,['position','intervals'].includes(topic)?{session_key:key,'date>':new Date(Math.max(Date.parse(selected.date_start)-1,Math.min(Date.now(),Date.parse(selected.date_end))-14399999)).toISOString(),'date<':new Date(Math.min(Date.now(),Date.parse(selected.date_end))).toISOString()}:{session_key:key});}catch{feeds[topic]={...(cached?.key===key?cached.feeds[topic]:null),data:cached?.key===key?(cached.feeds[topic]?.data??[]):[],error:'Unavailable'};}}));
    let track=cached?.key===key?cached.track:[];
    if(!track.length){const lap=feeds.laps.data.find(l=>l.date_start&&l.lap_duration>30&&l.lap_duration<=300&&l.lap_number>1&&!l.is_pit_out_lap);if(lap){try{const start=Date.parse(lap.date_start);track=(await service.data('location',{session_key:key,driver_number:String(lap.driver_number),'date>':new Date(start).toISOString(),'date<':new Date(start+lap.lap_duration*1000).toISOString()})).data.filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y));const stride=Math.max(1,Math.ceil(track.length/450));track=track.filter((_,i)=>i%stride===0).map(p=>({x:p.x,y:p.y}));}catch{}}}
    cached={key,feeds,track};expires=Date.now()+60000;
   })().finally(()=>pending=null);}
   await pending;
   if(cached.key!==key)return {session:selected,track:[],cars:[],messages:[],status:'loading',sessions:[]};
  }
  const feeds=Object.fromEntries(Object.entries(cached.feeds).map(([topic,f])=>[topic,{...f,data:mergeRows(topic,f.data,service.liveRows.get(`${key}:${topic}`)??[])}]));
  const location=service.liveRows.get(`${key}:location`)??[],telemetry=service.liveRows.get(`${key}:car_data`)??[];
  const cars=timingRows(feeds,{useResults:sessionMode(selected)==='historical'}).map(d=>({number:d.driver_number,name:d.name_acronym,full_name:d.full_name,team:d.team_name,color:d.team_colour,position:d.position??null,interval:typeof d.interval?.interval==='number'?d.interval.interval.toFixed(1):d.interval?.interval??null,status:d.result?.dsq?'DSQ':d.result?.dns?'DNS':d.result?.dnf?'OUT':null,status_source:d.result?'OpenF1 session result':null,gap:typeof d.interval?.gap_to_leader==='number'?d.interval.gap_to_leader.toFixed(3):d.interval?.gap_to_leader??null,lap:d.lap?.lap_number??null,last_lap:d.lap?.lap_duration??null,compound:d.stint?.compound??null,tire_age:d.tireAge??null,location:location.find(p=>p.driver_number===d.driver_number)??null,telemetry:telemetry.find(p=>p.driver_number===d.driver_number)??null}));
  const timing=official.snapshot(key);
  if(timing&&!timing.stale){for(const car of cars){const row=timing.lines[car.number];if(!row)continue;const position=Number(row.Position??row.Line);if(Number.isInteger(position)&&position>0)car.position=position;if(row.interval!=null)car.interval=row.interval;if(row.GapToLeader!=null)car.gap=row.GapToLeader;car.status=row.Retired===true?'OUT':row.InPit===true?'IN PIT':car.status;car.status_source='Formula 1 live TimingData';}cars.sort((a,b)=>(a.position??999)-(b.position??999));}
  return {session:selected,status_feed:timing&&!timing.stale?'Formula 1 live TimingData':'Unavailable',total_laps:timing?.laps.TotalLaps??null,current_lap:timing?.laps.CurrentLap??Math.max(0,...cars.map(c=>c.lap??0)),mode:sessionMode(selected),live:service.status(key),track:cached.track,cars,weather:feeds.weather.data.at(-1)??null,messages:feeds.race_control.data.slice(-30).reverse(),feeds,sessions:eligible.slice(-30).reverse(),fetched_at:new Date().toISOString()};
 };
}
