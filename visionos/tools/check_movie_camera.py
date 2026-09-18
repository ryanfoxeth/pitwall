"""Blender --background SCENE.blend --python check_movie_camera.py.
Checks the complete POV camera path for collisions with rendered geometry.
"""
import bpy,json
from pathlib import Path
scene=bpy.context.scene;camera=scene.camera;hits=[];previous=None
for f in range(241,1441):
 scene.frame_set(f);p=camera.location.copy()
 if previous is not None:
  delta=p-previous
  if delta.length>.001:
   hit,point,normal,index,obj,matrix=scene.ray_cast(bpy.context.evaluated_depsgraph_get(),previous,delta.normalized(),distance=delta.length)
   if hit and not (obj.parent and obj.parent.name=='Staged lead car'):hits.append({'frame':f,'object':obj.name,'point':list(point)})
 previous=p
out=Path(bpy.data.filepath).parent/'camera-collisions.json';out.write_text(json.dumps(hits,indent=2));print('CAMERA COLLISIONS',len(hits),flush=True)

if hits:raise RuntimeError(f"POV camera intersects geometry on {len(hits)} frames")
