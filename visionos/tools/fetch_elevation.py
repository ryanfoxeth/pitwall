"""Build approximate circuit height profiles from independently aligned recorded laps.
Requires numpy. Raw downloaded data is cached outside the public repository.
Only profiles passing geometry and cross-lap agreement checks are applied.
"""
import argparse,hashlib,json,time,urllib.request,urllib.parse,urllib.error
from datetime import datetime,timedelta
from pathlib import Path
import numpy as np
parser=argparse.ArgumentParser();parser.add_argument('--catalog',type=Path,required=True);parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--ids',nargs='+',required=True);parser.add_argument('--apply',action='store_true');parser.add_argument('--archive',type=Path);args=parser.parse_args();args.cache.mkdir(parents=True,exist_ok=True)
archive=json.loads(args.archive.read_text()) if args.archive else None
def fetch(topic,q):
 if archive:
  if topic=='sessions':return [archive['session']]
  if topic=='laps':return [l for l in archive['feeds']['laps'] if l['driver_number']==q['driver_number']]
  if topic=='location':
   origin=datetime.fromisoformat(archive['session']['date_start']).timestamp()
   lo=datetime.fromisoformat(q['date>']).timestamp()-origin;hi=datetime.fromisoformat(q['date<']).timestamp()-origin
   return [dict(x=x,y=y,z=z) for t,x,y,z in archive['locations'].get(str(q['driver_number']),[]) if lo<t<hi]

 key=hashlib.sha256(json.dumps([topic,q],sort_keys=True).encode()).hexdigest();p=args.cache/(key+'.json')
 if p.exists():return json.loads(p.read_text())
 for attempt in range(3):
  try:
   with urllib.request.urlopen('https://api.openf1.org/v1/'+topic+'?'+urllib.parse.urlencode(q),timeout=40)as f:r=json.load(f)
   p.write_text(json.dumps(r));time.sleep(2.5);return r
  except urllib.error.HTTPError as e:
   if e.code==404:return []
   if attempt==2:raise
   time.sleep(35 if e.code==429 else 3)
 return []
def sample(p,n=512):
 p=np.vstack([p,p[0]]);d=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p[:,:2],axis=0),axis=1))];keep=np.r_[True,np.diff(d)>1e-6];p=p[keep];d=d[keep]
 return np.stack([np.interp(np.linspace(0,d[-1],n,endpoint=False),d,p[:,k])for k in range(p.shape[1])],axis=1)
def align(geo,xyz):
 g=sample(geo);v=sample(xyz);y=g[:,:2]-g[:,:2].mean(0);best=None
 for reverse in [False,True]:
  b=v[::-1]if reverse else v
  for shift in range(len(v)):
   q=np.roll(b,shift,axis=0);x=q[:,:2]-q[:,:2].mean(0);u,sv,vt=np.linalg.svd(x.T@y);rot=u@vt
   if np.linalg.det(rot)<0:continue
   scale=sv.sum()/(x*x).sum();mapped=x@rot*scale+g[:,:2].mean(0);err=np.mean(np.sum((mapped-g[:,:2])**2,axis=1))**.5
   if best is None or err<best[0]:best=(err,scale,q,mapped)
 return best
