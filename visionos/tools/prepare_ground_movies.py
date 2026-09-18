"""Prepare movie scene inputs from mapped scenery and geographic ground models.
Keeps app assets unchanged until movie terrain has been reviewed.
"""
import json,sys,numpy as np
from pathlib import Path
from terrain_grid import TerrainGrid
scenes,terrain,out=map(Path,sys.argv[1:4]);osm_cache=Path(sys.argv[4]) if len(sys.argv)>4 else scenes.parent/'pitwall-season';out.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[1];report=[]
for c in json.loads((root/'Sources/Resources/Season2026.json').read_text()):
 cid=c['id'];d=json.loads((root/'Assets/Monaco/MonacoGeography.json' if cid=='monaco' else scenes/(cid+'.json')).read_text());t=json.loads((terrain/(cid+'.json')).read_text());grid=TerrainGrid(t);old=np.array(d['track']);track=old.copy();track[:,2]=np.array(t['trackTerrainHeights'])-t['trackDatumMeters']
 adjustments=[]
 # Coarse terrain samples must not become roof-sized steps in a road.
 # A separate, explicitly modeled longitudinal grade leaves the land grid intact.
 ds=np.linalg.norm(np.roll(track[:,:2],-1,axis=0)-track[:,:2],axis=1)
 rawgrade=np.abs(np.roll(track[:,2],-1)-track[:,2])/np.maximum(.1,ds)
 if t['source'].get('groundModel')!='National terrain DEM' or rawgrade.max()>.20:
  station=np.r_[0,np.cumsum(ds[:-1])];dist=np.abs(station[:,None]-station);dist=np.minimum(dist,ds.sum()-dist);weights=np.exp(-.5*(dist/45)**2)*ds[None,:];track[:,2]=(weights@track[:,2])/weights.sum(1)
  adjustments.append('Road grade is a 45m-sigma distance-weighted smoothing of geographic terrain samples; approximate engineered surface. Terrain grid remains unchanged.')
 if cid=='suzuka':
  # OSM way 175231434 identifies the elevated raceway at the crossover.
  osm=json.loads((osm_cache/'suzuka-osm.json').read_text());way=next(e for e in osm['elements'] if e['id']==175231434);pr=t['projection'];bridge=(np.array([[v['lon'],v['lat']] for v in way['geometry']])-pr['origin'])*pr['factors'];center=bridge.mean(0);axis=bridge[-1]-bridge[0];axis/=np.linalg.norm(axis);tangent=np.roll(track[:,:2],-1,axis=0)-np.roll(track[:,:2],1,axis=0);tangent/=np.maximum(.001,np.linalg.norm(tangent,axis=1))[:,None];score=np.linalg.norm(track[:,:2]-center,axis=1)+200*(1-np.abs(tangent@axis));idx=int(score.argmin());station=np.r_[0,np.cumsum(ds[:-1])];dist=np.abs(station-station[idx]);dist=np.minimum(dist,ds.sum()-dist);track[:,2]+=6*np.exp(-.5*(dist/65)**2);d['modeledBridge']={'osm':175231434,'center':center.tolist(),'clearance_m':6,'note':'OSM bridge location; assumed 6m separation, not surveyed'};adjustments.append('Suzuka crossover: mapped elevated branch, modeled 6m separation; not surveyed.')
 if cid=='monaco':
  # Underground route follows the mapped tunnel portals, not the land above it.
  ends=np.array([d['tunnel'][0],d['tunnel'][-1]]);indices=[int(np.argmin(((track[:,:2]-e)**2).sum(1))) for e in ends];i,j=sorted(indices)
  if j-i>len(track)//2:indices=list(range(j,len(track)))+list(range(i+1))
  else:indices=list(range(i,j+1))
  path=track[indices];dist=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path[:,:2],axis=0),axis=1))];track[indices,2]=np.interp(dist,[0,dist[-1]],[path[0,2],path[-1,2]])
  adjustments.append('Tunnel grade interpolated between terrain-sampled mapped portals; modeled, not surveyed.')
 # Terrain datum is preserved for track, ground and buildings; never renormalize each independently.
 d['track']=track.round(4).tolist();d['id']=cid;d['name']=c['circuit'];d['event']=c['name'];d['terrainGrid']=t;d['elevation']=t['source']['provider'];d['groundSource']=t['source'];d['engineeringNotes']=adjustments
 for tri in d['terrain']:
  for p in tri:p[2]=round(grid.height(*p[:2])-.6,3)
 for b in d['buildings']+d['landmarks']:
  pp=np.array(b['footprint']);center=b.get('center',pp.mean(0));base=grid.height(*center);change=base-b['base'];b['base']=base
  for tier in b.get('supportTiers',[]):tier['top']+=change;tier['bottom']+=change
 # Water stays horizontal at the mapped shoreline's median ground height.
 waterPoints=[p for tri in d.get('waterTriangles',[]) for p in tri];d['waterLevel']=float(np.percentile([grid.height(*p[:2]) for p in waterPoints],15)-.8) if waterPoints else 0
 d['notes']='Mapped OSM surroundings; geographic ground model, no car telemetry heights. Terrain/road detail below source resolution and engineered structures remain approximate.'
 (out/(cid+'.json')).write_text(json.dumps(d,separators=(',',':')));report.append({'id':cid,'provider':t['source']['provider'],'terrainRangeMeters':round(t['trackTerrainRangeMeters'],3),'roadRangeMeters':round(float(np.ptp(track[:,2])),3),'engineeringNotes':adjustments});print(cid,'prepared',flush=True)
(out/'terrain-report.json').write_text(json.dumps(report,indent=2))
