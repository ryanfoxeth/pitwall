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
pier_shapes=[Polygon(p['points']).buffer(0) if p['points'][0]==p['points'][-1] else LineString(p['points']).buffer(1.5) for p in data['piers']]
piers=unary_union(pier_shapes)
available=water.buffer(-.2).difference(piers.buffer(.2))
boats=[];occupied=[]
# Stern-to berths along real quay and pier faces. Bow points into the water.
# No boats are seeded in open water; each retains its dock anchor for validation.
segments=[]
shore=list(orient(water,sign=1).exterior.coords)
for a,b in zip(shore,shore[1:]):
 length=math.dist(a,b)
 if 14<length<220:segments.append((a,b,1,90,'quay'))
for shape in pier_shapes:
 if shape.geom_type!='Polygon':continue
 points=list(orient(shape,sign=1).exterior.coords)
 for a,b in zip(points,points[1:]):
  if math.dist(a,b)>14:segments.append((a,b,-1,60,'pier'))
segments.sort(key=lambda s:math.dist(s[0],s[1]),reverse=True)
for a,b,side,maximum,kind in segments:
 dx,dy=b[0]-a[0],b[1]-a[1];span=math.hypot(dx,dy);nx,ny=-dy/span*side,dx/span*side
 angle=math.atan2(ny,nx)
 # Choose one vessel length for the row, sized for the surrounding basin.
 for length in [maximum,60,44,32,24]:
  if length>maximum:continue
  width=length*.22;count=int((span-6)/(width+2.8))
  if count<1:continue
  candidates=[]
  for j in range(count):
   distance=span/2+(j-(count-1)/2)*(width+2.8)
   dock=[a[0]+dx*distance/span,a[1]+dy*distance/span]
   gap=2.8;x=dock[0]+nx*(length*.5+gap);y=dock[1]+ny*(length*.5+gap)
   hull=translate(rotate(box(-length*.5,-width*.5,length*.54,width*.5),angle,use_radians=True),x,y)
   clearance=hull.buffer(1.1,join_style=2)
   if not available.covers(clearance) or any(clearance.intersects(other) for other in occupied):continue
   candidates.append((clearance,{'x':x,'y':y,'angle':angle,'length':length,'width':width,'style':(len(boats)+len(candidates))%5,'dock':dock,'dockKind':kind,'sternGap':gap}))
  if not candidates:continue
  for hull,boat in candidates:occupied.append(hull);boats.append(boat)
  break
print('Docked fleet:',len(boats),'including',sum(b['length']>=72 for b in boats),'megayachts')
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
data['notes']=data['notes'].replace('Fairmont/tunnel roof is cut away for race visibility.','Fairmont massing is cut away; the circuit tunnel has a continuous roof.')
notes=' Dense party-yacht positions and casino retaining terraces are original fictional set dressing, not surveyed architecture or real vessel data.'
if notes not in data['notes']:data['notes']+=notes
path.write_text(json.dumps(data,separators=(',',':')))
