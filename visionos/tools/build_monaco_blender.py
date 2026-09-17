"""Blender background generator: -- DATA.json OUTPUT.usdz PREVIEW.png.
Original Grand Prix landmark detailing over attributed OSM footprints.
Uses Blender Z up; exported Y up matches Pitwall's x,height,-north convention.
"""
import bpy, json, sys, math, random
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:];data=json.load(open(args[0]));output=args[1];preview=args[2]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
random.seed(17)
track=data['track'];cx=(min(p[0] for p in track)+max(p[0] for p in track))/2;cy=(min(p[1] for p in track)+max(p[1] for p in track))/2
scale=.55/max(max(p[0] for p in track)-min(p[0] for p in track),max(p[1] for p in track)-min(p[1] for p in track))
# Build at geographic metres, then transform every object into tabletop units.
mats={}
def mat(name,color,rough=.65,metal=0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;mats[name]=m;return m
mat('Limestone',(0.76,.69,.56));mat('Ivory',(.91,.86,.73));mat('Terracotta',(.43,.20,.12));mat('Slate',(.12,.18,.20),.45)
mat('Glass',(.055,.14,.19),.22,.2);mat('Water',(.015,.24,.32),.24,.25);mat('Land',(.49,.48,.39));mat('Quay',(.70,.69,.60));mat('White',(.96,.96,.91));mat('Hull',(.13,.19,.24),.4);mat('Gold',(.73,.52,.20),.32,.3);mat('Foliage',(.16,.30,.16));mat('Red',(.68,.045,.035));mat('Asphalt',(.10,.115,.12));mat('Base',(.055,.075,.085));mat('Pool',(.05,.53,.65),.2)
mat('Teak',(.56,.34,.16));mat('Cushion',(.90,.36,.12));mat('PartyBlue',(.025,.42,.68));mat('Skin',(.72,.43,.28))
def mesh(name,verts,faces,m):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o.data.materials.append(mats[m]);return o
def box(name,p,size,m,angle=0):
 x,y,z=[v/2 for v in size];v=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
 o=mesh(name,v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],m);o.location=p;o.rotation_euler.z=angle;return o
def cylinder(name,p,r,depth,m,vertices=12):
 bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=depth,location=p);o=bpy.context.object;o.name=name;o.data.materials.append(mats[m]);return o
def dome(name,p,r,m):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=r,location=p);o=bpy.context.object;o.name=name;o.scale.z=.85;o.data.materials.append(mats[m]);return o
def ribbon(name,a,b,width,height,m):
 mid=((a[0]+b[0])/2,(a[1]+b[1])/2,(a[2]+b[2])/2);dx=b[0]-a[0];dy=b[1]-a[1]
 o=box(name,mid,((Vector(b)-Vector(a)).length,width,height),m)
 o.rotation_euler=(Vector(b)-Vector(a)).to_track_quat('X','Z').to_euler();return o
def poly(name,points,z,h,m):
 p=points[:-1] if points[0]==points[-1] else points;n=len(p)
 if sum(p[i][0]*p[(i+1)%n][1]-p[(i+1)%n][0]*p[i][1] for i in range(n))<0:p=list(reversed(p))
 v=[(x,y,z) for x,y in p]+[(x,y,z+h) for x,y in p]
 f=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return mesh(name,v,f,m)
def ground(x,y):
 best=1e30;z=0
 for a,b in zip(track,track[1:]):
  dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/max(1e-8,dx*dx+dy*dy)))
  d=(a[0]+t*dx-x)**2+(a[1]+t*dy-y)**2
  if d<best:best=d;z=a[2]+t*(b[2]-a[2])
 return z
# Detailed land surface and geographic harbor basin.
verts=[];faces=[]
for tri in data['terrain']:
 start=len(verts);verts.extend(tri);faces.append((start,start+1,start+2))
mesh('Monaco sculpted land',verts,faces,'Land')
for a,b in zip(track,track[1:]):
 ribbon('Street foundation',(a[0],a[1],a[2]-1.3),(b[0],b[1],b[2]-1.3),19,1.5,'Quay')
