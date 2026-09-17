import RealityKit
import UIKit

/// Original reusable tabletop model. Forward is +X; shared meshes are cloned per driver.
@MainActor enum FormulaVehicle {
 static let template: Entity = {
  let root=Entity()
  func part(_ name:String,_ size:SIMD3<Float>,_ p:SIMD3<Float>,_ color:UIColor,rounded:Bool=false) {
   let mesh:MeshResource = rounded ? .generateSphere(radius:1) : .generateBox(size:size,cornerRadius:0.0002)
   let e=ModelEntity(mesh:mesh,materials:[SimpleMaterial(color:color,roughness:0.45,isMetallic:false)])
   if rounded {e.scale=size/2};e.position=p;e.name=name;root.addChild(e)
  }
  let carbon=UIColor(white:0.055,alpha:1)
  part("floor",[0.026,0.0007,0.010],[0,0.0015,0],carbon)
  part("livery",[0.019,0.0045,0.005],[-0.002,0.004,0],.white,rounded:true)
  part("livery",[0.012,0.002,0.0025],[0.008,0.003,0],.white,rounded:true)
  for z:Float in [-1,1] {
   part("livery",[0.011,0.0035,0.003],[-0.003,0.0035,z*0.0035],.white,rounded:true)
   for x:Float in [-0.008,0.008] {
    let tire=ModelEntity(mesh:.generateCylinder(height:0.0028,radius:0.0032),materials:[SimpleMaterial(color:carbon,roughness:0.9,isMetallic:false)])
    tire.orientation=simd_quatf(angle:.pi/2,axis:[1,0,0]);tire.position=[x,0.0032,z*0.006];tire.name="tire";root.addChild(tire)
    let hub=ModelEntity(mesh:.generateCylinder(height:0.0029,radius:0.0017),materials:[SimpleMaterial(color:.darkGray,roughness:0.3,isMetallic:true)])
    hub.orientation=tire.orientation;hub.position=tire.position;root.addChild(hub)
    for dx:Float in [-0.002,0.002] {
     let a=SIMD3<Float>(x+dx,0.003,z*0.002),b=SIMD3<Float>(x,0.003,z*0.006)
     let arm=ModelEntity(mesh:.generateBox(size:[0.00045,0.00045,simd_distance(a,b)]),materials:[SimpleMaterial(color:carbon,roughness:0.7,isMetallic:false)])
     arm.position=(a+b)/2;arm.orientation=simd_quatf(from:[0,0,1],to:simd_normalize(b-a));root.addChild(arm)
    }
   }
   part("halo",[0.006,0.0006,0.0006],[0.001,0.0065,z*0.0017],carbon)
   part("livery",[0.0035,0.003,0.0005],[-0.012,0.006,z*0.0055],.white)
  }
  part("cockpit",[0.005,0.001,0.003],[0,0.006,0],carbon,rounded:true)
  part("helmet",[0.0021,0.002,0.0021],[-0.0006,0.0065,0],.white,rounded:true)
  part("visor",[0.0005,0.0007,0.0018],[0.0004,0.0066,0],.black)
  part("halo",[0.0006,0.002,0.0006],[0.004,0.0057,0],carbon)
  part("halo",[0.0006,0.0006,0.004],[0.0038,0.0065,0],carbon)
  for x:Float in [0.012,0.0135] {part("front-wing",[0.001,0.0005,0.013],[x,0.002,0],carbon)}
  for y:Float in [0.006,0.007] {part("livery",[0.003,0.0005,0.011],[-0.012,y,0],.white)}
  part("airbox",[0.004,0.003,0.002],[-0.004,0.007,0],carbon,rounded:true)
  return root
 }()
 static func make(number:Int)->Entity {
  let car=template.clone(recursive:true)
  // Oversized number plates remain readable at tabletop scale from above or either side.
  func badge(_ name:String, at position:SIMD3<Float>, rotation:simd_quatf, size:SIMD2<Float>) {
   let plate=Entity();plate.name=name;plate.position=position;plate.orientation=rotation
   let backing=ModelEntity(mesh:.generateBox(size:[size.x,size.y,0.00018],cornerRadius:0.00035),materials:[UnlitMaterial(color:.white)])
   plate.addChild(backing)
   let label=ModelEntity(mesh:.generateText(String(number),extrusionDepth:0.001,font:.systemFont(ofSize:1,weight:.black)),materials:[UnlitMaterial(color:.black)])
   label.name="driver-number"
   let bounds=label.visualBounds(relativeTo:label)
   let scale=min(size.x*0.82/max(bounds.extents.x,0.001),size.y*0.82/max(bounds.extents.y,0.001))
   label.scale=SIMD3(repeating:scale)
   label.position = -bounds.center*scale + SIMD3(0,0,0.00013)
   plate.addChild(label);car.addChild(plate)
  }
  badge("number-nose",at:[0.008,0.0047,0],rotation:simd_quatf(angle:-.pi/2,axis:[1,0,0]),size:[0.0065,0.005])
  badge("number-right",at:[-0.001,0.004,0.0052],rotation:simd_quatf(angle:0,axis:[0,1,0]),size:[0.009,0.0046])
  badge("number-left",at:[-0.001,0.004,-0.0052],rotation:simd_quatf(angle:.pi,axis:[0,1,0]),size:[0.009,0.0046])
  return car
 }
}
