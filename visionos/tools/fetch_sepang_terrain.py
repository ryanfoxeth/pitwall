"""Fill Sepang's missing height profile with explicitly approximate 30m SRTM terrain.
This is terrain height, not surveyed road elevation. Cache preserves source observations.
"""
import json,urllib.request,urllib.parse,time,math
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1];path=root/'Sources/Resources/Season2026.json';catalog=json.loads(path.read_text());c=next(c for c in catalog if c['id']=='sepang');scene=json.loads((root/'Assets/Season/sepang.json').read_text());origin=scene['projection']['origin'];factors=scene['projection']['factors'];cache=root/'Assets/Season/SepangElevation.json'
if cache.exists():rows=json.loads(cache.read_text())['observations']
else:
 rows=[]
 for start in range(0,len(c['points']),80):
  points=c['points'][start:start+80];locations='|'.join(f'{p[1]/factors[1]+origin[1]:.7f},{p[0]/factors[0]+origin[0]:.7f}' for p in points)
  url='https://api.opentopodata.org/v1/srtm30m?'+urllib.parse.urlencode({'locations':locations,'interpolation':'bilinear'})
  r=json.load(urllib.request.urlopen(url,timeout=45));assert r['status']=='OK' and len(r['results'])==len(points);rows+=r['results'];time.sleep(1.1)
 cache.write_text(json.dumps({'provider':'NASA SRTMGL1 v3 via Open Topo Data','source':'https://www.opentopodata.org/datasets/srtm/','retrieved':'2026-09-18','resolution_m':30,'observations':rows},separators=(',',':')))
z=np.array([r['elevation'] for r in rows],dtype=float);assert len(z)==len(c['points']) and np.isfinite(z).all();z=np.median(np.array([np.roll(z,i) for i in range(-2,3)]),axis=0);z=sum(np.roll(z,i) for i in range(-2,3))/5;z-=z.min();assert z.max()<60
for p,h in zip(c['points'],z):p[2]=round(float(h),3)
c['elevation']=f'SRTM terrain estimate · approx. {z.max():.1f} m range · not surveyed road'
c['elevationSource']={'provider':'NASA SRTMGL1 v3 via Open Topo Data','source':'https://www.opentopodata.org/datasets/srtm/','survey_grade':False,'road_surface':False,'resolution_m':30,'range_m':round(float(z.max()),3),'method':'Bilinear terrain samples; circular five-sample median then mean; relative minimum. Buildings and embankments may affect heights.'}
path.write_text(json.dumps(catalog,separators=(',',':')));print('Sepang terrain height range',z.max())