poly('Compact diorama plinth',data['boundary'],-20,2,'Base')
for a,b in zip(data['boundary'],data['boundary'][1:]):
 za=max(-.3,ground(*a)-1.3);zb=max(-.3,ground(*b)-1.3)
 mesh('Diorama edge',[(*a,-18),(*b,-18),(*b,zb),(*a,za)],[(0,1,2,3)],'Land')
verts=[];faces=[]
for tri in data['waterTriangles']:
 start=len(verts);verts.extend([(x,y,-.8) for x,y in tri]);faces.append((start,start+1,start+2))
mesh('Port Hercule water',verts,faces,'Water')
# Quay walls follow the mapped port perimeter.
water=data['water']
for a,b in zip(water,water[1:]):
 if math.dist(a,b)>220:continue # the open harbor mouth has no invented seawall
 ribbon('Stone harbor quay',(*a,1),(*b,1),3,4,'Quay')
# Raised city blocks, roof lips, and sparse facade windows.
for k,b in enumerate(data['buildings']):
 p=b['footprint'];z=b['base']-1.1;h=b['height'];poly('City foundation',p,-3,z+3,'Limestone');poly('City '+str(b['osm']),p,z,h,'Ivory' if k%3 else 'Limestone');poly('Roof '+str(b['osm']),p,z+h,.8,'Terracotta' if k%4==0 else 'Slate')
 for a,c in zip(p,p[1:]):
  length=math.dist(a,c)
  if length<9:continue
  dx=(c[0]-a[0])/length;dy=(c[1]-a[1])/length
  for j in range(1,min(7,int(length/6))):
   t=j/min(7,int(length/6));x=a[0]+t*(c[0]-a[0]);y=a[1]+t*(c[1]-a[1])
   for level in range(1,min(7,int(h/4))):box('Facade window',(x,y,z+level*4),(2,.35,1.8),'Glass',math.atan2(dy,dx))
# Landmark footprint massing, with original silhouette details.
for l in data['landmarks']:
 kind=l['kind'];p=l['footprint'];x,y=l['center'];z=l['base']-1
 for tier in l.get('supportTiers',[]):
  for triangle in tier['triangles']:
   poly('Terraced retaining foundation',triangle,tier['bottom'],tier['top']-tier['bottom']+.08,'Limestone')
   poly('Retaining wall coping',triangle,tier['top'],.35,'Quay')
 if kind=='fairmont':
  # Open roof and low terraces keep the tunnel and hairpin readable.
  for part in l['renderTriangles']:
   poly('Fairmont cutaway terraces',part,z,5,'Ivory');poly('Fairmont rooftop terrace',part,z+5,.7,'Quay')
  box('Fairmont pool',(x,y,z+6),(24,10,.8),'Pool')
 elif kind=='yacht_club':
  for i in range(3):
   pp=[(x+(a-x)*(1-i*.10),y+(b-y)*(1-i*.10)) for a,b in p]
   poly('Yacht Club deck '+str(i),pp,2+i*5,3.1,'White');poly('Yacht Club glazing '+str(i),pp,5.1+i*5,1.2,'Glass')
 elif kind=='hotel_paris':
  poly('Hotel de Paris',p,z,23,'Ivory');poly('Hotel de Paris mansard roof',p,z+23,4,'Slate')
  for a,b in zip(p,p[1:]):
   if math.dist(a,b)>12:ribbon('Hotel cornice',(*a,z+21),(*b,z+21),1.3,1,'White')
 else:
  poly('Casino and Opera',p,z,18,'Limestone');poly('Casino roof',p,z+18,3,'Slate')
  # Twin casino towers on the northwest entrance facade; roof pavilions behind.
  front=(x-17,y+28);angle=-.55
  def cp(a,b,h):return (front[0]+a*math.cos(angle)-b*math.sin(angle),front[1]+a*math.sin(angle)+b*math.cos(angle),z+h)
  box('Casino front facade',cp(0,0,12),(55,13,24),'Ivory',angle)
  for a in [-21,21]:
   box('Casino tower',cp(a,0,24),(11,12,19),'Ivory',angle)
   cylinder('Casino tower drum',cp(a,0,35),6,4,'Gold');dome('Casino copper dome',cp(a,0,39),6,'Slate');cylinder('Casino finial',cp(a,0,45),.65,5,'Gold')
  for a in range(-15,16,5):
   box('Casino arch glazing',cp(a,-7,12),(2.6,.6,7),'Glass',angle)
   box('Casino pilaster',cp(a+2,-7,12),(.8,1,15),'White',angle)
  cylinder('Casino clock surround',cp(0,-7.5,25),3,.6,'Gold').rotation_euler.x=math.pi/2
  dome('Opera roof dome',(x+14,y-22,z+24),12,'Slate')
