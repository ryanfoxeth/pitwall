#if DEBUG
import Foundation
@MainActor func validateThemes(_ race: RaceStore) {
    let original = race.theme
    let time = race.time, driver = race.selected, delay = race.tvDelay, playing = race.playing
    let positions = race.cars.map(\.point), order = race.cars.map(\.id), highlights = race.highlights
    let scene = TableScene()
    var counts: [String:Int] = [:]
    for theme in [RaceTheme.tron,.kart,.miniature,.grandPrix,.tron] {
        race.theme = theme
        scene.update(race)
        precondition(race.time == time && race.selected == driver && race.tvDelay == delay && race.playing == playing)
        precondition(race.cars.map(\.point) == positions && race.cars.map(\.id) == order && race.highlights == highlights)
        precondition(scene.theme == theme && scene.bikes.count == race.cars.count && scene.trails.count == 42)
        counts[theme.rawValue] = scene.root.children.count
        let terrain=Diorama(race.track.map(scene.project),world:.park,theme:theme)
        for p in race.track.prefix(20).map(scene.project) {precondition(abs(terrain.height(p.x,p.z)-(p.y-0.001))<0.0001)}
        let vehicle = scene.bikes.values.first!
        if theme == .tron {
            for car in race.cars {
                let model=scene.bikes[car.id]!
                if car.id == race.leader, ModelLibrary.model("CycleFirestar",size:1) != nil {precondition(model.findEntity(named:"CycleFirestar") != nil)}
                else if race.highlights.contains(car.id), ModelLibrary.model("CycleSpringSociety",size:1) != nil {precondition(model.findEntity(named:"CycleSpringSociety") != nil)}
                else {precondition(model.children.count == 1 && model.findEntity(named:"livery") != nil)}
            }
        } else if theme == .grandPrix { for car in scene.bikes.values {
            for name in ["number-nose","number-left","number-right"] {
                let plate=car.findEntity(named:name)!
                precondition(plate.findEntity(named:"driver-number") != nil)
            }
        } }
        else { precondition(vehicle.children.count == (theme == .kart ? 3 : 9)) }
        if theme == .kart {precondition(vehicle.findEntity(named:"kart-body") != nil)}
        let bounds=scene.root.visualBounds(relativeTo:nil)
        precondition(bounds.extents.x<0.64 && bounds.extents.z<0.64,"Compact tabletop footprint")
    }
    if ModelLibrary.model("CycleFirestar",size:1) != nil,ModelLibrary.model("CycleSpringSociety",size:1) != nil,let leader=race.leader,let other=race.cars.first(where:{$0.id != leader})?.id {
        race.selected=leader;scene.update(race)
        precondition(race.highlights.count == 1)
        precondition(scene.bikes[leader]!.findEntity(named:"CycleFirestar") != nil)
        race.selected=other;scene.update(race)
        precondition(scene.bikes[other]!.findEntity(named:"CycleSpringSociety") != nil)
        race.selected=leader;scene.update(race)
        precondition(scene.bikes[other]!.findEntity(named:"CycleSpringSociety") == nil)
    }
    race.selected=driver
    race.theme = original
    var modelBounds:[String:[Float]]=[:]
    for name in ["Kart","Tree","Pine","Palm","Bush","Mushroom","Rock","CycleFirestar","CycleSpringSociety"] {
        guard let asset=ModelLibrary.model(name,size:1) else {continue}
        let ext=asset.visualBounds(relativeTo:nil).extents
        modelBounds[name]=[ext.x,ext.y,ext.z]
    }
    let result: [String:Any] = ["passed":true,"modelBounds":modelBounds,"checks":["Tron → Kart → Miniature → Grand Prix → Tron","Playback, driver, delay, position and ordering preserved","All driver entities recreated","Distinct vehicle geometry","Bounded trail pool","Imported kart model loaded","All theme footprints under 64 cm","Terrain meets recorded road elevation"],"sceneRootEntities":counts]
    let url = FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("theme-validation.json")
    try! JSONSerialization.data(withJSONObject:result,options:.prettyPrinted).write(to:url)
}
#endif
