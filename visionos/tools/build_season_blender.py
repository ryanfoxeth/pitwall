"""Build themed, mapped circuit surroundings. Blender -- DATA OUTPUT PREVIEW THEME.
Road geometry remains owned by the app. Original architectural approximations.
"""
import bpy,sys,json,math,random
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).parent))
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
from scenery_blender import *
a=sys.argv[sys.argv.index('--')+1:];d=json.load(open(a[0]));output=a[1];preview=a[2];theme=a[3];kart=theme=='kart';tron=theme=='tron';track=d['track'];random.seed(26)
cx=(min(p[0] for p in track)+max(p[0] for p in track))/2;cy=(min(p[1] for p in track)+max(p[1] for p in track))/2;scale=.55/max(max(p[i] for p in track)-min(p[i] for p in track) for i in [0,1])
mat('Grass',(.20,.34,.16));mat('Concrete',(.58,.60,.58));mat('Sand',(.65,.56,.39));mat('Seats',(.18,.31,.45));mat('Blue',(.04,.30,.66));mat('Yellow',(.95,.62,.04))
def ground(x,y):
 best=1e30;z=0
 for a,b in zip(track,track[1:]+track[:1]):
  dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/max(1e-8,dx*dx+dy*dy)));dist=(a[0]+t*dx-x)**2+(a[1]+t*dy-y)**2
  if dist<best:best=dist;z=a[2]+t*(b[2]-a[2])
 return z

def surface(name,tris,material,height=None):
 vs=[];fs=[]
 for tri in tris:
  n=len(vs);vs.extend([(p[0],p[1],p[2] if len(p)>2 else (height if height is not None else ground(*p)-1)) for p in tri]);fs.append((n,n+1,n+2))
 if vs:mesh(name,vs,fs,material)
def sphere(name,p,r,m,stretch=(1,1,1)):
 o=dome(name,p,r,m);o.scale=stretch;return o

def footprint_axes(points):
 edges=[(math.dist(a,b),a,b) for a,b in zip(points,points[1:])];_,a,b=max(edges);ang=math.atan2(b[1]-a[1],b[0]-a[0]);co,si=math.cos(ang),math.sin(ang);xs=[p[0]*co+p[1]*si for p in points];ys=[-p[0]*si+p[1]*co for p in points];u=(min(xs)+max(xs))/2;v=(min(ys)+max(ys))/2
 return (u*co-v*si,u*si+v*co),max(xs)-min(xs),max(ys)-min(ys),ang

