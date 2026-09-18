"""Cache attributed geographic DEM tiles and sample circuit neighborhoods.
No driver position/elevation data is used. Output is a candidate, not an automatic
replacement for engineered road surfaces (notably tunnels and bridges).
Usage: python fetch_land_terrain.py --projects PATH --output PATH [--ids ID ...]
Requires numpy and Pillow. Tile resolution is not source survey accuracy.
"""
import argparse, io, json, math, hashlib, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('--projects',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--ids',nargs='*');a=p.parse_args()
root=Path(__file__).resolve().parents[1];catalog=json.loads((root/'Sources/Resources/Season2026.json').read_text());a.output.mkdir(parents=True,exist_ok=True);cache=a.output/'tiles';cache.mkdir(exist_ok=True)
names=dict(albert_park='Melbourne',shanghai='Shanghai',suzuka='Suzuka',miami='Miami',villeneuve='Montreal',monaco='Monaco',catalunya='Barcelona',red_bull_ring='Spielberg',silverstone='Silverstone',spa='Spa',hungaroring='Hungaroring',zandvoort='Zandvoort',monza='Monza',madring='Madrid',baku='Baku',sepang='Sepang',marina_bay='Singapore',americas='Austin',rodriguez='Mexico City',interlagos='Interlagos',vegas='Las Vegas',losail='Lusail',yas_marina='Yas Marina')
projections=json.loads((root/'Assets/TerrainProjections.json').read_text())
report=[]
for c in catalog:
 cid=c['id']
 if a.ids and cid not in a.ids:continue
 out=a.output/(cid+'.json')
 expected=hashlib.sha256(json.dumps([p[:2] for p in c['points']],separators=(',',':')).encode()).hexdigest()
 assert expected==projections[cid]['catalogHorizontalSHA256'], 'Horizontal catalog changed; rebuild geographic projection'
 if out.exists() and json.loads(out.read_text()).get('catalogHorizontalSHA256')==expected:print(cid,'cached',flush=True);continue
 scene=root/'Assets/Season'/f'{cid}.json';mono=root/'Assets/Monaco/MonacoGeography.json'
 if scene.exists() or cid=='monaco':
  sd=json.loads((mono if cid=='monaco' else scene).read_text());pr=sd['projection'];origin=np.array(pr['origin']);factors=np.array(pr.get('factors',[pr.get('metersPerLongitudeDegree'),pr.get('metersPerLatitudeDegree')]),float)
 elif cid in projections:
  pr=projections[cid];expected=hashlib.sha256(json.dumps([p[:2] for p in c['points']],separators=(',',':')).encode()).hexdigest();assert expected==pr['catalogHorizontalSHA256'], 'Horizontal catalog changed; rebuild geographic projection';origin=np.array(pr['origin']);factors=np.array(pr['factors'])
 else:
  if a.projects is None:raise ValueError('Missing geographic projection for '+cid)
  sources=list((a.projects/names[cid]).glob('*source.json'));src=next(x for x in sources if 'elevated' not in x.name);geo=np.array(json.loads(src.read_text())['outline'])[:,:2];origin=geo.mean(0);factors=np.array([111320*math.cos(math.radians(origin[1])),111320])
 track=np.array(c['points']);lo=track[:,:2].min(0)-600;hi=track[:,:2].max(0)+600
 if scene.exists() or cid=='monaco':
  boundary=np.array(sd['boundary']);lo=np.minimum(lo,boundary.min(0)-25);hi=np.maximum(hi,boundary.max(0)+25)
 step=15.;xs=np.arange(lo[0],hi[0]+step,step);ys=np.arange(lo[1],hi[1]+step,step);xx,yy=np.meshgrid(xs,ys);xy=np.stack([xx,yy],axis=-1);geo=xy/factors+origin
 z=14;size=256*2**z
 def pixels(ll):return np.stack([(ll[...,0]+180)/360*size,(1-np.arcsinh(np.tan(np.radians(ll[...,1])))/math.pi)/2*size],axis=-1)-.5
 px=pixels(geo);tx0,ty0=np.floor(px.reshape(-1,2).min(0)/256).astype(int);tx1,ty1=np.floor((px.reshape(-1,2).max(0)+1)/256).astype(int);mosaic=np.zeros(((ty1-ty0+1)*256,(tx1-tx0+1)*256));sources=[]
 for ty in range(ty0,ty1+1):
  for tx in range(tx0,tx1+1):
   f=cache/f'{z}-{tx}-{ty}.png';meta=f.with_suffix('.json');url=f'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{tx}/{ty}.png'
   if not f.exists():
    with urllib.request.urlopen(url,timeout=45) as r:blob=r.read();headers=dict(r.headers)
    f.write_bytes(blob);meta.write_text(json.dumps({'url':url,'headers':headers,'sha256':hashlib.sha256(blob).hexdigest()}))
   m=json.loads(meta.read_text());h={k.lower():v for k,v in m['headers'].items()};sources.append({'url':url,'imagery':h.get('x-amz-meta-x-imagery-sources','unspecified'),'lastModified':h.get('last-modified'),'sha256':m['sha256']});rgb=np.asarray(Image.open(f),dtype=float);heights=rgb[:,:,0]*256+rgb[:,:,1]+rgb[:,:,2]/256-32768;mosaic[(ty-ty0)*256:(ty-ty0+1)*256,(tx-tx0)*256:(tx-tx0+1)*256]=heights
 def sample(ll):
  q=pixels(ll)-[tx0*256,ty0*256];ij=np.floor(q).astype(int);u,v=(q-ij).T;x,y=ij.T
  return mosaic[y,x]*(1-u)*(1-v)+mosaic[y,x+1]*u*(1-v)+mosaic[y+1,x]*(1-u)*v+mosaic[y+1,x+1]*u*v
 land=sample(geo.reshape(-1,2)).reshape(xx.shape);tz=sample(track[:,:2]/factors+origin);datum=float(tz.min());assert np.isfinite(land).all() and np.isfinite(tz).all()
 data={'id':cid,'catalogHorizontalSHA256':expected,'name':c['circuit'],'projection':{'origin':origin.tolist(),'factors':factors.tolist()},'grid':{'x0':float(xs[0]),'y0':float(ys[0]),'step':step,'heights':np.round(land,3).tolist()},'trackTerrainHeights':np.round(tz,3).tolist(),'trackDatumMeters':datum,'trackTerrainRangeMeters':float(np.ptp(tz)),'previousTelemetryRangeMeters':float(np.ptp(track[:,2])),'source':{'provider':'Mapzen Terrain Tiles / source DEMs','url':'https://registry.opendata.aws/terrain-tiles/','retrieved':'2026-09-18','method':'Terrarium RGB decoding and bilinear geographic sampling; no telemetry','zoom':z,'tilePixelSpacingMeters':math.cos(math.radians(origin[1]))*2*math.pi*6378137/size,'gridSpacingMeters':step,'survey_grade':False,'road_surface':False,'tiles':sources,'limitations':'Composite geographic elevation, not a road survey. Source age/resolution varies. Structures, vegetation, bridges, tunnels and recent grading require separate treatment. Resampling does not improve native accuracy.','attribution':'https://github.com/tilezen/joerd/blob/master/docs/attribution.md'}}
 out.write_text(json.dumps(data,separators=(',',':')));print(cid,'DEM range',round(np.ptp(tz),2),'previous',round(np.ptp(track[:,2]),2),set(s['imagery'].split('/')[0] for s in sources),flush=True)
