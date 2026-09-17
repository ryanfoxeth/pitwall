import sys
SESSION=int(sys.argv[1]) if len(sys.argv)>1 else 11369
import json,urllib.request,urllib.parse,urllib.error,time,bisect
from pathlib import Path
from datetime import datetime,timedelta
P=Path(__file__).resolve().parent.parent;C=P/'tools/cache';C.mkdir(exist_ok=True)
def fetch(topic,q):
 key=topic+'-'+str(abs(hash(json.dumps(q,sort_keys=True))))
 path=C/(topic+'-'+urllib.parse.quote(json.dumps(q,sort_keys=True),safe='')+'.json')
 if path.exists():return json.loads(path.read_text())
 for n in range(5):
  try:
   with urllib.request.urlopen('https://api.openf1.org/v1/'+topic+'?'+urllib.parse.urlencode(q),timeout=90)as r:d=json.load(r)
   path.write_text(json.dumps(d));return d
  except urllib.error.HTTPError as e:
   if e.code==404 and topic=="location":return []
   if n==4:raise
   time.sleep(2+n*2)
  except Exception:
   if n==4:raise
   time.sleep(2+n*2)
def ts(s):return datetime.fromisoformat(s).timestamp() if s else None
session=fetch('sessions',{'session_key':SESSION})[0];start=ts(session['date_start']);end=ts(session['date_end']);feeds={}
for topic in ['drivers','laps','stints','race_control','weather','pit','position','intervals','session_result','team_radio','overtakes']:
 try:feeds[topic]=fetch(topic,{'session_key':SESSION});print(topic,len(feeds[topic]),flush=True)
 except Exception as e:feeds[topic]=[];print(topic,str(e),flush=True)
locations=[]
for sec in range(0,int(end-start),300):
 q={'session_key':SESSION,'date>':datetime.fromtimestamp(start+sec-0.001).isoformat()+'Z','date<':datetime.fromtimestamp(min(end,start+sec+300)).isoformat()+'Z'}
 # timezone-safe UTC strings
 from datetime import timezone
 q['date>']=datetime.fromtimestamp(start+sec-.001,timezone.utc).isoformat();q['date<']=datetime.fromtimestamp(min(end,start+sec+300),timezone.utc).isoformat()
 rows=fetch('location',q);locations.extend(rows);print('locations',sec,len(rows),flush=True)
# Compact position samples at 1Hz, keeping observed timestamps and actual source coordinates.
loc={};last={}
for r in sorted(locations,key=lambda x:x['date']):
 n=str(r['driver_number']);t=ts(r['date'])-start;bucket=int(t)
 if last.get(n)==bucket:continue
 last[n]=bucket;loc.setdefault(n,[]).append([round(t,3),r['x'],r['y'],r['z']])
# A measured lap supplies geometry in precisely the same coordinate system.
lap=next(l for l in feeds['laps'] if l.get('lap_number',0)>1 and 30 < (l.get('lap_duration') or 0) < 300 and not l.get('is_pit_out_lap'))
a=ts(lap['date_start'])-start;b=a+lap['lap_duration'];track=[[r['x'],r['y'],r['z']]for r in locations if r['driver_number']==lap['driver_number'] and a<=ts(r['date'])-start<=b]
for topic,rows in feeds.items():
 for r in rows:
  for k in ['date','date_start','date_end']:
   if r.get(k):r[k+'_seconds']=round(ts(r[k])-start,3)
archive={'session':session,'duration':min(end-start,max(p[0] for samples in loc.values() for p in samples)),'locations':loc,'track':track,'feeds':feeds,'provenance':'User-downloaded OpenF1 historical session. Positions sampled at 1 Hz; interpolated only across gaps <= 5s. Recorded XYZ are approximate, not survey geometry.'}
out=P/'Sources/Resources/MadridReplay.json';out.write_text(json.dumps(archive,separators=(',',':')));print('DONE',out.stat().st_size,flush=True)
