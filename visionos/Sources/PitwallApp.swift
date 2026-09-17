import SwiftUI

enum Panel: String, CaseIterable, Codable, Identifiable {
    case map = "2D Map", timing = "Leaderboard", tires = "Tires & Stints", telemetry = "Driver", control = "Race Control", weather = "Weather", laps = "Lap Times", pits = "Pit Stops", radio = "Team Radio", overtakes = "Overtakes"
    var id: String { rawValue }
}
@main struct PitwallApp: App {
    @StateObject private var race = RaceStore()
    var body: some Scene {
        Window("Pitwall", id: "controls") { ControlView().environmentObject(race).task { race.start() } }
            .defaultSize(width: 620, height: 680)
        Window("Tabletop", id: "tabletop-resizable") { TabletopView().environmentObject(race)
            .ornament(attachmentAnchor: .scene(.bottom)) { TabletopControls().environmentObject(race).padding(12).glassBackgroundEffect() }
        }
            .windowStyle(.volumetric).windowResizability(.contentSize)
            .defaultSize(width: 0.7, height: 0.25, depth: 0.7, in: .meters)
        WindowGroup("Race Panel", for: Panel.self) { $panel in
            PanelView(panel: panel ?? .timing).environmentObject(race)
        }.defaultSize(width: 600, height: 520)
    }
}
