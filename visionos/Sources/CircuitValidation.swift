#if DEBUG
import Foundation
import RealityKit
@MainActor func validateCircuits(_ race:RaceStore) async {
 var results:[[String:Any]]=[]
 let savedTheme=race.theme
 let catalog=CircuitCatalog.all
 precondition(catalog.count==23 && Set(catalog.map(\.id)).count==23)
 let date=ISO8601DateFormatter().date(from:"2026-09-17T12:00:00Z")!
 precondition(CircuitCatalog.upcoming(at:date).count==9)
 precondition(CircuitCatalog.upcoming(at:date).first?.id=="baku")
 for c in catalog {
  race.previewCircuit(c)
  // SwiftUI's source-change callback can run after selection; repeating it must preserve the chosen circuit.
  race.switchMode()
  precondition(race.track==c.track && race.cars.isEmpty && race.feeds.isEmpty)
  for theme in RaceTheme.allCases {
   let scene=TableScene();race.theme=theme;scene.update(race)
   let bounds=scene.root.visualBounds(relativeTo:nil)
   precondition(bounds.extents.x.isFinite && bounds.extents.z.isFinite)
   precondition(bounds.extents.x>0.1 && bounds.extents.z>0.1 && bounds.extents.x<0.7 && bounds.extents.z<0.7)
   precondition(scene.bikes.isEmpty)
   results.append(["id":c.id,"theme":theme.rawValue,"points":c.track.count,"bounds":[bounds.extents.x,bounds.extents.y,bounds.extents.z]])
   await Task.yield()
  }
 }
 race.theme=savedTheme;race.previewCircuit(catalog.first{$0.id=="baku"}!)
 let url=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("circuit-validation.json")
 try! JSONSerialization.data(withJSONObject:["passed":true,"circuits":23,"upcoming":9,"sceneChecks":results],options:.prettyPrinted).write(to:url)
}
#endif
