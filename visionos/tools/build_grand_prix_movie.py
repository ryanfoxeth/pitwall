"""Blender: -- SCENE_JSON OUTPUT_DIR [preview|render]. Geographic Grand Prix fly-in/full lap."""
import bpy,sys,json,math,tempfile
from pathlib import Path
from mathutils import Vector
TOOLS=Path(__file__).parent;sys.path.insert(0,str(TOOLS))
args=sys.argv[sys.argv.index('--')+1:];datafile=Path(args[0]);dest=Path(args[1]);mode=args[2] if len(args)>2 else 'preview';dest.mkdir(parents=True,exist_ok=True)
D=json.loads(datafile.read_text());cid=D['id'];script=TOOLS/('build_monaco_blender.py' if cid=='monaco' else 'build_season_blender.py');source=script.read_text();marker='# Triangulate and batch by material;' if cid=='monaco' else '# Normalize to the exact app projection'
source=source[:source.index(marker)]
# Reuse mapped Grand Prix geometry at world metre scale, before app normalization.
if cid!='monaco':
 # Permanent parkland circuits use the same Grand Prix grass material as Austin.
 # City circuits retain their mapped urban ground treatment.
 source=source.replace("['americas','sepang','interlagos','rodriguez']", "['americas','sepang','interlagos','rodriguez','suzuka','catalunya','red_bull_ring','silverstone','spa','hungaroring','zandvoort','monza','villeneuve']")
 start=source.index('def ground(');end=source.index('\ndef surface(',start);source=source[:start]+"from terrain_grid import TerrainGrid\nterrain_sampler=TerrainGrid(d['terrainGrid'])\ndef ground(x,y):return terrain_sampler.height(x,y)\n"+source[end:]
 source=source.replace('base=-8',"base=min(p[2] for tri in d['terrain'] for p in tri)-3")
 source=source.replace("z=b['base'];height=","z=b['base'];poly('Stadium ground foundation',p,base,z-base+.1,'Concrete');height=")
 source=source.replace("'Water',-.7)","'Water',d['waterLevel'])")
sys.argv=['blender','--',str(datafile),str(dest/'scenery.usdz'),str(dest/'scenery.png'),'grandPrix']
exec(compile(source,str(script),'exec'),globals())
# Smooth the planar route densely without normalizing its physical dimensions.
raw=[Vector(p) for p in D['track']]
if (raw[0]-raw[-1]).length<.01:raw.pop()
pts=[]
for i,p1 in enumerate(raw):
 p0,p2,p3=raw[i-1],raw[(i+1)%len(raw)],raw[(i+2)%len(raw)]
 for j in range(max(2,math.ceil((p2-p1).length/3))):
  t=j/max(2,math.ceil((p2-p1).length/3));pts.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
N=len(pts);roadverts=[];curbverts=[[],[]]
for i,p in enumerate(pts):
 tangent=pts[(i+1)%N]-pts[i-1];side=Vector((-tangent.y,tangent.x,0)).normalized()
 roadverts += [p-side*6+Vector((0,0,.15)),p+side*6+Vector((0,0,.15))]
 for k,sign in enumerate([-1,1]):curbverts[k]+=[p+side*sign*6+Vector((0,0,.22)),p+side*sign*7+Vector((0,0,.22))]