# Open-sided tunnel: columns and narrow roof beams, not a solid occluding slab.
tunnel=data['tunnel']
for i,(a,b) in enumerate(zip(tunnel,tunnel[1:])):
 za=ground(*a);zb=ground(*b)
 ribbon('Tunnel roof edge',(*a,za+8),(*b,zb+8),2.5,1,'Quay')
 if i%2==0:
  dx=b[0]-a[0];dy=b[1]-a[1];length=max(.1,math.hypot(dx,dy));nx=-dy/length;ny=dx/length
  for side in [-1,1]:box('Tunnel pier',(a[0]+nx*side*7,a[1]+ny*side*7,za+3.4),(1.2,1.2,7),'Ivory')
  ribbon('Tunnel arch', (a[0]-nx*7,a[1]-ny*7,za+7),(a[0]+nx*7,a[1]+ny*7,za+7),1.1,1.2,'Ivory')
# Real mapped piers and original yachts.
def inside(p,poly):
 x,y=p;c=False
 for a,b in zip(poly,poly[1:]):
  if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:c=not c
 return c
boats=data['partyYachts']
def yacht(x,y,angle,length,w,style):
 h=length*.042
 def at(a,b,z):return (x+a*math.cos(angle)-b*math.sin(angle),y+a*math.sin(angle)+b*math.cos(angle),z)
 def deckbox(name,a,b,z,size,m):return box(name,at(a,b,z),size,m,angle)
 outline=[(-length*.50,-w*.46),(-length*.50,w*.46),(length*.22,w*.5),(length*.54,0),(length*.22,-w*.5)]
 pp=[at(a,b,0)[:2] for a,b in outline]
 poly('Megayacht hull',pp,-.3,h,'White' if style%3 else 'Hull')
 poly('Teak promenade deck',pp,h-.1,.5,'Teak')
 # Stepped decks and continuous dark glazing remain readable at tabletop scale.
 for level in range(3 if length>60 else 2):
  z=h+1+level*2.7
  deckbox('White deck overhang',-.02*length,0,z,(length*(.69-level*.12),w*(.93-level*.12),.65),'White')
  deckbox('Panoramic glass',.025*length,0,z+1.35,(length*(.52-level*.10),w*(.75-level*.12),2),'Glass')
  deckbox('White superstructure roof',.025*length,0,z+2.5,(length*(.55-level*.10),w*(.79-level*.12),.5),'White')
 top=h+1+(2 if length>60 else 1)*2.7+2.9
 deckbox('Open party sun deck',-.09*length,0,top,(length*.38,w*.58,.45),'Teak')
 deckbox('Radar mast',.12*length,0,top+2,(.8,.8,4),'White')
 for side in [-1,1]:
  deckbox('Satellite radar',.10*length,side*w*.20,top+1,(1.5,1.5,1.8),'White')
 # Stern pool, bathing platform, sun beds and colored party furniture.
 deckbox('Stern beach club',-.46*length,0,h+.5,(length*.12,w*.86,.6),'White')
 deckbox('Turquoise pool',-.35*length,0,h+.65,(length*.12,w*.50,.25),'Pool')
 for side in [-1,1]:
  for j in range(3):deckbox('Sun lounger',(-.25+j*.075)*length,side*w*.32,h+1,(length*.05,w*.12,.7),'Cushion' if style%2 else 'White')
 # Canopy, cocktail bar and guests: stylized decorative details, not telemetry.
 deckbox('Cocktail bar',-.015*length,0,top+1.1,(length*.09,w*.32,1.3),'White')
 for side in [-1,1]:
  deckbox('Canopy support',-.20*length,side*w*.22,top+1.9,(.45,.45,3.8),'White')
 deckbox('Party shade canopy',-.20*length,0,top+3.8,(length*.17,w*.54,.4),'White')
 for j in range(6 if length<60 else 12):
  a=(-.27+random.random()*.36)*length;b=(random.random()-.5)*w*.45
  deckbox('Party guest',a,b,top+1.0,(.8,.8,1.5),'PartyBlue' if j%3 else 'Red')
  deckbox('Guest head',a,b,top+1.95,(.65,.65,.65),'Skin')
 if length>=80:
  # Bow helipad and oversized H marking.
  deckbox('Helipad',.33*length,0,h+.6,(length*.15,w*.58,.25),'Slate')
  for side in [-1,1]:deckbox('Helipad H',.33*length,side*w*.12,h+.8,(length*.095,.7,.12),'White')
  deckbox('Helipad H crossbar',.33*length,0,h+.8,(.7,w*.28,.12),'White')
