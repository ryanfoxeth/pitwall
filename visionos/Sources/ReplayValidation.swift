#if DEBUG
import Foundation
import RealityKit
@MainActor func validateReplay(_ race:RaceStore) {
 var failures:[String]=[]
 let t=race.replaySession=="11299" ? 300.0:1800.0
 race.mode="Replay";race.time=t;race.switchMode()
 let first=Dictionary(uniqueKeysWithValues:race.cars.compactMap{c in c.point.map{(c.id,$0)}})
 race.time=t+2;race.updateReplay()
 let moved=race.cars.filter{c in guard let p=c.point,let old=first[c.id] else{return false};return simd_distance(p,old)>0.1}.count
 if moved<5 {failures.append("Too few cars changed recorded positions")}
 if race.cars.filter({$0.position != nil}).count<5 {failures.append("Missing timing positions")}
 if race.cars.filter({$0.compound != "—"}).count<5 {failures.append("Missing tires")}
 let theme=race.theme;var environments=0
 for style in [RaceTheme.grandPrix,.tron,.kart] {
  race.theme=style;let scene=TableScene();scene.update(race)
  let expected=style == .grandPrix ? "MonacoGrandPrixGeography":style == .tron ? "MonacoTronGeography":"MonacoKartGeography"
  if scene.circuit.findEntity(named:expected) != nil {environments+=1}else{failures.append("No registered scenery for \(style)")}
  scene.fit(in:BoundingBox(min:SIMD3(-0.35,-0.125,-0.35),max:SIMD3(0.35,0.125,0.35)))
 }
 race.theme=theme;race.time=t;race.updateReplay()
 let report:Row=["passed":failures.isEmpty,"failures":failures,"session":race.replaySession,"movingCars":moved,"sceneryThemes":environments,"positionCoverage":race.replayCoverage,"cars":race.cars.count,"lap":race.currentLap]
 let url=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("replay-validation.json")
 try? JSONSerialization.data(withJSONObject:report).write(to:url)
}
#endif
