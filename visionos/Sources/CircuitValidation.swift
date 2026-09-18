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
   expect(bounds.extents.x>0.1 && bounds.extents.z>0.1 && bounds.extents.x<0.91 && bounds.extents.z<0.91)
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
    // Match the production fit target; disabled trail placeholders are outside it.
    let actual=scene.circuit.visualBounds(relativeTo:world)
    let ratios=actual.extents/size
    if !ratios.x.isFinite || !ratios.y.isFinite || !ratios.z.isFinite || !actual.center.x.isFinite || !actual.center.y.isFinite || !actual.center.z.isFinite || max(ratios.x,max(ratios.y,ratios.z))>0.961 || abs(scene.presentation.scale.x*scene.authoredUnitsPerMeter-TabletopScale.metersToDisplay(size))>0.000001 || simd_length(actual.center)>=0.002 {
     failures.append("\(id): size \(size), bounds \(actual.extents), center \(actual.center)")
    }
    checks+=1
   }
  }
 }
 let url=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("volume-validation.json")
 try! JSONSerialization.data(withJSONObject:["passed":failures.isEmpty,"failures":failures,"fitChecks":checks]).write(to:url)
}
@MainActor func validateTrackIsolation(_ race: RaceStore) {
 let savedLocations = race.locations
 let savedTime = race.time
 let savedSelected = race.selected
 // Exercise a real bundled replay when available; otherwise use a small fixture.
 if race.locations.isEmpty {
  race.selected = 1; race.time = 4
  race.locations[1] = (0...4).map { [Double($0), 10000 + Double($0)*10, 8000, 6000] }
 }
 let replaySamples = stride(from: max(0,race.time-4), through: race.time, by: 0.2).compactMap {race.sample(race.selected,at:$0).0}
 var results: [[String:Any]] = []
 var passed = !replaySamples.isEmpty
 for id in ["marina_bay","monaco","baku"] {
  guard let c = CircuitCatalog.all.first(where: {$0.id == id}) else {passed = false;continue}
  race.previewCircuit(c)
  let scene = TableScene();scene.update(race)
  let target = BoundingBox(min: SIMD3(-0.442647,-0.158088,0),max: SIMD3(0.442647,0.158088,0.885294))
  scene.fit(in:target)
  let scale = scene.presentation.scale
  let position = scene.presentation.position
  // A bad telemetry object must not alter the circuit framing.
  let stray = ModelEntity(mesh: .generateBox(size: 0.01));stray.position = SIMD3(3,3,3);scene.root.addChild(stray)
  scene.fit(in:target)
  let noTrail = race.trail(race.selected).isEmpty && scene.trails.allSatisfy {!$0.isEnabled}
  let stable = simd_length(scene.presentation.scale-scale)<0.00001 && simd_length(scene.presentation.position-position)<0.00001
  passed = passed && noTrail && stable
  results.append(["circuit":id,"noPreviewTrails":noTrail,"outlierCannotShrinkCircuit":stable,"scale":scale.x,"legacyReplayProjectedPoints":replaySamples.prefix(2).map {p in let q=scene.project(p);return [q.x,q.y,q.z]}])
 }
 race.locations=savedLocations;race.time=savedTime;race.selected=savedSelected
 let url=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("track-isolation.json")
 try? JSONSerialization.data(withJSONObject:["passed":passed,"replaySamples":replaySamples.count,"checks":results],options:.prettyPrinted).write(to:url)
}
@MainActor func validateMonaco(_ race: RaceStore) {
 guard let c=CircuitCatalog.all.first(where:{$0.id == "monaco"}) else {return}
 let originalTheme=race.theme
 race.previewCircuit(c);race.theme = .grandPrix
 let scene=TableScene();scene.update(race)
 var failures:[String]=[]
 if scene.circuit.findEntity(named:"MonacoGrandPrixGeography") == nil {failures.append("Bundled Monaco environment failed to load")}
 var checks=0
 for environmentTheme in [RaceTheme.grandPrix, .tron, .kart] {
 race.theme=environmentTheme
 for angle in [0.0,Double.pi/4,Double.pi/2,Double.pi] {
  race.rotation=angle
  for size:SIMD3<Float> in [SIMD3(0.7,0.25,0.7),SIMD3(3,1,3),SIMD3(5.5,2,5.5)] {
   scene.update(race)
   let target=BoundingBox(min:-size/2,max:size/2);scene.fit(in:target)
   let actual=scene.circuit.visualBounds(relativeTo:scene.coordinateRoot)
   let ratios=actual.extents/size
   if simd_length(actual.center)>0.002 || max(ratios.x,max(ratios.y,ratios.z))>0.961 || abs(scene.presentation.scale.x*scene.authoredUnitsPerMeter-TabletopScale.metersToDisplay(size))>0.000001 {failures.append("Monaco failed fit at angle \(angle), size \(size)")}
   checks+=1
  }
 }
 }
 for theme in RaceTheme.allCases {
  race.theme=theme;scene.update(race)
  let hasKart=scene.circuit.findEntity(named:"MonacoKartGeography") != nil
  if hasKart != (theme == .kart) {failures.append("Incorrect Kart environment in \(theme)")}
  let hasTron=scene.circuit.findEntity(named:"MonacoTronGeography") != nil
  if hasTron != (theme == .tron) {failures.append("Incorrect Tron environment in \(theme)")}
  let hasEnvironment=scene.circuit.findEntity(named:"MonacoGrandPrixGeography") != nil
  if hasEnvironment != (theme == .grandPrix) {failures.append("Incorrect environment in \(theme)")}
 }
 race.rotation=0;race.theme = originalTheme;scene.update(race)
 let bounds=scene.circuit.visualBounds(relativeTo:scene.root)
 if max(bounds.extents.x,bounds.extents.z)>0.70 {failures.append("Environment exceeds compact authored footprint: \(bounds.extents)")}
 let url=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("monaco-validation.json")
 try? JSONSerialization.data(withJSONObject:["passed":failures.isEmpty,"failures":failures,"rotationSizeChecks":checks,"themeSwitchChecks":4,"authoredBounds":[bounds.extents.x,bounds.extents.y,bounds.extents.z]]).write(to:url)
}
#endif
