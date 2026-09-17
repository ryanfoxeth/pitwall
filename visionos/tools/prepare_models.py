import bpy, pathlib, math, json, shutil
from mathutils import Vector
P=pathlib.Path(__file__).resolve().parents[1]
out=P/'Sources/Resources/Models';out.mkdir(exist_ok=True)
assets={'Kart':('car-kit','GLB format','kart-oobi'),'Tree':('nature-kit','GLTF format','tree_oak'),'Pine':('nature-kit','GLTF format','tree_pineTallA'),'Bush':('nature-kit','GLTF format','plant_bushLarge'),'Mushroom':('nature-kit','GLTF format','mushroom_redGroup'),'Rock':('nature-kit','GLTF format','rock_largeA'),'Palm':('nature-kit','GLTF format','tree_palm')}
manifest=[]
for name,(pack,fmt,file) in assets.items():
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 src=P/'tools/asset-cache'/pack/'Models'/fmt/(file+'.glb')
 if not src.exists():src=P/'Assets/Source'/(name+'.glb')
 bpy.ops.import_scene.gltf(filepath=str(src))
 meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
 points=[o.matrix_world@Vector(c) for o in meshes for c in o.bound_box]
 lo=Vector(tuple(min(p[i] for p in points) for i in range(3)));hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
 scale=1/max(hi-lo);center=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
 # Bake world transform then normalize with bottom pivot; USD's declared Z-up handles RealityKit conversion.
 for o in meshes:
  world=o.matrix_world.copy();o.parent=None;o.matrix_world.identity()
  for v in o.data.vertices:v.co=(world@v.co-center)*scale
 for o in meshes:
  for mat in o.data.materials:
   if mat and mat.use_nodes:
    node=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if node:
     node.inputs['Metallic'].default_value=0
     node.inputs['Roughness'].default_value=0.85
 bpy.ops.wm.usd_export(filepath=str(out/(name+'.usdz')),export_animation=False,convert_world_material=False,export_lights=False,convert_orientation=True,export_global_forward_selection="NEGATIVE_Z",export_global_up_selection="Y")
 bpy.ops.export_scene.gltf(filepath=str(P/'Assets/Source'/(name+'.glb')),export_format='GLB')
 manifest.append({'name':name,'source':str(src.relative_to(P)),'pack':pack,'license':'CC0','meshes':len(meshes),'polygons':sum(len(o.data.polygons) for o in meshes)})
for pack in ['car-kit','nature-kit']:
 for f in (P/'tools/asset-cache'/pack).glob('*icense*'):shutil.copy(f,P/'Assets/Source'/(pack+'-'+f.name))
(P/'Assets/Source/manifest.json').write_text(json.dumps(manifest,indent=2))
print('MODELS DONE',manifest)
