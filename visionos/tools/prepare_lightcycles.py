"""Normalize user-downloaded CC-BY Sketchfab models; preserve authored materials."""
import bpy, pathlib, math, json
from mathutils import Vector, Matrix
P=pathlib.Path(__file__).resolve().parents[1]
for name in ['Firestar','SpringSociety']:
 bpy.ops.wm.read_factory_settings(use_empty=True)
 bpy.ops.import_scene.gltf(filepath=str(P/'Assets/Source/Lightcycles'/f'{name}.glb'))
 keep={'Object_10','Object_11','Object_12','Object_13'} if name=='Firestar' else {'Object_65'}
 meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name in keep]
 # Bake evaluated meshes, including the source skeletal rest pose.
 baked=[]
 deps=bpy.context.evaluated_depsgraph_get()
 for o in meshes:
  mesh=bpy.data.meshes.new_from_object(o.evaluated_get(deps),depsgraph=deps)
  new=bpy.data.objects.new('cycle-'+o.name,mesh);bpy.context.collection.objects.link(new)
  world=o.matrix_world.copy()
  for v in mesh.vertices:v.co=world@v.co
  baked.append(new)
 for o in list(bpy.context.scene.objects):
  if o not in baked:bpy.data.objects.remove(o,do_unlink=True)
 points=[v.co for o in baked for v in o.data.vertices]
 lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)])
 center=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z));scale=1/max(hi-lo)
 # Both source bikes run along Y; rotate into app forward +X (verify preview).
 rot=Matrix.Rotation(-math.pi/2,4,'Z')
 for o in baked:
  for v in o.data.vertices:v.co=rot@((v.co-center)*scale)
 bpy.ops.wm.usd_export(filepath=str(P/'Sources/Resources/Models'/f'Cycle{name}.usdz'),export_animation=False,convert_world_material=False,export_lights=False,convert_orientation=True,export_global_forward_selection='NEGATIVE_Z',export_global_up_selection='Y')
 # Offline inspection render of precisely the normalized geometry.
 scene=bpy.context.scene
 scene.render.engine='CYCLES';scene.cycles.samples=16
 scene.world=bpy.data.worlds.new('Studio');scene.world.use_nodes=True
 scene.world.node_tree.nodes.get('Background').inputs[0].default_value=(0.12,0.12,0.12,1)
 scene.world.node_tree.nodes.get('Background').inputs[1].default_value=0.6
 for pos,power,size in [((1,-2,3),500,3),((-1,2,2),350,2)]:
  bpy.ops.object.light_add(type='AREA',location=pos);bpy.context.object.data.energy=power;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=size
 bpy.ops.object.camera_add(location=(1.3,-1.8,1.1));cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,0.16))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=1.4;scene.camera=cam
 scene.render.resolution_x=1000;scene.render.resolution_y=700;scene.render.resolution_percentage=100
 scene.render.filepath=str(P/'Evidence'/f'cycle-{name}.png');bpy.ops.render.render(write_still=True)
 print('EXPORTED',name,[(o.name,len(o.data.polygons)) for o in baked])
