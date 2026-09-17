#if DEBUG
import Foundation
import RealityKit
@MainActor func validateCircuits(_ race:RaceStore) async {
 var results:[[String:Any]]=[]
 var failures:[String]=[]
 func expect(_ value:Bool) {if !value {failures.append("Circuit/theme validation check failed at result \(results.count)")}}
 let savedTheme=race.theme
 let catalog=CircuitCatalog.all
 expect(catalog.count==23 && Set(catalog.map(\.id)).count==23)
 let date=ISO8601DateFormatter().date(from:"2026-09-17T12:00:00Z")!
 expect(CircuitCatalog.upcoming(at:date).count==9)
 expect(CircuitCatalog.upcoming(at:date).first?.id=="baku")
 for c in catalog {
  race.previewCircuit(c)
  // SwiftUI's source-change callback can run after selection; repeating it must preserve the chosen circuit.
  race.switchMode()
  expect(race.track==c.track && race.cars.isEmpty && race.feeds.isEmpty)
  for theme in RaceTheme.allCases {
   let scene=TableScene();race.theme=theme;scene.update(race)
   let bounds=scene.root.visualBounds(relativeTo:nil)
   expect(bounds.extents.x.isFinite && bounds.extents.z.isFinite)
   expect(bounds.extents.x>0.1 && bounds.extents.z>0.1 && bounds.extents.x<0.7 && bounds.extents.z<0.7)
   expect(scene.bikes.isEmpty)
   results.append(["id":c.id,"theme":theme.rawValue,"points":c.track.count,"bounds":[bounds.extents.x,bounds.extents.y,bounds.extents.z]])
   await Task.yield()
  }
 }
 race.theme=savedTheme;race.previewCircuit(catalog.first{$0.id=="baku"}!)
 let url=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("circuit-validation.json")
 try! JSONSerialization.data(withJSONObject:["passed":failures.isEmpty,"failures":failures,"circuits":23,"upcoming":9,"sceneChecks":results],options:.prettyPrinted).write(to:url)
}
@MainActor func validateVolume(_ race:RaceStore) {
 let scene=TableScene()
 let world=Entity();world.addChild(scene.presentation)
 let identity=scene.presentation.id
 race.tabletopOpen=false
 precondition(race.requestTabletop() && !race.requestTabletop())
 race.tabletopOpen=false
 precondition(race.requestTabletop())
 race.tabletopOpen=false
 var checks=0
 var failures:[String]=[]
 for id in ["baku","monaco","spa"] {
  guard let circuit=CircuitCatalog.all.first(where:{$0.id==id}) else {preconditionFailure(id)}
  race.previewCircuit(circuit)
  scene.update(race)
  for size:SIMD3<Float> in [SIMD3(0.7,0.25,0.7),SIMD3(3,1,3),SIMD3(5.5,2,5.5)] {
   let target=BoundingBox(min: -size/2,max:size/2)
   for _ in 0..<4 {
    scene.update(race);scene.fit(in:target)
    let actual=scene.root.visualBounds(relativeTo:world)
    let ratios=actual.extents/size
    if !ratios.x.isFinite || !ratios.y.isFinite || !ratios.z.isFinite || !actual.center.x.isFinite || !actual.center.y.isFinite || !actual.center.z.isFinite || abs(max(ratios.x,max(ratios.y,ratios.z))-0.96)>=0.002 || simd_length(actual.center)>=0.002 {
     failures.append("\(id): size \(size), bounds \(actual.extents), center \(actual.center)")
    }
    checks+=1
   }
  }
 }
 let url=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("volume-validation.json")
 try! JSONSerialization.data(withJSONObject:["passed":failures.isEmpty,"failures":failures,"fitChecks":checks,"singleOpenGuard":true]).write(to:url)
}
#endif
