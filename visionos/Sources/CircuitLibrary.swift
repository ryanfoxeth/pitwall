import SwiftUI

struct SeasonCircuit: Codable, Identifiable {
 let id: String; let round: Int; let date: String; let name: String; let circuit: String
 let location: String; let country: String; let length: String; let turns: String; let direction: String
 let points: [[Float]]; let elevation: String; let source: String
 var track: [SIMD3<Float>] { points.filter{$0.count == 3 && $0.allSatisfy(\.isFinite)}.map{SIMD3($0[0],$0[1],$0[2])} }
 var raceDate: Date { ISO8601DateFormatter().date(from:date+"T23:59:59Z") ?? .distantPast }
}
enum CircuitCatalog {
 static let all: [SeasonCircuit] = {
  guard let u=Bundle.main.url(forResource:"Season2026",withExtension:"json"),let d=try? Data(contentsOf:u),let rows=try? JSONDecoder().decode([SeasonCircuit].self,from:d) else {return []}
  return rows.sorted{$0.round<$1.round}
 }()
 static func automatic(at date:Date=Date())->SeasonCircuit? {
  var calendar=Calendar(identifier:.iso8601);calendar.timeZone=TimeZone(secondsFromGMT:0)!
  if let week=calendar.dateInterval(of:.weekOfYear,for:date),let current=all.first(where:{$0.raceDate>=week.start && $0.raceDate<week.end}) {return current}
  return upcoming(at:date).first ?? all.last
 }
 static func upcoming(at date:Date=Date())->[SeasonCircuit] {all.filter{$0.raceDate>=date}}
}
extension RaceStore {
 func refreshAutomaticCircuit() {
  guard mode=="Tracks",automaticallySelectCircuit,let c=CircuitCatalog.automatic(),c.id != selectedCircuitID || track.isEmpty else{return}
  previewCircuit(c,automatic:true)
 }
 func previewCircuit(_ circuit:SeasonCircuit,automatic:Bool=false) {
  automaticallySelectCircuit=automatic
  selectedCircuitID=circuit.id;mode="Tracks";switchMode();track=circuit.track
  title=circuit.circuit+" · "+circuit.location
  status="TRACK PREVIEW · "+circuit.elevation
 }
}
struct CircuitLibraryView:View {
 @EnvironmentObject var race:RaceStore
 @Environment(\.openWindow) var openWindow
 @State private var showPast=false
 var body:some View {
  VStack(alignment:.leading,spacing:16) {
   Text("2026 track library").font(.title2.bold())
   Text("Upcoming races first · all four styles · available offline").font(.caption).foregroundStyle(.secondary)
   Toggle("Follow current race week",isOn:$race.automaticallySelectCircuit).onChange(of:race.automaticallySelectCircuit){race.refreshAutomaticCircuit()}
   Text("Automatically follows this week’s race, or the next race between weekends. Selecting a different track turns this off.").font(.caption).foregroundStyle(.secondary)
   Toggle("Include earlier races",isOn:$showPast)
   let upcoming=CircuitCatalog.automatic().map {current in [current]+CircuitCatalog.upcoming().filter{$0.id != current.id}} ?? CircuitCatalog.upcoming()
   ForEach(upcoming) {c in circuitRow(c,next:c.id==upcoming.first?.id)}
   if showPast {ForEach(CircuitCatalog.all.filter{c in !upcoming.contains(where:{$0.id==c.id})}) {c in circuitRow(c,next:false)}}
   if CircuitCatalog.all.isEmpty {Text("Track library unavailable.").foregroundStyle(.orange)}
   Text("Calendar snapshot: 17 September 2026; race dates are UTC. Reference geometry may differ from the current layout. Track previews have no cars or race telemetry; switch to Live or Replay for positioned cars.").font(.caption).foregroundStyle(.secondary)
   Link("Current F1 calendar",destination:URL(string:"https://www.formula1.com/en/racing/2026")!)
   Link("Circuit geometry and license",destination:URL(string:"https://github.com/bacinger/f1-circuits")!)
   Link("Circuit facts: F1DB · CC BY 4.0",destination:URL(string:"https://github.com/f1db/f1db")!)
  }
 }
 func circuitRow(_ c:SeasonCircuit,next:Bool)->some View {
  Button {
   race.previewCircuit(c);openWindow(id:"tabletop-resizable")
  } label: {
   VStack(alignment:.leading,spacing:6) {
    HStack {Text(next ? "NEXT RACE":"ROUND \(c.round)").font(.caption.bold()).foregroundStyle(.cyan);Spacer();Text(c.date).font(.caption).monospacedDigit()}
    Text(c.name).font(.headline)
    Text(c.circuit).font(.subheadline)
    Text("\(c.length) km · \(c.turns) turns · \(c.direction)").font(.caption).foregroundStyle(.secondary)
    Text(c.elevation).font(.caption2).foregroundStyle(.secondary)
   }.frame(maxWidth:.infinity,alignment:.leading).padding(10)
  }.buttonStyle(.bordered)
 }
}
