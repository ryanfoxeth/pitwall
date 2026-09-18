import bpy, math
from mathutils import Vector
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
