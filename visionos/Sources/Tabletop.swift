import SwiftUI
import RealityKit
import UIKit
import Spatial

@MainActor final class TableScene:ObservableObject {
 let coordinateRoot=Entity()
 let presentation=Entity()
 let circuit=Entity()
 init() { coordinateRoot.addChild(presentation); presentation.addChild(root) }
 let root=Entity();var bikes:[Int:Entity]=[:];var trails:[ModelEntity]=[];var lastTrack:[SIMD3<Float>]=[];var theme:RaceTheme = .tron;var lastColors:[Int:UIColor]=[:];var lastTitle="";var previousHeading:[Int:Float]=[:];var lastFrameTime=Date();var vehicleRoles:[Int:String]=[:]
 var lastFitDiagnostic = ""
 var center=SIMD3<Float>.zero;var factor:Float=1;var baseZ:Float=0
 func fit(in available: BoundingBox) {
  guard available.extents.x > 0.05, available.extents.y > 0.01, available.extents.z > 0.05 else { return }
  // Measure in the presentation parent's coordinates. Scene/world bounds can
  // include system volume scaling, feeding that scale back into our next fit.
  root.position = .zero
  root.scale = SIMD3(repeating: 1)
  // Cars and trails must never control the circuit’s size or center.
  let bounds = (circuit.parent == nil ? root : circuit).visualBounds(relativeTo: presentation)
  let extent = simd_max(bounds.extents, SIMD3(repeating: 0.001))
  let ratios = available.extents / extent
  let scale = max(0.001, min(ratios.x,min(ratios.y,ratios.z))*0.96)
  presentation.scale = SIMD3(repeating: scale)
  presentation.position = available.center-bounds.center*scale
  #if DEBUG
  let diagnostic = "target=\(available)\nmodel=\(bounds)\nscale=\(scale)\nposition=\(presentation.position)\ntrack=\(lastTitle)\n"
  if diagnostic != lastFitDiagnostic {
   lastFitDiagnostic = diagnostic
   let url = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("tabletop-fit.txt")
   try? diagnostic.write(to: url, atomically: true, encoding: .utf8)
  }
  #endif
 }
 func project(_ p:SIMD3<Float>)->SIMD3<Float>{SIMD3((p.x-center.x)*factor,(p.z-baseZ)*factor+0.006,-(p.y-center.y)*factor)}
 func material(_ c:UIColor)->UnlitMaterial{UnlitMaterial(color:c)}
 func segment(_ a:SIMD3<Float>,_ b:SIMD3<Float>,width:Float,height:Float?=nil,color:UIColor)->ModelEntity{
  let e=ModelEntity(mesh:.generateBox(size:SIMD3(width,height ?? width,max(0.00001,simd_distance(a,b)))),materials:[material(color)]);e.position=(a+b)/2;e.orientation=simd_quatf(from:SIMD3(0,0,1),to:simd_normalize(b-a+SIMD3(0,0,0.0000001)));return e
 }
 func build(_ track:[SIMD3<Float>], theme:RaceTheme, title:String="") {
  self.theme=theme;lastTitle=title;lastColors=[:];previousHeading=[:]
  root.children.removeAll();circuit.children.removeAll();root.addChild(circuit);bikes=[:];vehicleRoles=[:];trails=[];lastTrack=track
  guard track.count>2 else{return}
  let xs=track.map(\.x),ys=track.map(\.y);center=SIMD3(((xs.min() ?? 0)+(xs.max() ?? 0))/2,((ys.min() ?? 0)+(ys.max() ?? 0))/2,0);factor=0.55/max(1,max((xs.max() ?? 1)-(xs.min() ?? 0),(ys.max() ?? 1)-(ys.min() ?? 0)));baseZ=track.map(\.z).min() ?? 0
  let terrain=Diorama(track.map(project),world:CircuitWorld.forTitle(title),theme:theme)
  circuit.addChild(terrain.mesh())
  var distance:Float=0
  for i in track.indices {
   let a=project(track[i]),b=project(track[(i+1)%track.count])
   guard simd_distance(a,b)>0.00001 else{continue}
   circuit.addChild(segment(a,b,width:theme == .tron ? 0.007:theme == .kart ? 0.014:0.010,height:0.001,color:theme.road))
   let d=simd_normalize(SIMD3(b.x-a.x,0,b.z-a.z)+SIMD3(0.000001,0,0));let side=SIMD3(-d.z,0,d.x)*(theme == .tron ? 0.005:theme == .kart ? 0.0085:0.0065)
   let alternate=Int(distance/0.018)%2==0
   let edge:UIColor=theme == .tron ? .cyan:theme == .kart ? (alternate ? .systemYellow:.systemRed):(alternate ? .white:.systemRed)
   for sign:Float in [-1,1]{circuit.addChild(segment(a+side*sign,b+side*sign,width:theme == .tron ? 0.0008:0.0025,color:edge))}
   distance += simd_distance(a,b)
  }
  if theme != .tron { addScenery(track.map(project),terrain:terrain) }
  for _ in 0..<42 {let e=ModelEntity(mesh:.generateBox(size:SIMD3(0.001,0.003,0.01)),materials:[material(.cyan)]);e.isEnabled=false;trails.append(e);root.addChild(e)}
 }
 func box(_ size:SIMD3<Float>,_ position:SIMD3<Float>,_ color:UIColor,_ name:String="")->ModelEntity {
  let e=ModelEntity(mesh:.generateBox(size:size),materials:[material(color)]);e.position=position;e.name=name;return e
 }
 func makeVehicle(highlighted: Bool = true, number: Int = 0, leader: Bool = false)->Entity {
  let vehicle=Entity()
  if theme == .grandPrix { return FormulaVehicle.make(number: number) }
  if theme == .tron && !highlighted {
   vehicle.addChild(box(SIMD3(0.010,0.003,0.005),SIMD3(0,0.002,0),.white,"livery"));return vehicle
  }
  if theme == .tron {
   let name=leader ? "CycleFirestar":"CycleSpringSociety"
   if let cycle=ModelLibrary.model(name,size:0.023) {
    cycle.name=name;vehicle.addChild(cycle)
   } else { vehicle.addChild(box([0.010,0.003,0.005],[0,0.002,0],.white,"livery")) }
  } else if theme == .kart,let kart=ModelLibrary.model("Kart",size:0.023) {
   kart.name="kart-body";kart.orientation=simd_quatf(angle:.pi/2,axis:SIMD3(0,1,0));vehicle.addChild(kart)
   // Preserve the borrowed character; use a team-color nose stripe rather than a second helmet.
   vehicle.addChild(box(SIMD3(0.006,0.0008,0.006),SIMD3(0.007,0.0055,0),.white,"livery"))
   let shadow=ModelEntity(mesh:.generateCylinder(height:0.0001,radius:0.01),materials:[material(UIColor(white:0.08,alpha:1))]);shadow.scale=SIMD3(1.2,1,0.65);shadow.position.y=0.0002;vehicle.addChild(shadow)
  } else {
   let kart=theme == .kart
   vehicle.addChild(box(SIMD3(kart ? 0.013:0.021,0.003,kart ? 0.008:0.005),SIMD3(0,0.003,0),.white,"livery"))
   vehicle.addChild(box(SIMD3(0.005,0.003,kart ? 0.006:0.004),SIMD3(-0.001,0.005,0),.black))
   for x:Float in [-1,1]{for z:Float in [-1,1]{
    let wheel=ModelEntity(mesh:.generateCylinder(height:0.0025,radius:kart ? 0.003:0.0032),materials:[material(UIColor(white:0.045,alpha:1))]);wheel.orientation=simd_quatf(angle:.pi/2,axis:SIMD3(1,0,0));wheel.position=SIMD3(x*(kart ? 0.0045:0.007),0.003,z*(kart ? 0.005:0.0045));vehicle.addChild(wheel)
   }}
   let helmet=ModelEntity(mesh:.generateSphere(radius:kart ? 0.0028:0.0018),materials:[material(.white)]);helmet.position=SIMD3(-0.002,kart ? 0.008:0.006,0);vehicle.addChild(helmet)
   vehicle.addChild(box(SIMD3(0.001,kart ? 0.0015:0.001,0.010),SIMD3(kart ? 0.007:0.011,0.002,0),kart ? .white:.black))
   if !kart {vehicle.addChild(box(SIMD3(0.003,0.001,0.011),SIMD3(-0.010,0.006,0),.white,"livery"))}
  }
  return vehicle
 }
 func addScenery(_ track:[SIMD3<Float>],terrain:Diorama) {
  let minX=(track.map(\.x).min() ?? 0)-0.015,maxX=(track.map(\.x).max() ?? 0)+0.015
  let minZ=(track.map(\.z).min() ?? 0)-0.015,maxZ=(track.map(\.z).max() ?? 0)+0.015
  for i in 0..<100 {
   let x=minX+Float((i*37)%101)/100*(maxX-minX),z=minZ+Float((i*61+13)%103)/102*(maxZ-minZ)
   guard terrain.contains(x,z),terrain.nearest(x,z).0>0.026 else{continue}
   if let c=terrain.featureCenter,simd_length(SIMD2(x-c.x,z-c.z))<0.042 {continue}
   let p=SIMD3(x,terrain.height(x,z),z)
   if theme == .kart {
    let choices:[String]=terrain.world == .desert ? ["Rock","Rock","Palm","Bush"]:terrain.world == .alpine ? ["Pine","Pine","Rock","Bush"]:terrain.world == .tropical || terrain.world == .harbor ? ["Palm","Tree","Bush","Rock"]:["Tree","Pine","Bush","Mushroom","Rock"]
    let name=choices[i%choices.count],size:Float=name == "Tree" || name == "Pine" || name == "Palm" ? 0.038:0.014
    if let prop=ModelLibrary.model(name,size:size){prop.position=p;prop.orientation=simd_quatf(angle:Float(i)*0.7,axis:SIMD3(0,1,0));circuit.addChild(prop)}
    if i%13==0 {addBillboard(at:p)}
    if i%23==0 {
     let stand=Entity();stand.position=p
     for tier in 0..<3 {stand.addChild(box(SIMD3(0.024,0.003,0.005),SIMD3(0,Float(tier)*0.003,Float(tier)*0.005),.systemOrange))}
     for seat in 0..<5 {let head=ModelEntity(mesh:.generateSphere(radius:0.0015),materials:[material(seat%2==0 ? .systemPurple:.systemYellow)]);head.position=SIMD3(Float(seat-2)*0.004,0.010,0.010);stand.addChild(head)}
     circuit.addChild(stand)
    }
   } else if i%12==0 {
    let stand=Entity();stand.position=p
    for tier in 0..<3 {stand.addChild(box(SIMD3(0.025,0.003,0.006),SIMD3(0,Float(tier)*0.003,Float(tier)*0.005),tier%2==0 ? .lightGray:.systemBlue))};circuit.addChild(stand)
   }
  }
  if theme == .kart {addWorldDetails(terrain)}
  guard track.count>2 else{return}
  let p=track[0],next=track[1];let gate=Entity();gate.position=p
  gate.orientation=simd_quatf(angle:atan2(-(next.z-p.z),next.x-p.x),axis:SIMD3(0,1,0))
  for sign:Float in [-1,1]{gate.addChild(box(SIMD3(0.002,0.026,0.002),SIMD3(0,0.012,sign*0.012),.white))}
  for j in 0..<10 {gate.addChild(box(SIMD3(0.002,0.004,0.0024),SIMD3(0,0.025,Float(j)*0.0024-0.0108),j%2==0 ? .black:.white))}
  circuit.addChild(gate)
  if theme == .kart,terrain.world == .harbor {
   let tunnel=Entity();tunnel.position=p;tunnel.orientation=gate.orientation
   for sign:Float in [-1,1] {tunnel.addChild(box(SIMD3(0.028,0.021,0.003),SIMD3(0,0.009,sign*0.013),.systemIndigo))}
   tunnel.addChild(box(SIMD3(0.028,0.005,0.029),SIMD3(0,0.022,0),.systemIndigo));circuit.addChild(tunnel)
  }
 }
 func addBillboard(at p:SIMD3<Float>){
  let sign=Entity();sign.position=p
  sign.addChild(box(SIMD3(0.0015,0.012,0.0015),SIMD3(-0.008,0.006,0),.white))
  sign.addChild(box(SIMD3(0.0015,0.012,0.0015),SIMD3(0.008,0.006,0),.white))
  sign.addChild(box(SIMD3(0.023,0.009,0.002),SIMD3(0,0.014,0),.systemOrange))
  for i in 0..<3 {let arrow=box(SIMD3(0.0015,0.005,0.001),SIMD3(Float(i-1)*0.006,0.014,0.0015),.white);arrow.orientation=simd_quatf(angle:-0.6,axis:SIMD3(0,0,1));sign.addChild(arrow)}
  circuit.addChild(sign)
 }
 func addWorldDetails(_ terrain:Diorama){
  guard let center=terrain.featureCenter else{return}
  if terrain.world != .desert {
   let water=ModelEntity(mesh:.generateCylinder(height:0.0006,radius:0.028),materials:[SimpleMaterial(color:UIColor(red:0.12,green:0.67,blue:0.88,alpha:1),roughness:0.35,isMetallic:false)]);water.position=center+SIMD3(0,-0.002,0);circuit.addChild(water)
   for i in 0..<4 {circuit.addChild(box(SIMD3(0.009,0.0002,0.0007),center+SIMD3(Float(i%2)*0.012-0.009,-0.0015,Float(i)*0.008-0.012),UIColor(white:0.9,alpha:1)))}
   if terrain.world == .harbor {
    let boat=box(SIMD3(0.014,0.003,0.006),center+SIMD3(0,0,0),.white);circuit.addChild(boat)
    circuit.addChild(box(SIMD3(0.005,0.005,0.005),center+SIMD3(-0.002,0.003,0),.systemBlue))
    for i in 0..<5 {let p=center+SIMD3(Float(i-2)*0.011,0,0.037);let h:Float=0.017+Float(i%3)*0.004
     circuit.addChild(box(SIMD3(0.009,h,0.008),SIMD3(p.x,terrain.height(p.x,p.z)+h/2,p.z),i%2==0 ? .systemPink:.systemYellow))}
   }
  } else {
   if let rock=ModelLibrary.model("Rock",size:0.045){rock.position=center;circuit.addChild(rock)}
  }
 }
 func colorVehicle(_ entity:Entity,_ color:UIColor){
  if entity.name.hasPrefix("Cycle") {return}
  if let model=entity as? ModelEntity {
   if model.name == "livery" {model.model?.materials=[material(color)]}
   else if model.name.replacingOccurrences(of:"_",with:"").replacingOccurrences(of:"-",with:"").lowercased()=="kartoobi" {
    model.model?.materials=model.model?.materials.map { original in
     if var pbr=original as? PhysicallyBasedMaterial {pbr.baseColor.tint=color;return pbr}
     if var simple=original as? SimpleMaterial {simple.color.tint=color;return simple}
     return original
    } ?? []
   }
  }
  for child in entity.children {colorVehicle(child,color)}
 }
 func update(_ race:RaceStore){
  #if DEBUG
  if ProcessInfo.processInfo.arguments.contains("--preview-cycles") {
   if root.children.isEmpty {
    for (i,name) in ["CycleFirestar","CycleSpringSociety"].enumerated() {
     if let cycle=ModelLibrary.model(name,size:0.023) {
      cycle.position=[Float(i)*0.032-0.016,0,0];root.addChild(cycle)
     }
    }
    root.orientation=simd_quatf(angle:0.5,axis:[1,0,0])
   }
   return
  }
  if ProcessInfo.processInfo.arguments.contains("--preview-badges") {
   if root.children.isEmpty {
    for (i,number) in [3,44,81].enumerated() {
     let car=FormulaVehicle.make(number:number)
     colorVehicle(car,[UIColor.systemBlue,.systemRed,.systemOrange][i])
     car.position=[Float(i-1)*0.035,0,0]
     car.orientation=simd_quatf(angle:Float(i-1)*0.8,axis:[0,1,0])
     root.addChild(car)
    }
    root.orientation=simd_quatf(angle:0.5,axis:[1,0,0])
   }
   return
  }
  #endif
  if lastTrack != race.track || theme != race.theme || lastTitle != race.title {build(race.track,theme:race.theme,title:race.title)}
  root.orientation=simd_quatf(angle:Float(race.rotation),axis:SIMD3(0,1,0));root.scale=SIMD3(repeating:Float(race.tableScale))
  let now=Date();let dt=Float(max(0.001,now.timeIntervalSince(lastFrameTime)));lastFrameTime=now
  for c in race.cars {
   let highlighted = race.highlights.contains(c.id)
   let role = c.id == race.leader ? "leader" : highlighted ? "tracked" : "block"
   if theme == .tron, let existing=bikes[c.id], vehicleRoles[c.id] != role {
    existing.removeFromParent();bikes.removeValue(forKey:c.id);lastColors.removeValue(forKey:c.id)
   }
   let bike:Entity
   if let existing=bikes[c.id]{bike=existing}else{
    bike=makeVehicle(highlighted:highlighted,number:c.id,leader:c.id == race.leader);vehicleRoles[c.id]=role;bike.name="driver-\(c.id)"
    bikes[c.id]=bike;root.addChild(bike)
   }
   bike.scale=SIMD3(repeating:Float(race.vehicleScale))
   bike.isEnabled=c.point != nil
   if let p=c.point {bike.position=project(p);let old=previousHeading[c.id] ?? c.heading;let delta=atan2(sin(c.heading-old),cos(c.heading-old));let lean:Float=theme == .kart && (race.playing || (race.mode == "Live" && !race.tvPaused)) ? max(-0.16,min(0.16,-delta/dt*0.035)):0;previousHeading[c.id]=c.heading;bike.orientation=simd_quatf(angle:c.heading,axis:SIMD3(0,1,0))*simd_quatf(angle:lean,axis:SIMD3(1,0,0));let color:UIColor=theme == .grandPrix ? UIColor(Color(hex:c.color)) : c.id==race.leader ? .yellow:c.id==race.selected ? .cyan:UIColor(Color(hex:c.color));if lastColors[c.id] != color {colorVehicle(bike,color);lastColors[c.id]=color}}
  }
  for (n,bike)in bikes where !race.cars.contains(where:{$0.id==n}){bike.isEnabled=false}
  trails.forEach{$0.isEnabled=false};var index=0
  for n in race.highlights.sorted(){let pts=race.trail(n).map(project);guard pts.count>1 else{continue};for i in 1..<pts.count where index<trails.count {let e=trails[index];index+=1;let a=pts[i-1],b=pts[i];let distance=simd_distance(a,b);guard distance>0.00001 && distance<0.15 else{continue};e.isEnabled=true;e.position=(a+b)/2+SIMD3(0,0.002,0);e.scale=SIMD3(theme == .tron ? 1:2,theme == .tron ? 1:0.2,distance/0.01);e.orientation=simd_quatf(from:SIMD3(0,0,1),to:simd_normalize(b-a));e.model?.materials=[material(n==race.leader ? .yellow:.cyan)]}}
 }
}
struct TrackVolume {
 let center: SIMD3<Float>
 let size: SIMD3<Float>
 init(track: [SIMD3<Float>], rotation: Double, scale: Double) {
  guard track.count > 2 else { center = .zero; size = SIMD3(0.63,0.14,0.63); return }
  let lo = track.reduce(track[0]) { simd_min($0,$1) }
  let hi = track.reduce(track[0]) { simd_max($0,$1) }
  let factor: Float = 0.55 / max(1,max(hi.x-lo.x,hi.y-lo.y))
  let q = simd_quatf(angle: Float(rotation), axis: SIMD3(0,1,0))
  let points = track.map { q.act(SIMD3(($0.x-(hi.x+lo.x)/2)*factor,($0.z-lo.z)*factor+0.006,-($0.y-(hi.y+lo.y)/2)*factor)) }
  var lower = points.reduce(points[0]) { simd_min($0,$1) }
  var upper = points.reduce(points[0]) { simd_max($0,$1) }
  // Reserve space for the island skirt, scenery, vehicles and trails.
  lower -= SIMD3(0.045,0.04,0.045)
  upper += SIMD3(0.045,0.07,0.045)
  center = (upper+lower)/2 * Float(scale)
  size = (upper-lower) * Float(scale)
 }
}
struct TabletopView:View {
 @EnvironmentObject var race:RaceStore
 @StateObject private var scene=TableScene()
 @State private var volumeFrame: Rect3D = .zero
 @PhysicalMetric(from: .meters) private var pointsPerMeter: CGFloat = 1
 var body:some View {
  GeometryReader3D { geometry in
   RealityView {content in
    content.add(scene.coordinateRoot)
    scene.update(race)
    fit(content, geometry: geometry)
   } update:{content in
    scene.update(race)
    fit(content, geometry: geometry)
   }
   .onGeometryChange3D(for: Rect3D.self) { $0.frame(in: .local) } action: { volumeFrame = $0 }
   .frame(width: geometry.size.width, height: geometry.size.height)
   .frame(depth: geometry.size.depth)
  }
  .frame(minWidth: 0.25*pointsPerMeter, maxWidth: 6.5*pointsPerMeter,
         minHeight: 0.12*pointsPerMeter, maxHeight: 3*pointsPerMeter)
  .frame(minDepth: 0.25*pointsPerMeter, maxDepth: 6.5*pointsPerMeter)
 }
 private func fit(_ content: RealityViewContent, geometry: GeometryProxy3D) {
  let frame = volumeFrame.size.width > 0 ? volumeFrame : geometry.frame(in: .local)
  // Convert directly to the parent we position in; scene origin and the
  // RealityView root origin need not coincide in a volumetric window.
  let available = content.convert(frame, from: .local, to: scene.coordinateRoot)
  scene.fit(in: available)

 }
}
