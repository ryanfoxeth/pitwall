import Foundation
import RealityKit

/// Assets share the catalog projection. Provider positions must be registered first.
@MainActor enum CircuitScenery {
 static let circuits=["baku","sepang","marina_bay","americas","rodriguez","interlagos","vegas","losail","yas_marina"]
 nonisolated static let providerIDs=[144:"baku",12:"sepang",61:"marina_bay",9:"americas",65:"rodriguez",14:"interlagos",152:"vegas",150:"losail",70:"yas_marina",22:"monaco"]
 private static var cached:[String:Entity]=[:]
 private static var recent:[String]=[]
 static func model(for track:[SIMD3<Float>],theme:RaceTheme)->Entity? {
  guard let c=CircuitCatalog.all.first(where:{circuits.contains($0.id) && $0.track==track}) else{return nil}
  let style=theme == .miniature ? "grandPrix":theme.rawValue
  let name="Scenery_\(c.id)_\(style)"
  if cached[name]==nil {
   guard let url=Bundle.main.url(forResource:name,withExtension:"usdz"),let entity=try? Entity.load(contentsOf:url) else{return nil}
   cached[name]=entity
  }
  recent.removeAll{$0==name};recent.append(name)
  while recent.count>2 {cached.removeValue(forKey:recent.removeFirst())}
  let model=cached[name]?.clone(recursive:true);model?.name="CircuitScenery_\(c.id)";return model
 }
}
