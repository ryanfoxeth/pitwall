#if DEBUG
import Foundation
import RealityKit
@MainActor func validateSeasonScenery(_ race:RaceStore) async {
 var failures:[String]=[];var checks=0;var results:[Row]=[]
 for id in CircuitCatalog.all.map(\.id) {
  guard let c=CircuitCatalog.all.first(where:{$0.id==id}) else{failures.append("Missing catalog \(id)");continue}
  for theme in RaceTheme.allCases {
   race.previewCircuit(c);race.theme=theme
   let scene=TableScene();scene.update(race)
   let loaded=scene.circuit.findEntity(named:"CircuitScenery_\(id)") != nil
   if CircuitScenery.circuits.contains(id) && !loaded {failures.append("Missing \(id) \(theme.rawValue)")}
   for angle in [0.0,Double.pi/2,Double.pi*1.2] {
    race.rotation=angle;scene.update(race)
   for width:Float in [0.7,2.0] {
    let available=BoundingBox(min:SIMD3(-width/2,-width/5,-width/2),max:SIMD3(width/2,width/5,width/2));scene.fit(in:available)
    let bounds=scene.circuit.visualBounds(relativeTo:scene.coordinateRoot)
    let scaleMatches=abs(scene.presentation.scale.x*scene.authoredUnitsPerMeter-TabletopScale.metersToDisplay(available.extents))<0.000001
    let good=scaleMatches && (0..<3).allSatisfy{bounds.min[$0]>=available.min[$0] - 0.002 && bounds.max[$0]<=available.max[$0] + 0.002 && bounds.extents[$0].isFinite}
    if !good {failures.append("Out of volume \(id) \(theme.rawValue) \(width)")}
    checks+=1
   }
   }
   results.append(["circuit":id,"theme":theme.rawValue,"loaded":loaded])
   await Task.yield()
  }
 }
 race.rotation=0
 let report:Row=["passed":failures.isEmpty,"failures":failures,"fitChecks":checks,"scenes":results]
 let path=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("season-scenery-validation.json")
 try? JSONSerialization.data(withJSONObject:report,options:.prettyPrinted).write(to:path)
}
#endif
