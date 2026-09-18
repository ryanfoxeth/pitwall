import SwiftUI

struct ControlView: View {
 @EnvironmentObject var race:RaceStore
 @Environment(\.openWindow) var openWindow
 @Environment(\.dismissWindow) var dismissWindow
 @State private var credential=""
 var body: some View {
  ScrollView { VStack(alignment:.leading,spacing:22) {
   Link(destination: URL(string: "https://tv.apple.com/us/channel/formula-1/tvs.sbd.241000")!) { Label("Watch F1 on Apple TV", systemImage: "tv") }
   Text("PITWALL / SPATIAL").font(.headline).foregroundStyle(.cyan)
   Text(race.title).font(.largeTitle.bold())
   Label(race.status,systemImage:race.mode=="Replay" ? "clock.arrow.circlepath":"antenna.radiowaves.left.and.right").font(.subheadline)
   if let e=race.error { Text(e).foregroundStyle(.orange) }
   Picker("Theme",selection:$race.theme){ForEach(RaceTheme.allCases){theme in Text(theme.title).tag(theme)}}.pickerStyle(.segmented)
   Text(race.theme.detail).font(.caption).foregroundStyle(race.theme.accent)
   TextField("https://your-server.example/api/f1/device",text:$race.serverURL).textInputAutocapitalization(.never).autocorrectionDisabled()
   Picker("Source",selection:$race.mode){Text("Historical replay").tag("Replay");Text("Live server").tag("Live");Text("Track library").tag("Tracks")}.pickerStyle(.segmented).onChange(of:race.mode){race.switchMode()}
   if race.mode=="Replay" {
    ReplayLibraryView()
    Text(race.replayNotice).font(.caption).foregroundStyle(.orange)
    if race.replayCoverage<0.9 {Button("Next recorded positions") {if let t=race.locations.values.flatMap({$0}).filter({$0[0]>race.time+5}).map({$0[0]}).min(){race.time=t;race.updateReplay()}}}
    HStack {Button(race.playing ? "Pause":"Play",systemImage:race.playing ? "pause.fill":"play.fill"){race.playing.toggle()};Picker("Speed",selection:$race.speed){ForEach([0.5,1,2,4,8],id:\.self){Text("\($0,specifier:"%g")×").tag($0)}}}
    Slider(value:$race.time,in:0...max(1,race.duration)).onChange(of:race.time){if !race.playing {race.updateReplay()}}
    HStack{Text(Duration.seconds(race.time).formatted(.time(pattern:.minuteSecond)));Spacer();Text("Lap \(race.currentLap)");Spacer();Text(Duration.seconds(race.duration).formatted(.time(pattern:.minuteSecond)))}.monospacedDigit()
    Text("Recorded race · all windows share this clock. Missing observations stay missing; no fabricated car motion.").font(.caption).foregroundStyle(.secondary)
   } else if race.mode=="Tracks" {
    CircuitLibraryView()
   } else {
    Text("Sync with TV").font(.title2.bold())
    HStack {Text("Delay");Slider(value:$race.tvDelay,in:0...300,step:1);Text("\(Int(race.tvDelay))s").monospacedDigit().frame(width:50)}
    HStack {
     Button("−1s"){race.tvDelay=max(0,race.tvDelay-1)}
     Button("+1s"){race.tvDelay=min(300,race.tvDelay+1)}
     Button(race.tvPaused ? "Resume with TV":"Pause to match TV"){race.toggleTVPause()}
     Button("Latest"){race.tvPaused=false;race.tvDelay=0}
    }
    Text(race.syncStatus).font(.caption).foregroundStyle(.cyan)
    Text("Match a lap crossing on TV, then fine-tune the delay. All panels and cycle trails share the same clock. Up to five minutes of delay builds while connected; Latest retains a two-second smoothing buffer. This is manual sync, not TV recognition.").font(.caption).foregroundStyle(.secondary)
    SecureField("Your server device key",text:$credential)
    Button("Save connection key"){race.key=credential;credential=""}
    Text("Your OpenF1 credentials remain on your server. Live tabletop height uses the backend’s 2D outline until a registered elevation model is available.").font(.caption).foregroundStyle(.secondary)
   }
   Picker("Follow driver",selection:$race.selected){ForEach(race.cars){c in Text("\(c.name) · \(c.id)").tag(c.id)}}
   Text("Only P1 and your followed driver leave a trail. If they’re the same driver, there is one trail.").font(.caption).foregroundStyle(.secondary)
   Button("Open tabletop track",systemImage:"cube.transparent"){openWindow(id:"tabletop-resizable")}.buttonStyle(.borderedProminent)
   VStack(alignment:.leading,spacing:8) {
    HStack {Text("Vehicle size");Spacer();Text("\(race.vehicleScale,specifier:"%.1f")×").monospacedDigit();Button("Reset"){race.vehicleScale=1}}
    Slider(value:$race.vehicleScale,in:0.1...4,step:0.1).accessibilityLabel("Vehicle size").accessibilityValue("\(race.vehicleScale,specifier:"%.1f") times")
    Text("Scales cars, lightcycles and blocks in every theme. Saved for next time.").font(.caption).foregroundStyle(.secondary)
   }
   HStack{Text("Rotate");Slider(value:$race.rotation,in:-Double.pi...Double.pi)}
   Text("Resize the track using the volume’s corner handles. All circuits share one real-world scale at the same volume size. Smaller circuits occupy less space. Enlarge the volume to enlarge everything.").font(.caption).foregroundStyle(.secondary)
   DisclosureGroup("Model credits") {
    Text("Monaco and remaining-season scenery: © OpenStreetMap contributors (ODbL). Original stylized landmarks. Approximate building heights and terrain; decorative docked yachts.").font(.caption)
    Link("OpenStreetMap attribution",destination:URL(string:"https://www.openstreetmap.org/copyright")!)
    Text("Optional models: Tron Light Cycle by Firestar · Lightcycle by SpringSociety. CC BY 4.0. Adapted for Pitwall: normalized size/orientation, removed separate trail and converted to USDZ.").font(.caption)
    Link("Firestar — Tron Light Cycle",destination:URL(string:"https://sketchfab.com/3d-models/tron-light-cycle-083076c8a3644b088ce7f1e107a12ca6")!)
    Link("SpringSociety — Lightcycle",destination:URL(string:"https://sketchfab.com/3d-models/lightcycle-aaebbf5d4c504dbbb8963f3dd91b37c1")!)
    Link("Creative Commons Attribution 4.0",destination:URL(string:"https://creativecommons.org/licenses/by/4.0/")!)
   }
   Text("Floating panels").font(.title2.bold())
   ForEach(Panel.allCases){p in HStack{Button(p.rawValue){openWindow(value:p)};Spacer();Button("Close",systemImage:"xmark"){dismissWindow(value:p)}.labelStyle(.iconOnly)}}
   Text("Move the volume above your table using its window handle. It is a movable tabletop display, not a detected physical-table anchor.").font(.caption).foregroundStyle(.secondary)
  }.padding(28) }.task {
   #if DEBUG
   if ProcessInfo.processInfo.arguments.contains("--validate-windows") {
    var observations: [[String: Any]] = []
    func record(_ stage: String) {
     let scenes = UIApplication.shared.connectedScenes.map { $0.session.configuration.name ?? "unnamed" }
     observations.append(["stage": stage, "scenes": scenes, "count": scenes.count])
     let url = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("window-validation.json")
     try? JSONSerialization.data(withJSONObject: observations, options: .prettyPrinted).write(to: url)
    }
    if let circuit = CircuitCatalog.all.first(where: {$0.id == "monaco"}) { race.previewCircuit(circuit) }
    openWindow(id: "tabletop-resizable")
    try? await Task.sleep(for: .seconds(3)); record("opened")
    openWindow(id: "tabletop-resizable"); openWindow(id: "controls"); openWindow(id: "controls")
    try? await Task.sleep(for: .seconds(3)); record("repeated open")
    dismissWindow(id: "tabletop-resizable")
    try? await Task.sleep(for: .seconds(3)); record("closed")
    openWindow(id: "tabletop-resizable")
    try? await Task.sleep(for: .seconds(3)); record("reopened")
   }
   if let i=ProcessInfo.processInfo.arguments.firstIndex(of:"--theme"),ProcessInfo.processInfo.arguments.count>i+1,let theme=RaceTheme(rawValue:ProcessInfo.processInfo.arguments[i+1]) {race.theme=theme}
   if ProcessInfo.processInfo.arguments.contains("--replay-2025"),let url=Bundle.main.url(forResource:"Monaco2025Replay",withExtension:"json"),let data=try? Data(contentsOf:url){try? race.loadReplay(data:data)}
   if ProcessInfo.processInfo.arguments.contains("--validate-season-scenery") {await validateSeasonScenery(race)}
   if ProcessInfo.processInfo.arguments.contains("--validate-replay") {validateReplay(race)}
   if ProcessInfo.processInfo.arguments.contains("--validate-track-isolation") {validateTrackIsolation(race)}
   if ProcessInfo.processInfo.arguments.contains("--validate-monaco") {validateMonaco(race)}
   if ProcessInfo.processInfo.arguments.contains("--validate-volume") {validateVolume(race)}
   if ProcessInfo.processInfo.arguments.contains("--validate-circuits") {await validateCircuits(race)}
   if let i=ProcessInfo.processInfo.arguments.firstIndex(of:"--preview-circuit"),ProcessInfo.processInfo.arguments.count>i+1,let c=CircuitCatalog.all.first(where:{$0.id==ProcessInfo.processInfo.arguments[i+1]}) {race.previewCircuit(c);openWindow(id:"tabletop-resizable")}
   #endif
   if ProcessInfo.processInfo.arguments.contains("--preview-tabletop") {
    race.mode="Replay";race.switchMode()
    race.time=race.replaySession=="11299" ? 200:1800;race.updateReplay();race.playing = !ProcessInfo.processInfo.arguments.contains("--paused-preview")
    #if DEBUG
    if ProcessInfo.processInfo.arguments.contains("--validate-themes") {validateThemes(race)}
    #endif
    openWindow(id:"tabletop-resizable")
    if !ProcessInfo.processInfo.arguments.contains("--scene-only") {openWindow(value:Panel.timing)}
   }
  }
 }
}
struct PanelView:View {
 let panel:Panel
 @EnvironmentObject var race:RaceStore
 var body:some View {
  VStack(alignment:.leading,spacing:16){
   HStack{Text(panel.rawValue).font(.title.bold());Spacer();ControlsButton();Text(race.mode.uppercased()).font(.caption).foregroundStyle(.cyan)}
   Text(race.title).font(.caption).foregroundStyle(.secondary)
   if panel == .map { MapView() }
   else {ScrollView {VStack(alignment:.leading,spacing:12){content}}}
   Text(race.status).font(.caption2).foregroundStyle(.secondary)
  }.padding(24)
 }
 @ViewBuilder var content:some View {
  switch panel {
  case .timing:
   ForEach(race.cars){c in Button{race.selected=c.id}label:{HStack{Text(c.position.map(String.init) ?? "—").frame(width:30);Circle().fill(Color(hex:c.color)).frame(width:9,height:9);Text(c.name).bold();Text(c.status).foregroundStyle(.orange);Spacer();Text(c.interval).monospacedDigit();Text(c.compound.prefix(1)).foregroundStyle(.cyan)}}.buttonStyle(.plain);Divider()}
  case .tires:
   ForEach(race.cars){c in HStack{Text(c.name).bold().frame(width:60);Text(c.compound);Spacer();Text("\(c.age) laps").monospacedDigit();Text("L\(c.lap)").foregroundStyle(.secondary)}}
  case .telemetry:
   if let c=race.cars.first(where:{$0.id==race.selected}) {Text("\(c.name) · \(c.team)").font(.title2);metric("Position",c.position.map(String.init) ?? "—");metric("Gap to leader",c.gap);metric("Last completed lap",c.lastLap);metric("Speed",c.speed);metric("Gear",c.gear);metric("Throttle",c.throttle);metric("Brake",c.brake);if race.mode=="Replay"{Text("Historical telemetry loads for the followed driver when online; unavailable readings remain blank.").font(.caption).foregroundStyle(.secondary)}}
  case .weather:
   ForEach(["air_temperature","track_temperature","humidity","rainfall","wind_speed","wind_direction"],id:\.self){k in metric(k.replacingOccurrences(of:"_",with:" ").capitalized,text(race.weather[k]))}
  case .control:
   if race.messages.isEmpty {Text("No race-control messages at this time.")}
   ForEach(Array(race.messages.enumerated()),id:\.offset){_,r in Text(text(r["message"]));Divider()}
  case .laps: rows("laps",keys:["driver_number","lap_number","lap_duration"])
  case .pits: rows("pit",keys:["driver_number","lap_number","pit_duration"])
  case .radio: rows("team_radio",keys:["driver_number","date"])
  case .overtakes: rows("overtakes",keys:["overtaking_driver_number","overtaken_driver_number","position"])
  case .map:EmptyView()
  }
 }
 func metric(_ title:String,_ value:String)->some View{HStack{Text(title).foregroundStyle(.secondary);Spacer();Text(value).monospacedDigit()}}
 @ViewBuilder func rows(_ topic:String,keys:[String]) -> some View {
  let records=Array((race.feeds[topic] ?? []).suffix(80).reversed())
  if records.isEmpty {Text("No published \(panel.rawValue.lowercased()) data at this time.").foregroundStyle(.secondary)}
  ForEach(Array(records.enumerated()),id:\.offset){_,r in HStack{ForEach(keys,id:\.self){k in VStack(alignment:.leading){Text(k.replacingOccurrences(of:"_",with:" ")).font(.caption2).foregroundStyle(.secondary);Text(text(r[k])).font(.body.monospacedDigit())}};if let s=r["recording_url"] as? String,let u=URL(string:s){Link("Listen",destination:u)}};Divider()}
 }
}
struct MapView:View {
 @EnvironmentObject var race:RaceStore
 var body:some View {GeometryReader{g in
  let points=race.track;let xs=points.map(\.x),ys=points.map(\.y);let minX=xs.min() ?? 0,maxX=xs.max() ?? 1,minY=ys.min() ?? 0,maxY=ys.max() ?? 1
  let scale=min((g.size.width-36)/CGFloat(max(1,maxX-minX)),(g.size.height-36)/CGFloat(max(1,maxY-minY)))
  let project:(SIMD3<Float>)->CGPoint={p in CGPoint(x:g.size.width/2+CGFloat(p.x-(minX+maxX)/2)*scale,y:g.size.height/2-CGFloat(p.y-(minY+maxY)/2)*scale)}
  Canvas{ctx,_ in if let first=points.first {var path=Path();path.move(to:project(first));for p in points.dropFirst(){path.addLine(to:project(p))};path.closeSubpath();ctx.stroke(path,with:.color(race.theme.accent.opacity(0.35)),lineWidth:9);ctx.stroke(path,with:.color(race.theme.accent),lineWidth:2)}
   for c in race.cars {if let p=c.point{let pos=project(p);let radius:CGFloat=race.highlights.contains(c.id) ? 7:4;ctx.fill(Path(ellipseIn:CGRect(x:pos.x-radius,y:pos.y-radius,width:radius*2,height:radius*2)),with:.color(c.id==race.leader ? .yellow:c.id==race.selected ? .cyan:Color(hex:c.color)));if race.highlights.contains(c.id){ctx.draw(Text(c.name).font(.caption.bold()),at:CGPoint(x:pos.x,y:pos.y-18))}}}
  }
 }}
}
extension Color {init(hex:String){let n=UInt64(hex.replacingOccurrences(of:"#",with:""),radix:16) ?? 0x42D9FF;self.init(red:Double((n>>16)&255)/255,green:Double((n>>8)&255)/255,blue:Double(n&255)/255)}}

struct ControlsButton: View {
 @Environment(\.openWindow) private var openWindow
 var body: some View {
  Button("Controls", systemImage: "slider.horizontal.3") { openWindow(id: "controls") }
   .accessibilityHint("Reopen Pitwall settings and playback controls")
 }
}

/// These controls stay attached to the volume and never open another window.
struct TabletopControls: View {
 @EnvironmentObject private var race: RaceStore
 var body: some View {
  HStack(spacing: 12) {
   Button { rotate(-1) } label: { Image(systemName: "rotate.left") }
    .accessibilityLabel("Rotate track left 15 degrees")
   Button { rotate(1) } label: { Label("Rotate", systemImage: "rotate.right") }
    .accessibilityLabel("Rotate track right 15 degrees")
   ControlsButton()
  }
 }
 private func rotate(_ direction: Double) {
  let angle = race.rotation + direction * .pi / 12
  race.rotation = atan2(sin(angle), cos(angle))
 }
}
