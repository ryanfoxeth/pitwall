"""Prepare attributed circuit neighborhoods from cached Overpass/GeoJSON extracts.
python prepare_season_scenery.py CACHE_DIR CATALOG OUTPUT_DIR
Geometry is mapped; inferred heights and interpolated terrain are explicitly approximate.
"""
import json,math,sys,re
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon,LineString,Point,box
from shapely.ops import unary_union,polygonize,split
from shapely.geometry.polygon import orient
from shapely import constrained_delaunay_triangles
cache,catalog,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
projections=json.loads((Path(__file__).resolve().parents[1]/'Assets/TerrainProjections.json').read_text())
patterns={'baku':r'Maiden Tower|House of Government|Double Gates|Shirvanshah|Tower [123]$', 'sepang':r'Main Grandstand|Paddock/Pit', 'marina_bay':r'Marina Bay Sands Tower|Esplanade (Concert Hall|Theatre)$|^Singapore Flyer$|F1 Pit Building', 'americas':r'Observation|Tower|Amphitheater', 'rodriguez':r'Foro Sol|GNP|Palacio de los Deportes', 'interlagos':r'Autódromo|Paddock', 'vegas':r'^Sphere$|Bellagio Las Vegas|^Paris Las Vegas$|Venetian Tower|Eiffel Tower', 'losail':r'Grandstand|Paddock|Pit', 'yas_marina':r'W Hotel Abu Dhabi|W Abu Dhabi|Main Grandstand|North Grandstand|South Grandstand'}
def parts(g):return [g] if g.geom_type=='Polygon' else [p for p in getattr(g,'geoms',[]) if p.geom_type=='Polygon']
def coords(p):return [[round(x,3),round(y,3)] for x,y in orient(p,sign=1).exterior.coords]
def triangles(p):return [coords(t)[:3] for t in constrained_delaunay_triangles(p).geoms if t.area>.01]
for c in json.load(open(catalog)):
 id=c['id'];file=cache/(id+'-osm.json')
 if not file.exists():continue
 geo=json.load(open(cache/(id+'-outline.json')))['features'][0]['geometry']['coordinates'];geo=np.array(geo)[:,:2];origin=np.array(projections[id]['origin']);factor=np.array(projections[id]['factors']);track=np.array(c['points']);line=LineString(track[:,:2]);road=line.buffer(10)
 def xy(p):return list((np.array([p['lon'],p['lat']])-origin)*factor)
 def height(x,y):
  a=track;v=np.roll(track,-1,axis=0)[:,:2]-a[:,:2];t=np.clip(((np.array([x,y])-a[:,:2])*v).sum(1)/np.maximum(1e-8,(v*v).sum(1)),0,1);d=((a[:,:2]+v*t[:,None]-[x,y])**2).sum(1);i=int(np.argmin(d));return float(a[i,2]+t[i]*(track[(i+1)%len(track),2]-a[i,2]))
 elements=json.load(open(file))['elements'];geometries=[];landmarks=[]
 for f in elements:
  tag=f.get('tags',{});name=tag.get('name:en',tag.get('name',''));g=None
  try:
   if f['type']=='way' and len(f.get('geometry',[]))>2:
    p=[xy(v) for v in f['geometry']];g=Polygon(p).buffer(0) if p[0]==p[-1] else LineString(p)
   elif f['type']=='relation':
    lines=[LineString([xy(v) for v in m['geometry']]) for m in f.get('members',[]) if m.get('role')=='outer' and len(m.get('geometry',[]))>=2];g=unary_union(list(polygonize(unary_union(lines)))) if lines else None
   if g is None or g.is_empty:continue
   geometries.append((f,tag,name,g))
   if (re.search(patterns.get(id, r'Grandstand|Paddock|Pit Building'),name,re.I) or (id=='rodriguez' and f['id'] in [377679562,1315400018])) and g.geom_type=='Polygon':
    landmarks.append({'osm':f['id'],'name':name,'footprint':coords(g),'center':list(g.centroid.coords)[0],'base':height(g.centroid.x,g.centroid.y)})
  except (ValueError,KeyError):continue
 boundary=unary_union([Polygon(track[:,:2]).buffer(100),line.buffer(100)]+[Polygon(l['footprint']).buffer(30) for l in landmarks]).convex_hull
 # Include Singapore's bay and Sands skyline; no arbitrary outer world plane.
 waters=[];coasts=[]
 for f,t,n,g in geometries:
  if t.get('natural')=='water':waters.extend(parts(g.intersection(boundary)))
  if t.get('natural')=='coastline' and g.geom_type=='LineString':coasts.append(g)
 if coasts:
  cells=list(polygonize(unary_union([boundary.boundary]+coasts)))
  for cell in cells:
   pt=cell.representative_point();nearest=min(coasts,key=lambda l:l.distance(pt));cs=list(nearest.coords);segments=[(a,b,LineString([a,b]).distance(pt)) for a,b in zip(cs,cs[1:])];a,b,_=min(segments,key=lambda s:s[2]);cross=(b[0]-a[0])*(pt.y-a[1])-(b[1]-a[1])*(pt.x-a[0])
   if cross<0:waters.extend(parts(cell.intersection(boundary)))
 water=unary_union(waters).difference(road);waterTris=[]
 for p in parts(water):waterTris+=triangles(p)
 buildings=[];roads=[];walls=[];parks=[];landmarkIDs={l['osm'] for l in landmarks}
 for f,t,n,g in geometries:
  if not boundary.intersects(g):continue
  if g.geom_type=='Polygon' and ('building' in t or 'building:part' in t or t.get('leisure')=='grandstand'):
   if g.area<60 or not boundary.contains(g) or g.intersects(road) or g.intersects(water):continue
   h=12;source='Estimated';raw=t.get('height','')
   try:
    if raw and float(re.sub(r'[^0-9.]','',raw))>0:h=float(re.sub(r'[^0-9.]','',raw));source='OSM height'
    elif t.get('building:levels'):h=float(t['building:levels'])*3.2;source='OSM floors x 3.2m'
   except ValueError:pass
   h=max(5,min(280,h));p=g.simplify(1)
   buildings.append({'osm':f['id'],'name':n,'footprint':coords(p),'height':h,'base':height(g.centroid.x,g.centroid.y)-1,'heightSource':source,'kind':'stand' if t.get('building')=='grandstand' or t.get('leisure')=='grandstand' else 'building','landmark':f['id'] in landmarkIDs})
  if t.get('barrier')=='city_wall' or t.get('historic')=='citywalls':
   paths=[g.exterior] if g.geom_type=='Polygon' else [g] if g.geom_type=='LineString' else []
   for p in paths:
    q=p.intersection(boundary)
    if q.geom_type=='LineString':walls.append({'osm':f['id'],'points':list(q.coords)})
  if t.get('highway') and g.geom_type=='LineString':
   q=g.intersection(boundary).difference(road.buffer(3));ls=[q] if q.geom_type=='LineString' else [p for p in getattr(q,'geoms',[]) if p.geom_type=='LineString'];roads.extend([list(p.simplify(2).coords) for p in ls if p.length>15])
  if t.get('leisure')=='park' and g.geom_type=='Polygon':
   for p in parts(g.intersection(boundary).difference(road).difference(water)):parks+=triangles(p)
 # Keep surrounding density bounded; retain landmarks and largest structures.
 buildings=sorted(buildings,key=lambda b:(not b['landmark'],-Polygon(b['footprint']).area))[:220]
 land=boundary.difference(water).difference(road);terrain=[];xmin,ymin,xmax,ymax=boundary.bounds;step=max(25,max(xmax-xmin,ymax-ymin)/65)
 for x in np.arange(xmin,xmax,step):
  for y in np.arange(ymin,ymax,step):
   for p in parts(box(x,y,x+step,y+step).intersection(land)):
    for t in triangles(p):terrain.append([[a,b,round(height(a,b)-1.5,3)] for a,b in t])
 data={'id':id,'name':c['circuit'],'license':'ODbL-1.0','attribution':'© OpenStreetMap contributors','retrieved':'2026-09-18','source':'https://www.openstreetmap.org/copyright','projection':{'origin':origin.tolist(),'factors':factor.tolist()},'track':track.tolist(),'boundary':coords(boundary),'terrain':terrain,'waterTriangles':waterTris,'parks':parks,'buildings':buildings,'landmarks':landmarks,'roads':roads,'walls':walls,'elevation':c['elevation'],'notes':'OSM footprints; inferred building heights and nearest-road terrain are approximate, not surveyed. Original landmark silhouette detailing. Reference layout may differ from current event.'}
 special=[]
 for l in landmarks:
  kind={976405284:'sphere',27831699:'eiffel',1228229328:'yas_hotel'}.get(l['osm'])
  if kind:special.append({'kind':kind,'center':l['center'],'osm':l['osm'],'source':'https://www.openstreetmap.org/way/'+str(l['osm']),'angle':-.7 if kind=='yas_hotel' else 0})
 for f in elements:
  t=f.get('tags',{});name=t.get('name:en',t.get('name',''))
  if id=='americas' and ('tower' in name.lower() or f['id']==7911006730):
   if f.get('geometry'):center=np.array([xy(p) for p in f['geometry']]).mean(0).tolist()
   elif 'lat' in f:center=xy(f)
   else:continue
   special.append({'kind':'cota_tower','center':center,'osm':f['id'],'source':'https://www.openstreetmap.org/'+f['type']+'/'+str(f['id'])});break
 for l in special:
  if l['kind']=='yas_hotel':
   footprint=next(x['footprint'] for x in landmarks if x['osm']==l['osm']);l['bodyTriangles']=[t for part in parts(Polygon(footprint).difference(road.buffer(5))) for t in triangles(part)]
 data['boats']=[]
 if id=='yas_marina':
  occupied=[]
  for basin in parts(water):
   ring=list(orient(basin,sign=1).exterior.coords)
   for a,b in zip(ring,ring[1:]):
    length=math.dist(a,b)
    if length<35:continue
    dx,dy=(b[0]-a[0])/length,(b[1]-a[1])/length;nx,ny=-dy,dx
    for step in np.arange(10,length-10,8):
     stern=np.array(a)+np.array([dx,dy])*step+np.array([nx,ny])*2;center=stern+np.array([nx,ny])*13
     corners=[center+np.array([nx,ny])*u+np.array([dx,dy])*v for u,v in [(-13,-2.5),(13,-2.5),(13,2.5),(-13,2.5)]];hull=Polygon(corners)
     if water.contains(hull) and boundary.boundary.distance(Point(stern))>8 and not any(hull.buffer(1).intersects(other) for other in occupied):
      data['boats'].append({'center':center.tolist(),'angle':math.atan2(ny,nx),'length':26,'width':5,'placement':'Decorative stern-to row along mapped basin edge'});occupied.append(hull)
 data['special']=special
 (out/(id+'.json')).write_text(json.dumps(data,separators=(',',':')));print(id,'buildings',len(buildings),'landmarks',[(l['osm'],l['name']) for l in landmarks],'water',len(waterTris),flush=True)
