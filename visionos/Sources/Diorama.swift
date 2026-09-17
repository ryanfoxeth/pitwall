import RealityKit
import SwiftUI
import UIKit

// Terrain and dressing are artistic; the road and observed cars retain recorded XYZ.
enum CircuitWorld {
 case park, harbor, desert, alpine, tropical
 static func forTitle(_ title:String)->Self {
  let t=title.lowercased()
  if ["monaco","monte carlo","baku","azerbaijan"].contains(where:t.contains){return .harbor}
  if ["bahrain","sakhir","qatar","lusail","abu dhabi","yas marina","jeddah","las vegas"].contains(where:t.contains){return .desert}
  if ["austria","spielberg","spa","belgium"].contains(where:t.contains){return .alpine}
  if ["singapore","miami","são paulo","sepang"].contains(where:t.contains){return .tropical}
  return .park
 }
}
@MainActor final class Diorama {
 var points:[SIMD3<Float>];var world:CircuitWorld;var theme:RaceTheme
 init(_ points:[SIMD3<Float>],world:CircuitWorld,theme:RaceTheme){self.points=points;self.world=world;self.theme=theme}
 func nearest(_ x:Float,_ z:Float)->(Float,Float){
  var distance=Float.infinity,y:Float=0
  for i in points.indices {
   let a=points[i],b=points[(i+1)%points.count],v=SIMD2(b.x-a.x,b.z-a.z),w=SIMD2(x-a.x,z-a.z)
   let t=max(0,min(1,simd_dot(w,v)/max(0.0000001,simd_dot(v,v))))
   let d=simd_length(w-v*t)
   if d<distance {distance=d;y=a.y+(b.y-a.y)*t}
  }
  return (distance,y)
 }
 func inside(_ x:Float,_ z:Float)->Bool {
  var inside=false
  for i in points.indices {let a=points[i],b=points[(i+1)%points.count]
   if (a.z>z) != (b.z>z), x < (b.x-a.x)*(z-a.z)/(b.z-a.z)+a.x {inside.toggle()}
  };return inside
 }
 func contains(_ x:Float,_ z:Float)->Bool{inside(x,z) || nearest(x,z).0<0.026}
 lazy var featureCenter:SIMD3<Float>? = {
  var best:SIMD3<Float>?,clearance:Float=0.043
  let xs=points.map(\.x),zs=points.map(\.z)
  for i in 0..<20 {for j in 0..<20 {
   let x=(xs.min() ?? 0)+Float(i)/19*((xs.max() ?? 0)-(xs.min() ?? 0)),z=(zs.min() ?? 0)+Float(j)/19*((zs.max() ?? 0)-(zs.min() ?? 0))
   let d=nearest(x,z).0
   if inside(x,z) && d>clearance {clearance=d;best=SIMD3(x,0,z)}
  }};return best
 }()
 func height(_ x:Float,_ z:Float)->Float{
  if theme == .kart,world != .desert,let c=featureCenter {
   let radius=simd_length(SIMD2(x-c.x,z-c.z))
   if radius<0.033 {return -0.007+0.010*min(1,max(0,(radius-0.024)/0.009))}
  }
  let (d,y)=nearest(x,z)
  if theme != .kart{return y-0.001}
  let blend=min(1,max(0,(d-0.012)/0.026))
  let hill:Float=world == .alpine ? 0.034:0.016
  return (y-0.001)*(1-blend)+blend*(0.002+hill*(0.5+0.5*sin(x*43)*cos(z*37)))
 }
 func mesh()->Entity {
  let root=Entity();var groups=[Int:[SIMD3<Float>]]()
  let step:Float=0.008
  let minX=(points.map(\.x).min() ?? 0)-0.027,maxX=(points.map(\.x).max() ?? 0)+0.027
  let minZ=(points.map(\.z).min() ?? 0)-0.027,maxZ=(points.map(\.z).max() ?? 0)+0.027
  let nx=Int(ceil((maxX-minX)/step)),nz=Int(ceil((maxZ-minZ)/step))
  var filled=Set<Int>()
  for i in 0..<nx {for j in 0..<nz {if contains(minX+(Float(i)+0.5)*step,minZ+(Float(j)+0.5)*step){filled.insert(i*nz+j)}}}
  for i in 0..<nx {for j in 0..<nz where filled.contains(i*nz+j){
   let x=minX+Float(i)*step,z=minZ+Float(j)*step
   let p=[SIMD3(x,height(x,z),z),SIMD3(x+step,height(x+step,z),z),SIMD3(x+step,height(x+step,z+step),z+step),SIMD3(x,height(x,z+step),z+step)]
   let d=nearest(x+step/2,z+step/2).0
   let group=theme == .kart ? (d<0.020 ? 2:(i+j)%3==0 ? 1:0):0
   groups[group,default:[]] += [p[0],p[2],p[1],p[0],p[3],p[2]]
   let bottom=p.map{SIMD3($0.x,Float(-0.023),$0.z)}
   groups[3,default:[]] += [bottom[0],bottom[1],bottom[2],bottom[0],bottom[2],bottom[3]]
   for (a,b,di,dj) in [(0,1,0,-1),(1,2,1,0),(2,3,0,1),(3,0,-1,0)] {
    let ni=i+di,nj=j+dj
    if ni<0 || nj<0 || ni>=nx || nj>=nz || !filled.contains(ni*nz+nj) {
     let lowA=SIMD3(p[a].x,Float(-0.023),p[a].z),lowB=SIMD3(p[b].x,Float(-0.023),p[b].z)
     groups[3,default:[]] += [p[a],p[b],lowB,p[a],lowB,lowA]
    }
   }
  }}
  let grass=world == .desert ? UIColor(red:0.78,green:0.57,blue:0.28,alpha:1):UIColor(red:0.38,green:0.67,blue:0.19,alpha:1)
  let colors:[UIColor]=[theme == .kart ? grass:theme.ground,grass.withAlphaComponent(1).darker,UIColor(red:0.82,green:0.72,blue:0.45,alpha:1),theme == .tron ? .darkGray:UIColor(red:0.35,green:0.25,blue:0.17,alpha:1)]
  for (group,vertices) in groups {
   var desc=MeshDescriptor();desc.positions=MeshBuffers.Positions(vertices)
   var normals:[SIMD3<Float>]=[]
   for i in stride(from:0,to:vertices.count,by:3){let n=simd_normalize(simd_cross(vertices[i+1]-vertices[i],vertices[i+2]-vertices[i]));normals += [n,n,n]}
   desc.normals=MeshBuffers.Normals(normals);desc.primitives = .triangles((0..<UInt32(vertices.count)).map{$0})
   if let mesh=try? MeshResource.generate(from:[desc]){root.addChild(ModelEntity(mesh:mesh,materials:[SimpleMaterial(color:colors[group],roughness:1,isMetallic:false)]))}
  }
  return root
 }
}
extension UIColor {
 var darker:UIColor{var r:CGFloat=0,g:CGFloat=0,b:CGFloat=0,a:CGFloat=0;getRed(&r,green:&g,blue:&b,alpha:&a);return UIColor(red:r*0.9,green:g*0.94,blue:b*0.9,alpha:a)}
}
@MainActor enum ModelLibrary {
 static var cache:[String:Entity]=[:]
 static func model(_ name:String,size:Float)->Entity?{
  if cache[name]==nil,let url=Bundle.main.url(forResource:name,withExtension:"usdz") {cache[name]=try? Entity.load(contentsOf:url)}
  guard let source=cache[name] else{return nil}
  let e=source.clone(recursive:true),bounds=e.visualBounds(relativeTo:nil)
  e.scale *= SIMD3(repeating:size/max(bounds.extents.x,max(bounds.extents.y,bounds.extents.z)))
  let parent=Entity();parent.addChild(e)
  let actual=e.visualBounds(relativeTo:parent);e.position -= SIMD3(actual.center.x,actual.min.y,actual.center.z)
  return parent
 }
}