def stand(b):
 p=b['footprint'];(x,y),length,width,angle=footprint_axes(p);z=b['base'];height=min(28,max(14,b['height']))
 # Nested mapped footprints keep the stadium's bends and openings intact.
 for k in range(7):
  f=1-k*.025;pp=[(x+(px-x)*f,y+(py-y)*f) for px,py in p]
  poly('Grandstand seating tier',pp,z+k*height/7,height/7,'Seats' if k%2 else 'Concrete')
 if b['osm'] not in [377679562,1315400018]:poly('Grandstand canopy',p,z+height+2,1,'White')
 for px,py in p[::max(1,len(p)//8)]:box('Grandstand support',(px,py,z+height/2),(1.2,1.2,height),'White')

base=-8
surface('Mapped terrain',d['terrain'],'Sand' if d['id'] in ['losail','yas_marina','vegas'] else 'Grass' if d['id'] in ['americas','sepang','interlagos','rodriguez'] else 'Land')
poly('Compact tabletop base',d['boundary'],base-2,2,'Base')
for a,b in zip(d['boundary'],d['boundary'][1:]):mesh('Terrain edge',[(*a,base),(*b,base),(*b,ground(*b)-1.5),(*a,ground(*a)-1.5)],[(0,1,2,3)],'Sand' if d['id'] in ['losail','yas_marina'] else 'Land')
surface('Mapped water',d['waterTriangles'],'Water',-.7)
surface('Mapped parks',d['parks'],'Grass')
for a,b in zip(track,track[1:]+track[:1]):ribbon('Road foundation',(a[0],a[1],a[2]-1),(b[0],b[1],b[2]-1),18,1.2,'Quay')
for road in d['roads']:
 for a,b in zip(road,road[1:]):ribbon('Mapped street',(*a,ground(*a)-.8),(*b,ground(*b)-.8),8,.25,'Concrete')
# Major silhouettes are authored separately so generic boxes cannot duplicate them.
skip={253081850,253081914,253082095,299418016,116801004,172307471,172307472,51761904,230082125,256163011,256163012,976405284,27831699}
for b in d['buildings']:
 if b['osm'] in skip:continue
 if b['kind']=='stand':stand(b);continue
 p=b['footprint'];z=b['base'];h=b['height'];poly('Building foundation',p,base,z-base+.1,'Concrete');poly('Mapped building '+str(b['osm']),p,z,h,'Ivory' if h<45 else 'Glass');poly('Roof '+str(b['osm']),p,z+h,1,'Slate' if not kart else 'Red')
 for aa,bb in zip(p,p[1:]):
  length=math.dist(aa,bb)
  if length<15:continue
  angle=math.atan2(bb[1]-aa[1],bb[0]-aa[0])
  for k in range(1,min(9,int(h/6))):ribbon('Facade band',(*aa,z+k*h/min(9,int(h/6))),(*bb,z+k*h/min(9,int(h/6))),.7,1,'White' if h>45 else 'Glass')
for w in d['walls']:
 p=w['points']
 for aa,bb in zip(p,p[1:]):
  z=ground(*aa);ribbon('Old city rampart',(*aa,z+6),(*bb,ground(*bb)+6),4,12,'Limestone')
  n=max(1,int(math.dist(aa,bb)/7))
  for k in range(n):t=k/n;x=aa[0]+(bb[0]-aa[0])*t;y=aa[1]+(bb[1]-aa[1])*t;box('Castle crenellation',(x,y,ground(x,y)+12),(2.5,4.5,2),'Limestone')
landmarks={l['osm']:l for l in d['landmarks']}
# Mapped Baku towers, taper and curvature evoke their flame silhouettes.
if d['id']=='baku':
 for oid,height in [(253081850,182),(253081914,161),(253082095,165)]:
  if oid not in landmarks:continue
  l=landmarks[oid];x,y=l['center'];z=l['base'];p=l['footprint']
  for k in range(16):
   shrink=(1-k/17)**.55;dx=math.sin(k/16*math.pi/2)*12;pp=[(x+(px-x)*shrink+dx,y+(py-y)*shrink) for px,py in p];poly('Flame tower stepped glass',pp,z+k*height/16,height/16,'Glass');poly('Flame tower silver band',pp,z+(k+1)*height/16,.7,'White')
 if 299418016 in landmarks:
  l=landmarks[299418016];x,y=l['center'];z=l['base'];cylinder('Maiden Tower',(x,y,z+14),8,28,'Limestone',24)
  for level in range(3,28,4):cylinder('Maiden Tower stone band',(x,y,z+level),8.4,.8,'Quay',24)
# Sepang signature repeated umbrella roofs cover the central main grandstand.
if d['id']=='sepang' and 144247993 in landmarks:
 l=landmarks[144247993];(x,y),length,width,ang=footprint_axes(l['footprint']);z=l['base'];co,si=math.cos(ang),math.sin(ang)
 for k in range(18):
  u=(k/17-.5)*length;px,py=x+u*co,y+u*si;w=width/2+3;v=[(px+u1*co-v1*si,py+u1*si+v1*co,z+h) for u1,v1,h in [(-length/34,-w,20),(length/34,-w,20),(length/34,w,20),(-length/34,w,20),(0,0,29)]];mesh('Sepang umbrella canopy',v,[(0,1,4),(1,2,4),(2,3,4),(3,0,4)],'White')
# Singapore: three mapped towers with a continuous boat-shaped SkyPark.
if d['id']=='marina_bay':
 towers=[landmarks[k] for k in [116801004,172307472,172307471] if k in landmarks]
 for l in towers:
  x,y=l['center'];p=l['footprint'];z=l['base'];poly('Sands tower',p,z,190,'Ivory')
  for h in range(6,190,9):poly('Sands glazing',p,z+h,5,'Glass')
 if len(towers)==3:
  centers=[l['center'] for l in towers];aa,bb=centers[0],centers[-1];ang=math.atan2(bb[1]-aa[1],bb[0]-aa[0]);x,y=(aa[0]+bb[0])/2,(aa[1]+bb[1])/2;L=math.dist(aa,bb)+80;co,si=math.cos(ang),math.sin(ang);p=[(x+u*co-v*si,y+u*si+v*co) for u,v in [(-L/2,0),(-L*.4,-18),(L*.4,-18),(L/2,0),(L*.4,18),(-L*.4,18),(-L/2,0)]];poly('Sands SkyPark hull',p,190,9,'White');poly('Sands roof garden',p,199,1,'Grass');box('Sands infinity pool',(x,y,200),(L*.65,9,1),'Pool',ang)
 flyer=landmarks.get(51761904) or landmarks.get(230082125)
 if flyer:
  x,y=flyer['center'];z=ground(x,y);r=75;ang=.7;co,si=math.cos(ang),math.sin(ang);center=Vector((x,y,z+82));ring=[center+Vector((r*math.cos(t)*co,r*math.cos(t)*si,r*math.sin(t))) for t in [i*math.tau/64 for i in range(65)]]
  for aa,bb in zip(ring,ring[1:]):ribbon('Flyer rim',aa,bb,2,2,'White')
  for i in range(0,64,2):ribbon('Flyer spoke',center,ring[i],.55,.55,'White');sphere('Flyer capsule',ring[i],4,'Glass',(1,.6,.6))
  for side in [-1,1]:ribbon('Flyer A-frame',(x-si*side*30,y+co*side*30,z),center,4,4,'White')
 for oid in [256163011,256163012]:
  if oid in landmarks:
   l=landmarks[oid];x,y=l['center'];sphere('Esplanade shell',(x,y,l['base']+7),42,'Slate',(1,.72,.5))
# Circuit-specific major structures identified in the source manifest.
for landmark in d.get('special',[]):
 kind=landmark['kind'];x,y=landmark['center'];z=ground(x,y)
 if kind=='cota_tower':
  cylinder('Austin observation core',(x,y,z+37),4,74,'White',16);box('Austin observation deck',(x,y,z+74),(20,15,3),'White')
  for j in range(12):
   off=(j-5.5)*1.2;pts=[(x+off,y,z+76),(x+off,y+8,z+75),(x+off,y+17,z+67),(x+off,y+20,z+45),(x+off,y+22,z+20),(x+off,y+35,z+5),(x+off,y+65,z+3)]
   for aa,bb in zip(pts,pts[1:]):ribbon('Austin red tower ribbon',aa,bb,.9,.9,'Red')
 elif kind=='sphere':sphere('Las Vegas Sphere',(x,y,z+55),56,'Blue',(1,1,1))
 elif kind=='eiffel':
  for side in [-1,1]:
   for sy in [-1,1]:ribbon('Paris tower leg',(x+side*25,y+sy*25,z),(x+side*4,y+sy*4,z+115),3,3,'Gold')
  for h,w in [(35,38),(65,22),(95,12)]:box('Paris tower level',(x,y,z+h),(w,w,2),'Gold')
  ribbon('Paris tower spire',(x,y,z+100),(x,y,z+165),3,3,'Gold')
 elif kind=='yas_hotel':
  # Elevated lattice over the course: no solid mass blocking the road underneath.
  for triangle in landmark.get('bodyTriangles',[]):poly('Yas hotel body',triangle,z,25,'Glass')
  angle=landmark.get('angle',0);co,si=math.cos(angle),math.sin(angle)
  for u in range(-90,91,9):
   pts=[]
   for v in range(-36,37,6):pts.append((x+u*co-v*si,y+u*si+v*co,z+18+24*max(0,1-(v/40)**2)**.5+5*(1-(u/100)**2)))
   for aa,bb in zip(pts,pts[1:]):ribbon('Yas hotel luminous shell',aa,bb,1,1,'White')
  for v in range(-36,37,9):
   pts=[(x+u*co-v*si,y+u*si+v*co,z+18+24*max(0,1-(v/40)**2)**.5+5*(1-(u/100)**2)) for u in range(-90,91,9)]
   for aa,bb in zip(pts,pts[1:]):ribbon('Yas lattice longitudinal',aa,bb,.8,.8,'White')
for boat in d.get('boats',[]):
 x,y=boat['center'];angle=boat['angle'];L=boat['length'];w=boat['width'];co,si=math.cos(angle),math.sin(angle)
 p=[(x+u*co-v*si,y+u*si+v*co) for u,v in [(-L/2,-w/2),(L*.3,-w/2),(L/2,0),(L*.3,w/2),(-L/2,w/2),(-L/2,-w/2)]]
 poly('Docked yacht hull',p,0,2,'White');box('Docked yacht cabin',(x,y,3.2),(L*.5,w*.7,2.4),'Glass',angle);box('Docked yacht roof',(x,y,4.6),(L*.52,w*.8,.6),'White',angle)
# Trackside lights and barriers stay close to the actual course. Trees avoid roads.
for i,p in enumerate(track[::12]):
 q=track[(i*12+1)%len(track)];v=Vector((q[0]-p[0],q[1]-p[1],0)).normalized();side=Vector((-v.y,v.x,0));pos=Vector(p)+side*18
 if d['id'] in ['marina_bay','losail','yas_marina','vegas']:
  cylinder('Floodlight mast',(pos.x,pos.y,pos.z+10),.4,20,'White',6);box('Floodlight head',(pos.x,pos.y,pos.z+20),(4,2,1),'White')
 elif d['id'] in ['sepang','americas','interlagos','rodriguez']:
  cylinder('Tree trunk',(pos.x,pos.y,pos.z+3),.8,6,'Teak',6);sphere('Tree canopy',(pos.x,pos.y,pos.z+8),5,'Grass',(1,1,1.2))
# Semantic theme conversion preserves footprints, road clearance and landmark identity.
if kart:
 palette={'Grass':(.28,.67,.10),'Land':(.36,.62,.18),'Sand':(.88,.69,.30),'Water':(.015,.42,.85),'Ivory':(.97,.79,.45),'Limestone':(.82,.58,.31),'Slate':(.85,.15,.08),'Glass':(.05,.36,.67),'Concrete':(.68,.66,.53),'Seats':(.94,.24,.06),'Quay':(.85,.70,.37),'Base':(.15,.21,.10)}
 for name,color in palette.items():m=mats[name];m.diffuse_color=(*color,1);m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(*color,1)
 for name in ['Grass','Land','Water','Concrete']:
  m=mats[name];base=palette[name];img=bpy.data.images.new('Kart64_'+name,width=32,height=32);pixels=[]
  for j in range(32):
   for i in range(32):f=random.uniform(.8,1.12);pixels.extend([min(1,c*f) for c in base]+[1])
  img.pixels=pixels;img.pack();tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=img;tex.interpolation='Closest';m.node_tree.links.new(tex.outputs['Color'],m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
  for o in bpy.context.scene.objects:
   if o.type!='MESH' or not o.data.materials or o.data.materials[0]!=m:continue
   uv=o.data.uv_layers.new()
   for f in o.data.polygons:
    for li in f.loop_indices:v=o.data.vertices[o.data.loops[li].vertex_index].co+o.location;uv.data[li].uv=(v.x/24,v.y/24)
if tron:
 for m in mats.values():m.diffuse_color=(.008,.018,.032,1);p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=m.diffuse_color;p.inputs['Metallic'].default_value=.5
 for name,color in [('Neon',(.01,.65,1)),('Amber',(1,.25,.01))]:m=mat(name,color);p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=2
 bpy.context.view_layer.update();vs=[];fs=[]
 for o in list(bpy.context.scene.objects):
  if o.type!='MESH' or o.name.startswith(('Mapped terrain','Terrain edge','Mapped parks','Compact','Road foundation','Building foundation','Mapped street','Facade band')):continue
  # Roof and landmark contours, not every terrain triangle.
  if not o.name.startswith(('Docked yacht','Roof','Flame','Maiden','Sands','Flyer','Austin','Las Vegas','Paris','Yas','Grandstand canopy','Sepang','Old city')):continue
  for edge in o.data.edges:
   aa,bb=[o.matrix_world@o.data.vertices[i].co for i in edge.vertices];v=bb-aa
   if v.length<.1:continue
   side=v.cross(Vector((0,0,1)))
   if side.length<.1:side=v.cross(Vector((0,1,0)))
   side.normalize();side*=.5;n=len(vs);vs.extend([aa-side,aa+side,bb+side,bb-side]);fs.extend([(n,n+1,n+2,n+3),(n+3,n+2,n+1,n)])
 mesh('Neon architectural outlines',vs,fs,'Neon')
# Normalize to the exact app projection, preserving all relative dimensions.
for o in list(bpy.context.scene.objects):
 if o.type=='MESH':o.location.x=(o.location.x-cx)*scale;o.location.y=(o.location.y-cy)*scale;o.location.z*=scale;o.scale*=scale
bpy.ops.wm.save_as_mainfile(filepath=output.replace('.usdz','.blend'))
for m in mats.values():
 objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.data.materials and o.data.materials[0]==m]
 if not objects:continue
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();o=bpy.context.object;o.name=d['id']+'_'+m.name;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);mod=o.modifiers.new('Triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.ops.wm.usd_export(filepath=output,export_materials=True,generate_preview_surface=True,generate_materialx_network=False,export_lights=False,export_cameras=False,convert_orientation=True,export_global_forward_selection='NEGATIVE_Z',export_global_up_selection='Y',convert_scene_units='METERS',meters_per_unit=1.0)
for aa,bb in zip(track,track[1:]+track[:1]):
 p=((aa[0]-cx)*scale,(aa[1]-cy)*scale,aa[2]*scale);q=((bb[0]-cx)*scale,(bb[1]-cy)*scale,bb[2]*scale);ribbon('Preview course',p,q,12*scale,.0007,'Asphalt');v=Vector(q)-Vector(p)
 if v.length>.00001:
  side=Vector((-v.y,v.x,0)).normalized()*7*scale
  for sign in [-1,1]:ribbon('Preview curb',Vector(p)+side*sign,Vector(q)+side*sign,1.1*scale,.0008,'Neon' if tron else 'White')
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.render.resolution_x=1400;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.world.color=(.08,.08,.08) if tron else (.3,.3,.3)
bpy.ops.object.light_add(type='AREA',location=(-.5,-.4,1.2));bpy.context.object.data.energy=25;bpy.context.object.data.size=1
bpy.context.view_layer.update()
points=[o.matrix_world@Vector(v) for o in scene.objects if o.type=='MESH' for v in o.bound_box];lo=Vector(tuple(min(v[i] for v in points) for i in range(3)));hi=Vector(tuple(max(v[i] for v in points) for i in range(3)));center=(lo+hi)/2
bpy.ops.object.camera_add(location=center+Vector((.25,-.8,1.3)));cam=bpy.context.object;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=max(hi.x-lo.x,hi.y-lo.y)*1.36;scene.camera=cam;scene.render.image_settings.file_format='PNG';scene.render.filepath=preview;bpy.ops.render.render(write_still=True)
print('COMPLETE',d['id'],theme,flush=True)