names={'madring':'Madring','baku':'Baku','marina_bay':'Singapore','americas':'Austin','rodriguez':'Mexico City','interlagos':'Interlagos','vegas':'Las Vegas','losail':'Lusail','yas_marina':'Yas Marina Circuit','albert_park':'Melbourne','shanghai':'Shanghai','suzuka':'Suzuka','miami':'Miami','villeneuve':'Montreal','catalunya':'Catalunya','red_bull_ring':'Spielberg','silverstone':'Silverstone','spa':'Spa-Francorchamps','hungaroring':'Hungaroring','zandvoort':'Zandvoort','monza':'Monza'}
rows=json.loads(args.catalog.read_text());sessions=fetch('sessions',{'year':2024,'session_name':'Qualifying'});report=[]
for cid in args.ids:
 row=next(r for r in rows if r['id']==cid)
 if cid not in names:report.append({'id':cid,'status':'no matching historical source configured'});continue
 match=[s for s in sessions if names[cid].lower() in (s['circuit_short_name']+' '+s['location']).lower()]
 if not match:report.append({'id':cid,'status':'session unavailable'});continue
 session=match[-1];key=session['session_key'];profiles=[];provenance=[];geo=np.array(row['points'],float)
 try:
  for driver in [16,1]:
   laps=fetch('laps',{'session_key':key,'driver_number':driver});laps=[l for l in laps if not l.get('is_pit_out_lap') and l.get('date_start') and 50<(l.get('lap_duration')or 0)<180];laps=sorted(laps,key=lambda l:l['lap_duration'])[:2]
   for lap in laps:
    start=datetime.fromisoformat(lap['date_start']);loc=fetch('location',{'session_key':key,'driver_number':driver,'date>':start.isoformat(),'date<':(start+timedelta(seconds=lap['lap_duration'])).isoformat()})
    if len(loc)<(60 if archive else 100):continue
    xyz=np.array([[r[k]for k in ['x','y','z']]for r in loc],float)/10
    if not np.isfinite(xyz).all() or np.linalg.norm(xyz[0,:2]-xyz[-1,:2])>150:continue
    err,scale,q,m=align(geo,xyz)
    if err>40 or not .8<scale<1.2:continue
    # Match each geographic vertex to aligned lap position; circular median
    # suppresses isolated spikes without inventing missing large-scale shape.
    ix=((geo[:,None,:2]-m[None,:,:])**2).sum(2).argmin(1);z=q[ix,2];z-=np.median(z)
    z=np.median(np.stack([np.roll(z,n)for n in [-2,-1,0,1,2]]),axis=0)
    profiles.append(z);provenance.append({'driver_number':driver,'lap_number':lap['lap_number'],'horizontal_fit_rms_m':round(err,3),'horizontal_fit_scale':round(scale,5),'samples':len(loc)})
   if len(profiles)>=3:break
  if len(profiles)<3:raise ValueError('fewer than three aligned laps')
  arr=np.array(profiles);z=np.median(arr,axis=0);rms=float(np.sqrt(np.mean((arr-z)**2)));spread=float(np.max(np.ptp(arr,axis=0)))
  if rms>5 or spread>15:raise ValueError(f'height disagreement: rms {rms:.2f}m, max spread {spread:.2f}m')
  z-=z.min();height=float(np.ptp(z))
  if height<1 or height>150:raise ValueError(f'suspect height range {height:.2f}m')
  geo[:,2]=z
  refined=[]
  for a,b in zip(geo,np.roll(geo,-1,axis=0)):
   count=max(1,int(np.ceil(np.linalg.norm(b-a)/24.5)))
   refined.extend((a+(b-a)*t/count).tolist()for t in range(count))
  geo=np.array(refined)
  src={'provider':'OpenF1 location','session_key':key,'date':session['date_start'][:10],'year':session['year'],'survey_grade':False,'units':'source tenths of a meter, per FastF1 position data convention','relative_reference':'minimum median profile height','range_m':round(height,2),'cross_lap_rms_m':round(rms,3),'max_lap_spread_m':round(spread,3),'laps':provenance,'method':'independent similarity alignment; median of three or more laps from two drivers; circular five-point median smoothing'}
  row['points']=geo.round(5).tolist();row['elevation']=f'Recorded elevation · approx. {height:.1f} m range · not surveyed';row['elevationSource']=src
  report.append({'id':cid,'status':'accepted',**src});print(cid,'ACCEPT',round(height,2),'m, agreement RMS',round(rms,3),flush=True)
 except Exception as e:report.append({'id':cid,'status':'unavailable or rejected','reason':str(e)});print(cid,'REJECT',str(e),flush=True)
 if args.apply:args.catalog.write_text(json.dumps(rows,separators=(',',':'))+'\n')
 (args.cache/'report.json').write_text(json.dumps(report,indent=2))
(args.cache/'report.json').write_text(json.dumps(report,indent=2))
