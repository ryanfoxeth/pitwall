"""Validate geographic movie inputs without conflating modeled ground with survey data."""
import json,sys,math
from pathlib import Path
from terrain_grid import TerrainGrid
# Analytic bilinear plane and vertical datum regression.
g=TerrainGrid({'grid':{'x0':10,'y0':20,'step':2,'heights':[[100,104],[106,110]]},'trackDatumMeters':90})
assert abs(g.height(11,21)-15)<1e-8
assert abs(g.height(10,20)-10)<1e-8
assert abs(g.height(12,22)-20)<.00002
catalog=json.loads((Path(__file__).resolve().parents[1]/'Sources/Resources/Season2026.json').read_text())
root=Path(sys.argv[1]);reports=[]
for c in catalog:
 d=json.loads((root/(c['id']+'.json')).read_text());source=d['groundSource'];assert source['survey_grade'] is False and source['road_surface'] is False
 assert 'OpenF1' not in source['provider'] and 'telemetry' not in source['provider'].lower()
 assert len(d['track'])==len(c['points'])
 assert all(p[:2]==q[:2] or math.dist(p[:2],q[:2])<.0001 for p,q in zip(d['track'],c['points']))
 grid=d['terrainGrid']['grid'];h=grid['heights'];assert len(h)>2 and len(h[0])>2 and all(len(r)==len(h[0]) for r in h)
 assert all(math.isfinite(z) and -500<z<9000 for row in h for z in row)
 grades=[]
 for p,q in zip(d['track'],d['track'][1:]+d['track'][:1]):
  assert all(math.isfinite(v) for v in p)
  assert grid['x0']<=p[0]<=grid['x0']+(len(h[0])-1)*grid['step']
  assert grid['y0']<=p[1]<=grid['y0']+(len(h)-1)*grid['step']
  horizontal=math.dist(p[:2],q[:2]);assert horizontal<25.01
  if horizontal>.1:grades.append(abs(q[2]-p[2])/horizontal)
 assert max(grades)<.25,(c['id'],max(grades))
 reports.append({'id':c['id'],'points':len(d['track']),'maximumModeledGradePercent':round(max(grades)*100,2),'provider':source['provider'],'status':'passed'})
(root/'checks.json').write_text(json.dumps(reports,indent=2));print('PASS: 23 geographic terrain inputs; bilinear units/datum, coverage, finite heights, unchanged horizontal layouts, bounded modeled grades and explicit non-survey provenance')
