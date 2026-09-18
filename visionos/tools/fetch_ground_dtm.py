"""Read small geographic windows from GEDTM30 v1.2 COG; never download the globe.
Input directory: geographic projections from fetch_land_terrain.py.
Output: attributed bare-earth model grids, separately from telemetry and raw DSM.
Requires rasterio and numpy. GEDTM30 CC-BY-4.0; modeled terrain, not surveyed road.
"""
import json,sys,hashlib
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from terrain_grid import TerrainGrid
source,out=map(Path,sys.argv[1:3]);out.mkdir(parents=True,exist_ok=True)
url='https://s3.opengeohub.org/global/dtm/v1.2/gedtm_rf_m_30m_s_20060101_20151231_go_epsg.4326.3855_v1.2.tif'
cat=json.loads((Path(__file__).resolve().parents[1]/'Sources/Resources/Season2026.json').read_text())
with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',GDAL_HTTP_TIMEOUT='60',GDAL_HTTP_MAX_RETRY='3'):
 with rasterio.open(url) as src:
  for c in sorted(cat,key=lambda c:(c['round']<15,c['round'])):
   cid=c['id'];dest=out/(cid+'.json')
   if dest.exists():continue
   d=json.loads((source/(cid+'.json')).read_text());g=d['grid'];pr=d['projection'];origin=np.array(pr['origin']);factors=np.array(pr['factors']);shape=np.array(g['heights']).shape
   # Preserve higher-resolution bare-earth national data for US/Austria/UK.
   native=all(t['imagery'].startswith(('ned','austria','uk_lidar')) for t in d['source']['tiles'])
   if native:d['source']['groundModel']='National terrain DEM';dest.write_text(json.dumps(d,separators=(',',':')));print(cid,'national DEM',d['trackTerrainRangeMeters'],flush=True);continue
   xx,yy=np.meshgrid(g['x0']+np.arange(shape[1])*g['step'],g['y0']+np.arange(shape[0])*g['step']);ll=np.stack([xx,yy],-1)/factors+origin;lo=ll.reshape(-1,2).min(0)-.001;hi=ll.reshape(-1,2).max(0)+.001
   w=from_bounds(*lo,*hi,src.transform).round_offsets().round_lengths();z=src.read(1,window=w);tf=src.window_transform(w);np.savez_compressed(out/(cid+'-source.npz'),heights=z,transform=np.array(tuple(tf)))
   inv=~tf;q=np.stack([(ll[...,0]*inv.a+inv.c)-.5,(ll[...,1]*inv.e+inv.f)-.5],-1);ij=np.floor(q).astype(int);u,v=np.moveaxis(q-ij,-1,0);x,y=np.moveaxis(ij,-1,0)
   heights=z[y,x]*(1-u)*(1-v)+z[y,x+1]*u*(1-v)+z[y+1,x]*(1-u)*v+z[y+1,x+1]*u*v
   if not np.isfinite(heights).all() or np.abs(heights).max()>9000:raise ValueError('Missing terrain in '+cid)
   d['grid']['heights']=heights.round(3).tolist();d['trackDatumMeters']=0;sampler=TerrainGrid(d);tz=np.array([sampler.height(*p[:2]) for p in c['points']]);d['trackTerrainHeights']=tz.round(3).tolist();d['trackDatumMeters']=float(tz.min());d['trackTerrainRangeMeters']=float(np.ptp(tz));d['source']={'provider':'OpenGeoHub GEDTM30 v1.2','url':url,'citation':'Ho and Hengl (2026), Global Ensemble Digital Terrain Model 30m, https://doi.org/10.5281/zenodo.18887460','license':'CC-BY-4.0','retrieved':'2026-09-18','nativeResolutionArcSeconds':1,'groundModel':'Machine-learning fused geographic terrain','survey_grade':False,'road_surface':False,'method':'Bilinear sampling of geographic DTM; no driver telemetry; original cropped samples retained','limitations':'30m modeled terrain, not surveyed road; small embankments, tunnels, bridges and recent grading require separate treatment. Resampling adds no accuracy.'};dest.write_text(json.dumps(d,separators=(',',':')));print(cid,'DTM range',round(np.ptp(tz),2),'raw DSM',round(json.loads((source/(cid+'.json')).read_text())['trackTerrainRangeMeters'],2),flush=True)
