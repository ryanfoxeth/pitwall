"""Fetch OpenStreetMap and bacinger outlines. Raw responses remain in ignored cache.
Usage: python fetch_season_sources.py CACHE_DIR
"""
import json,urllib.request,urllib.parse,time,math
from pathlib import Path
import sys
P=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent/'asset-cache'/'season';P.mkdir(parents=True,exist_ok=True)
ids={'baku':'az-2016','sepang':'my-1999','marina_bay':'sg-2008','americas':'us-2012','rodriguez':'mx-1962','interlagos':'br-1940','vegas':'us-2023','losail':'qa-2004','yas_marina':'ae-2009'}
for name,file in ids.items():
 g=P/(name+'-outline.json')
 if not g.exists():g.write_bytes(urllib.request.urlopen('https://raw.githubusercontent.com/bacinger/f1-circuits/master/circuits/'+file+'.geojson').read())
 points=json.loads(g.read_text())['features'][0]['geometry']['coordinates'];xs,ys=zip(*[p[:2] for p in points]);pad=.005 if name!='marina_bay' else .009
 bbox=f'{min(ys)-pad},{min(xs)-pad},{max(ys)+pad},{max(xs)+pad}'
 query=f'''[out:json][timeout:120];(way[building]({bbox});way["building:part"]({bbox});way["leisure"~"grandstand|stadium|park|marina"]({bbox});way["natural"~"water|coastline"]({bbox});relation["natural"="water"]({bbox});way["waterway"]({bbox});way["barrier"="city_wall"]({bbox});way["historic"]({bbox});way["highway"~"primary|secondary|tertiary|pedestrian"]({bbox});node["tourism"~"attraction|viewpoint"]({bbox}););out body geom;'''
 out=P/(name+'-osm.json')
 if out.exists():continue
 for endpoint in ['https://overpass-api.de/api/interpreter','https://overpass.kumi.systems/api/interpreter','https://overpass-api.de/api/interpreter']:
  try:
   req=urllib.request.Request(endpoint,data=urllib.parse.urlencode({'data':query}).encode(),headers={'User-Agent':'Pitwall circuit geography research'})
   data=urllib.request.urlopen(req,timeout=150).read();r=json.loads(data);assert r.get('elements');out.write_bytes(data);print(name,len(r['elements']),len(data),flush=True);break
  except Exception as e:print(name,str(e),flush=True);time.sleep(2)

import xml.etree.ElementTree as ET
p=P
for name in ids:
 if (p/(name+'-osm.json')).exists():continue
 g=json.load(open(p/(name+'-outline.json')))['features'][0]['geometry']['coordinates'];xs,ys=zip(*[r[:2] for r in g]);bbox=f'{min(xs)-.002},{min(ys)-.002},{max(xs)+.002},{max(ys)+.002}'
 try:
  req=urllib.request.Request('https://api.openstreetmap.org/api/0.6/map?bbox='+bbox,headers={'User-Agent':'Pitwall/1.0 circuit-scenery'})
  data=urllib.request.urlopen(req,timeout=75).read();r=ET.fromstring(data);nodes={int(n.attrib['id']):{'lat':float(n.attrib['lat']),'lon':float(n.attrib['lon'])} for n in r.findall('node')};elements=[]
  for f in r:
   if f.tag not in ['way','node']:continue
   tags={t.attrib['k']:t.attrib['v'] for t in f.findall('tag')}
   if not tags:continue
   item={'type':f.tag,'id':int(f.attrib['id']),'tags':tags}
   if f.tag=='way':item['geometry']=[nodes[int(n.attrib['ref'])] for n in f.findall('nd') if int(n.attrib['ref']) in nodes]
   else:item.update(nodes[int(f.attrib['id'])])
   elements.append(item)
  (p/(name+'-osm.json')).write_text(json.dumps({'elements':elements}));print(name,len(elements),flush=True)
 except Exception as e:print(name,e,flush=True)
