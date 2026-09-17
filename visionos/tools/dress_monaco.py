"""Add deterministic, fictional race-weekend dressing to the mapped Monaco data.
Requires Shapely 2.1+. Run after prepare_monaco.py, before Blender export.
"""
import json, math, random, sys
from pathlib import Path
from shapely.geometry import Polygon, LineString, box
from shapely.geometry.polygon import orient
from shapely.affinity import rotate, translate
from shapely.ops import unary_union
from shapely import constrained_delaunay_triangles
path=Path(sys.argv[1]);data=json.loads(path.read_text());rng=random.Random(1709)
water=Polygon(data['water']);road=LineString([p[:2] for p in data['track']]).buffer(11)
piers=unary_union([LineString(p['points']).buffer(3) for p in data['piers']])
available=water.buffer(-5).difference(piers)
boats=[];occupied=[]
xmin,ymin,xmax,ymax=available.bounds
# Fill with the largest vessels first, then dense smaller berths. Positions are
# set dressing, not claims about actual moorings or navigation channels.
for count,low,high in [(45,72,100),(100,43,70),(180,26,42)]:
 added=0
 for attempt in range(16000):
  if added==count:break
  length=rng.uniform(low,high);width=length*rng.uniform(.20,.24)
  x=rng.uniform(xmin,xmax);y=rng.uniform(ymin,ymax)
  angle=1.35 if rng.random()<.85 else -.22
  hull=translate(rotate(box(-length*.5,-width*.5,length*.54,width*.5),angle,use_radians=True),x,y)
  clearance=hull.buffer(2.3,join_style=2)
  if not available.covers(clearance) or any(clearance.intersects(other) for other in occupied):continue
  occupied.append(clearance);boats.append({'x':x,'y':y,'angle':angle,'length':length,'width':width,'style':len(boats)%5});added+=1
print('Party fleet:',len(boats),'including',sum(b['length']>=72 for b in boats),'megayachts; hull coverage',round(sum(b['length']*b['width'] for b in boats)/water.area*100),'percent')
assert all(available.covers(p) for p in occupied)
assert all(not a.intersects(b) for i,a in enumerate(occupied) for b in occupied[i+1:])
data['partyYachts']=boats
# Casino/Opera terraces meet the hillside, without invading the track corridor.
for l in data['landmarks']:
 if l['kind'] not in ['casino','hotel_paris']:continue
 p=Polygon(l['footprint']);top=l['base']-1
 tiers=[]
 for level in range(4):
  bottom=-3+(top+3)*level/4;roof=-3+(top+3)*(level+1)/4
  footprint=p.buffer((3-level)*4,join_style=2).difference(road).difference(water)
  triangles=[list(orient(t,sign=1).exterior.coords)[:3] for t in constrained_delaunay_triangles(footprint).geoms]
  tiers.append({'bottom':bottom,'top':roof,'triangles':triangles})
 l['supportTiers']=tiers
notes=' Dense party-yacht positions and casino retaining terraces are original fictional set dressing, not surveyed architecture or real vessel data.'
if notes not in data['notes']:data['notes']+=notes
path.write_text(json.dumps(data,separators=(',',':')))