for pier in data['piers']:
 for a,b in zip(pier['points'],pier['points'][1:]):ribbon('Marina jetty',(*a,.5),(*b,.5),2.5,1,'Quay')
for boat in boats:yacht(boat['x'],boat['y'],boat['angle'],boat['length'],boat['width'],boat['style'])
# Trackside palms at the waterfront and casino square.
for x,y in [(-260,-310),(-260,-260),(-260,-210),(145,255),(155,272),(125,262),(65,26),(105,35)]:
 z=ground(x,y);cylinder('Palm trunk',(x,y,z+5),.7,10,'Terracotta',8)
 for j in range(6):
  a=j*math.pi/3;leaf=box('Palm frond',(x+math.cos(a)*2,y+math.sin(a)*2,z+10),(7,1.3,.6),'Foliage',a);leaf.rotation_euler.y=.22
# Triangulate and batch by material; retain original named objects in source .blend.
for o in list(bpy.context.scene.objects):
 if o.type=='MESH':
  o.location.x=(o.location.x-cx)*scale;o.location.y=(o.location.y-cy)*scale;o.location.z*=scale;o.scale*=scale
# Save editable source before batching.
bpy.ops.wm.save_as_mainfile(filepath=output.replace('.usdz','.blend'))
for material in mats.values():
 objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.data.materials and o.data.materials[0]==material]
 if not objects:continue
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();o=bpy.context.object;o.name='Monaco_'+material.name
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 mod=o.modifiers.new('Triangulate','TRIANGULATE');bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.ops.wm.usd_export(filepath=output,export_materials=True,generate_preview_surface=True,generate_materialx_network=False,export_lights=False,export_cameras=False,convert_orientation=True,export_global_forward_selection='NEGATIVE_Z',export_global_up_selection='Y',convert_scene_units='METERS',meters_per_unit=1.0)
# Preview includes the road for visual QA; road itself is generated by the app.
for a,b in zip(track,track[1:]):
 aa=((a[0]-cx)*scale,(a[1]-cy)*scale,a[2]*scale);bb=((b[0]-cx)*scale,(b[1]-cy)*scale,b[2]*scale)
 ribbon('Preview road',aa,bb,.006,.0008,'Asphalt')
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.render.resolution_x=1600;scene.render.resolution_y=1600;scene.render.resolution_percentage=100
scene.world.color=(.3,.3,.3)
bpy.ops.object.light_add(type='AREA',location=(-.5,-.4,1.2));bpy.context.object.data.energy=35;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=1
bpy.ops.object.camera_add(location=(.75,-1.05,1.0));cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,0))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.83;scene.camera=cam
scene.render.image_settings.file_format='PNG';scene.render.filepath=preview;scene.view_settings.view_transform='AgX';bpy.ops.render.render(write_still=True)
print('MONACO_COMPLETE',len(boats),'yachts',len(scene.objects),'batched objects')
