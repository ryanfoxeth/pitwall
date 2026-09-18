"""Upgrade Monaco with IGN RGE ALTI ground samples; retain explicit fallback masks.
Usage: python fetch_monaco_ground.py GROUND_DIRECTORY
"""
import json,sys,time,urllib.request
from pathlib import Path
import numpy as np
folder=Path(sys.argv[1]);path=folder/'monaco.json';d=json.loads(path.read_text());g=d['grid'];pr=d['projection'];old=np.array(g['heights']);xx,yy=np.meshgrid(g['x0']+np.arange(old.shape[1])*g['step'],g['y0']+np.arange(old.shape[0])*g['step']);geo=np.stack([xx,yy],-1)/pr['factors']+pr['origin'];c=next(x for x in json.loads((Path(__file__).resolve().parents[1]/'Sources/Resources/Season2026.json').read_text()) if x['id']=='monaco');ll=np.vstack([geo.reshape(-1,2),np.array(c['points'])[:,:2]/pr['factors']+pr['origin']]);cache=folder/'monaco-ign';cache.mkdir(exist_ok=True);rows=[];url='https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json'
for start in range(0,len(ll),4000):
 f=cache/f'{start}.json';q=ll[start:start+4000]
 if not f.exists():
  body={'lon':'|'.join(f'{p[0]:.8f}' for p in q),'lat':'|'.join(f'{p[1]:.8f}' for p in q),'resource':'ign_rge_alti_wld','measures':'true','zonly':'false'};req=urllib.request.Request(url,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
  for attempt in range(3):
   try:
    r=json.load(urllib.request.urlopen(req,timeout=80));assert len(r['elevations'])==len(q);f.write_text(json.dumps(r));break
   except Exception:
    if attempt==2:raise
    time.sleep(3)
  time.sleep(.3)
 rows+=json.loads(f.read_text())['elevations'];print(start,len(rows),'/',len(ll),flush=True)
z=np.array([r['z'] for r in rows]);grid=z[:old.size].reshape(old.shape);missing=grid<-1000;grid[missing]=old[missing];subsea=int((grid<0).sum());grid=np.maximum(grid,0);tz=z[old.size:];assert np.isfinite(tz).all() and tz.min()>-1000
np.savez_compressed(folder/'monaco-source.npz',heights=grid,fallbackMask=missing,observedTrack=tz);d['grid']['heights']=grid.round(3).tolist();d['trackTerrainHeights']=tz.tolist();d['trackTerrainRangeMeters']=float(np.ptp(tz));d['trackDatumMeters']=float(tz.min());d['source']={'provider':'IGN RGE ALTI via Géoplateforme','url':url,'resource':'ign_rge_alti_wld','license':'Licence Ouverte / Open Licence Etalab','groundModel':'National terrain DEM','survey_grade':False,'road_surface':False,'retrieved':'2026-09-18','gridSpacingMeters':g['step'],'method':'Geographic ground-elevation API with per-sample source metadata; no telemetry','fallbackCells':int(missing.sum()),'totalGridCells':int(old.size),'subSeaCellsFlooredForLandScene':subsea,'fallbackProvider':'OpenGeoHub GEDTM30 v1.2, CC-BY-4.0, https://doi.org/10.5281/zenodo.18887460','limitations':'Sub-sea samples are floored at sea level for this land-only scene. Accuracy varies by contributing IGN source; not a certified road survey. Tunnels and retaining structures require separate modeling.'};path.write_text(json.dumps(d,separators=(',',':')));print('MONACO IGN RANGE',np.ptp(tz),'fallback',missing.sum(),flush=True)