faces=[(2*i,2*i+1,2*((i+1)%N)+1,2*((i+1)%N)) for i in range(N)];mesh('Grand Prix continuous asphalt',roadverts,faces,'Asphalt')
for vv in curbverts:
 for parity,material in [(0,'White'),(1,'Red')]:mesh('Alternating kerb',vv,[f for i,f in enumerate(faces) if (i//3)%2==parity],material)
# Gravel shoulders bridge the independent DEM terrain and engineered road mesh.
from terrain_grid import TerrainGrid
sampler=TerrainGrid(D['terrainGrid'])
for sign in [-1,1]:
 vv=[]
 for i,p in enumerate(pts):
  tangent=pts[(i+1)%N]-pts[i-1];side=Vector((-tangent.y,tangent.x,0)).normalized()*sign;outer=p+side*12;outer.z=sampler.height(outer.x,outer.y)-.45
  if D.get('modeledBridge') and (Vector((p.x,p.y))-Vector(D['modeledBridge']['center'])).length<28:outer.z=p.z-.1
  vv.extend([p+side*6+Vector((0,0,.1)),outer])
 mesh('Continuous road verge',vv,faces,'Quay')
# Painted start/finish across the first reference point; not an official timing marker.
p=pts[0];v=(pts[1]-p).normalized();side=Vector((-v.y,v.x,0)).normalized()
for row in range(2):
 for col in range(12):
  o=box('Start finish checker',p+v*(row-.5)+side*(col-5.5)+Vector((0,0,.25)),(1,1,.025),'White' if (row+col)%2 else 'Slate');o.rotation_euler.z=math.atan2(v.y,v.x)
# Batch static geometry by material to keep Eevee draw calls bounded.
for m in list(bpy.data.materials):
 objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.data.materials and o.data.materials[0]==m]
 if not objects:continue
 bpy.ops.object.select_all(action='DESELECT')
 for o in objects:o.select_set(True)
 bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join()
# Meter-based subtle surface variation, shared consistently across circuits.
for material_name,colors,noise_scale in [('Asphalt',((.045,.05,.055,1),(.09,.10,.105,1)),3),('Grass',((.055,.13,.025,1),(.16,.25,.075,1)),.018),('Land',((.24,.23,.19,1),(.38,.37,.31,1)),.025)]:
 material=bpy.data.materials.get(material_name)
 if material is None:continue
 nodes=material.node_tree.nodes;links=material.node_tree.links;geo=nodes.new('ShaderNodeNewGeometry');noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=noise_scale;noise.inputs['Detail'].default_value=2;links.new(geo.outputs['Position'],noise.inputs['Vector']);ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=colors[0];ramp.color_ramp.elements[1].color=colors[1];links.new(noise.outputs['Fac'],ramp.inputs['Fac']);links.new(ramp.outputs['Color'],nodes.get('Principled BSDF').inputs['Base Color'])
# A clearly staged Grand Prix car ahead gives the POV scale and motion.
mat('Race cyan',(.015,.42,.58),.3,.3);mat('Rubber',(.012,.016,.02),.9);car=bpy.data.objects.new('Staged lead car',None);bpy.context.collection.objects.link(car)
def part(name,p,size,m):
 o=box(name,p,size,m);o.parent=car;return o
part('Monocoque',(0,0,.55),(2.8,.65,.6),'Race cyan');part('Nose',(1.9,0,.37),(1.4,.28,.28),'Race cyan');part('Front wing',(2.45,0,.22),(.38,1.9,.12),'Slate');part('Rear wing',(-1.9,0,.95),(.4,1.6,.16),'White');part('Engine cover',(-.85,0,.9),(1.2,.42,.5),'Race cyan')
for x in [-1.35,1.45]:
 for y in [-.83,.83]:
  o=cylinder('Race tyre',(x,y,.4),.38,.34,'Rubber',16);o.rotation_euler.x=math.pi/2;o.parent=car
# Original tunnel luminaires keep the covered Monaco section readable.
if cid=='monaco':
 tunnel_points=D['tunnel']
 for i in range(0,len(tunnel_points),max(1,len(tunnel_points)//9)):
  x,y=tunnel_points[i];z=ground(x,y)+6
  bpy.ops.object.light_add(type='AREA',location=(x,y,z));lamp=bpy.context.object;lamp.name='Tunnel ceiling illumination';lamp.data.energy=3500;lamp.data.shape='DISK';lamp.data.size=7;lamp.data.color=(1,.87,.68)
# Distance-based sampling avoids speed changes from vertex density.
lengths=[0.]
for i,p in enumerate(pts):lengths.append(lengths[-1]+(pts[(i+1)%N]-p).length)
L=lengths[-1]
import bisect
def at(distance):
 s=distance%L;i=min(N-1,bisect.bisect_right(lengths,s)-1);t=(s-lengths[i])/max(1e-8,lengths[i+1]-lengths[i]);return pts[i].lerp(pts[(i+1)%N],t)
scene=bpy.context.scene
# Eevee renders geographic scenes with materials and sun shadows.
try:scene.render.engine='BLENDER_EEVEE'
except TypeError:scene.render.engine='BLENDER_EEVEE_NEXT'
scene.eevee.taa_render_samples=16
scene.render.resolution_x=1280;scene.render.resolution_y=720;scene.render.resolution_percentage=100;scene.render.fps=24;scene.frame_start=1;scene.frame_end=1440
scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.24,.32,.45,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.025
sky=scene.world.node_tree.nodes.new('ShaderNodeTexSky');sky.sky_type='MULTIPLE_SCATTERING';sky.sun_elevation=.55;sky.sun_rotation=-.5;sky.sun_disc=False;scene.world.node_tree.links.new(sky.outputs['Color'],scene.world.node_tree.nodes['Background'].inputs[0])
bpy.ops.object.light_add(type='SUN',location=(0,0,1000));sun=bpy.context.object;sun.rotation_euler=(.45,-.5,-.5);sun.data.energy=2.5;sun.data.angle=.12
bpy.ops.object.camera_add();cam=bpy.context.object;cam.name='Orbit dive full lap';scene.camera=cam;cam.data.lens=22;cam.data.clip_start=.12;cam.data.clip_end=20000;cam.rotation_mode='QUATERNION'
bpy.context.view_layer.update()
bounds=[o.matrix_world@Vector(v) for o in scene.objects if o.type=='MESH' and o.parent!=car for v in o.bound_box];lo=Vector(tuple(min(v[j] for v in bounds) for j in range(3)));hi=Vector(tuple(max(v[j] for v in bounds) for j in range(3)));center=(lo+hi)/2;span=max(hi.x-lo.x,hi.y-lo.y);radius=span*1.05;start=0
# 6 s orbit, 4 s descent, 50 s complete lap. Camera is a forward-facing car POV.
for frame in range(1,1441):
 u=(frame-1)/1439
 if frame<=144:
  angle=-math.pi/2+(frame-1)/143*math.pi*.65;pos=center+Vector((radius*math.cos(angle),radius*math.sin(angle),span*.85));target=center
 elif frame<=240:
  t=(frame-144)/96;s=t*t*(3-2*t);angle=-math.pi/2+math.pi*.65;above=center+Vector((radius*math.cos(angle),radius*math.sin(angle),span*.85));low=at(start)+Vector((0,0,2.4));pos=above.lerp(low,s);target=center.lerp(at(start+25)+Vector((0,0,1.5)),s)
 else:
  distance=start+(frame-241)/1199*L;pos=at(distance)+Vector((0,0,2.4));target=at(distance+22)+Vector((0,0,1.9))
 cam.data.lens=26 if frame<=144 else (26-4*min(1,(frame-144)/96));cam.data.keyframe_insert(data_path='lens',frame=frame)
 cam.location=pos;cam.rotation_quaternion=(target-pos).to_track_quat('-Z','Y');cam.keyframe_insert(data_path='location',frame=frame);cam.keyframe_insert(data_path='rotation_quaternion',frame=frame)
 distance=start+max(0,(frame-241)/1199)*L+30;car.location=at(distance)+Vector((0,0,.25));direction=at(distance+2)-at(distance);car.rotation_euler=direction.to_track_quat('X','Z').to_euler();car.keyframe_insert(data_path='location',frame=frame);car.keyframe_insert(data_path='rotation_euler',frame=frame)
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';frame_dir=Path(tempfile.gettempdir())/'pitwall-grand-prix-frames'/cid;frame_dir.mkdir(parents=True,exist_ok=True);scene.render.filepath=str(frame_dir/'frame-');scene.render.use_overwrite=False
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.render.film_transparent=False
bpy.ops.wm.save_as_mainfile(filepath=str(dest/'Grand Prix Lap.blend'))
(dest/'manifest.json').write_text(json.dumps({'circuit':cid,'name':D['name'],'frames':1440,'fps':24,'width':1280,'height':720,'duration':60,'camera':'6s orbit, 4s dive, one complete 50s POV lap','motion':'Staged cinematic motion, not a historical race replay','terrain':D['groundSource'],'engineeringNotes':D['engineeringNotes']},indent=2))
if mode=='render':bpy.ops.render.render(animation=True)
else:
 for f in [100,240,500,900,1300]:scene.frame_set(f);scene.render.filepath=str(dest/f'preview-{f}.png');bpy.ops.render.render(write_still=True)
