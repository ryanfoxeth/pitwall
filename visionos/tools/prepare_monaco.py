"""Prepare a compact, attributed OSM scene. Requires numpy and shapely.
Usage: python prepare_monaco.py OSM.json RELATIONS.json CATALOG.json OUTPUT.json
OSM inputs: Overpass body/geometry extracts; never Google-derived geometry.
"""
import json, math, sys
import numpy as np
from shapely import constrained_delaunay_triangles
from shapely.geometry.polygon import orient
from shapely.geometry import Polygon, LineString, Point, mapping
from shapely.ops import unary_union, polygonize, linemerge, triangulate
osm,relations,catalog,out=sys.argv[1:]
features=json.load(open(osm))['elements'];rels=json.load(open(relations))['elements']
c=next(x for x in json.load(open(catalog)) if x['id']=='monaco');track=np.array(c['points'])
# The existing circuit uses the mean of its source geographic outline.
lon,lat=7.42530133125,43.7371575
sx=111320*math.cos(math.radians(lat))
def xy(v):return [(v['lon']-lon)*sx,(v['lat']-lat)*111320]
def relpoly(r):
 lines=[LineString([xy(v) for v in m['geometry']]) for m in r['members'] if m.get('role')=='outer' and m.get('geometry')]
 return max(polygonize(unary_union(lines)),key=lambda p:p.area)
port=relpoly(next(r for r in rels if r['id']==2221179))
line=LineString(track[:,:2]);road=line.buffer(9)
# Include the real port, but crop the city to a narrow circuit neighborhood.
boundary=unary_union([Polygon(track[:,:2]).buffer(55),line.buffer(55),port]).convex_hull.buffer(12,join_style=2)
land=boundary.difference(port).difference(road)
def height(x,y):
 a=track[:-1];v=track[1:,:2]-a[:,:2];w=np.array([x,y])-a[:,:2]
 t=np.clip((w*v).sum(1)/(v*v).sum(1),0,1);q=a[:,:2]+v*t[:,None];i=np.argmin(((q-[x,y])**2).sum(1))
 return float(a[i,2]+t[i]*(track[i+1,2]-a[i,2]))
def coords(p):return [[round(x,3),round(y,3)] for x,y in orient(p,sign=1).exterior.coords]
def tris(p):return [coords(t)[:3] for t in constrained_delaunay_triangles(p).geoms]
landmarks=[]
for kind,id in [('casino',161769674),('hotel_paris',8280869),('fairmont',2093796),('yacht_club',8269572)]:
 if kind=='casino':
  f=next(f for f in features if f['id']==id);p=Polygon([xy(v) for v in f['geometry']])
 else:p=relpoly(next(r for r in rels if r['id']==id))
 # A cutaway hotel over the tunnel is represented by a low upper mass later.
 landmarks.append({'kind':kind,'osm':id,'footprint':coords(p),'center':list(p.centroid.coords)[0],'base':height(p.centroid.x,p.centroid.y),'triangles':tris(p),'renderTriangles':tris(p.difference(road.buffer(2))) if kind=='fairmont' else tris(p)})
exclude=unary_union([Polygon(x['footprint']).buffer(6) for x in landmarks])
buildings=[]
for f in features:
 t=f.get('tags',{})
 if 'building' not in t:continue
 p=Polygon([xy(v) for v in f['geometry']])
 if not p.is_valid:p=p.buffer(0)
 if p.geom_type!='Polygon' or p.area<60 or not boundary.contains(p) or p.intersects(exclude) or p.intersects(road) or p.intersects(port):continue
 center=p.centroid
 if line.distance(center)>90:continue
 raw=t.get('height');levels=t.get('building:levels');h=16;quality='estimated'
 try:
  if raw:h=float(raw.split(';')[0].replace(' m',''));quality='OSM height'
  elif levels:h=float(levels)*3.1;quality='OSM floors times 3.1m'
 except ValueError:pass
 h=min(48,max(6,h));base=height(center.x,center.y)
 buildings.append({'osm':f['id'],'name':t.get('name',''),'footprint':coords(p.simplify(.6)),'height':round(h,2),'base':round(base,2),'heightSource':quality})
piers=[]
for f in features:
 if f.get('tags',{}).get('man_made')!='pier':continue
 p=LineString([xy(v) for v in f['geometry']]);p=p.intersection(port.buffer(3))
 if not p.is_empty and p.geom_type=='LineString':piers.append({'osm':f['id'],'points':list(p.coords)})
# Triangulate a clipped grid so terrain follows nearby road elevation.
terrain=[];xmin,ymin,xmax,ymax=boundary.bounds
for x in np.arange(xmin,xmax,18):
 for y in np.arange(ymin,ymax,18):
  cell=Polygon([(x,y),(x+18,y),(x+18,y+18),(x,y+18)]).intersection(land)
  parts=[cell] if cell.geom_type=='Polygon' else list(getattr(cell,'geoms',[]))
  for part in parts:
   if part.geom_type!='Polygon':continue
   for tri in tris(part):
    terrain.append([[a,b,round(max(-.3,height(a,b)-1.3),3)] for a,b in tri])
tunnel=next(f for f in features if f['id']==4230891)
tunnelPoints=[xy(v) for v in tunnel['geometry']]
data={'tunnel':tunnelPoints,'license':'ODbL-1.0','attribution':'© OpenStreetMap contributors','source':'https://www.openstreetmap.org/copyright','retrieved':'2026-09-17','projection':{'origin':[lon,lat],'metersPerLongitudeDegree':sx,'metersPerLatitudeDegree':111320},'track':track.tolist(),'boundary':coords(boundary),'water':coords(port),'waterTriangles':tris(port),'terrain':terrain,'buildings':buildings,'piers':piers,'landmarks':landmarks,'notes':'Building heights and terrain are approximate. Casino architectural detailing, yachts and furnishings are original stylized models. Track elevation is recorded, not surveyed. Fairmont/tunnel roof is cut away for race visibility.'}
json.dump(data,open(out,'w'),separators=(',',':'));print('Buildings',len(buildings),'piers',len(piers),'terrain triangles',len(terrain),'bounds',boundary.bounds)
