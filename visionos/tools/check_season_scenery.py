"""Validate all nine mapped neighborhoods before a native build."""
import json,math
from pathlib import Path
from shapely.geometry import Polygon,LineString
from shapely.ops import unary_union
root=Path(__file__).resolve().parents[1];ids=['baku','sepang','marina_bay','americas','rodriguez','interlagos','vegas','losail','yas_marina']
for id in ids:
 d=json.loads((root/'Assets/Season'/f'{id}.json').read_text());boundary=Polygon(d['boundary']);road=LineString([p[:2] for p in d['track']]).buffer(10)
 assert boundary.is_valid and boundary.contains(road),id+' boundary'
 assert len(d['buildings'])>=20,id+' missing structures'
 for b in d['buildings']:
  p=Polygon(b['footprint']);assert p.is_valid and not p.intersects(road),f'{id} building blocks track: {b["osm"]}'
 for t in d['terrain']+d['waterTriangles']:
  assert all(math.isfinite(v) for p in t for v in p)
  assert Polygon([p[:2] for p in t]).area>0,id+' bad triangle'
 span=max(max(p[i] for p in d['track'])-min(p[i] for p in d['track']) for i in [0,1]);bounds=boundary.bounds;ratio=max(bounds[2]-bounds[0],bounds[3]-bounds[1])/span
 assert ratio<1.65,(id,'oversized surrounding area',ratio)
 assert d['attribution']=='© OpenStreetMap contributors'
 if id=='americas':assert any(x['kind']=='cota_tower' for x in d['special'])
 if id=='rodriguez':assert {377679562,1315400018}.issubset({b['osm'] for b in d['buildings']})
 if id=='vegas':assert {x['kind'] for x in d['special']}=={'eiffel','sphere'}
 if id=='marina_bay':
  # Two-node relation members are needed to close the bay shoreline.
  assert sum(Polygon([p[:2] for p in t]).area for t in d['waterTriangles'])>400000,'Singapore bay missing'
 if id=='yas_marina':
  assert any(x['kind']=='yas_hotel' for x in d['special'])
  water=unary_union([Polygon([p[:2] for p in t]) for t in d['waterTriangles']]);hulls=[]
  assert len(d['boats'])>100
  for boat in d['boats']:
   x,y=boat['center'];angle=boat['angle'];a,b=math.cos(angle),math.sin(angle)
   hull=Polygon([(x+a*u-b*v,y+b*u+a*v) for u,v in [(-13,-2.5),(13,-2.5),(13,2.5),(-13,2.5)]])
   assert water.buffer(.01).contains(hull),'Yacht intersects shore'
   assert not any(hull.intersects(other) for other in hulls),'Overlapping yachts'
   hulls.append(hull)
 print(id,len(d['buildings']),'buildings; tabletop footprint ratio',round(ratio,2))
print('Season geography passed')
