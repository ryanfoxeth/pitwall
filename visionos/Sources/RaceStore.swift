import SwiftUI
import Combine
import Security

typealias Row = [String: Any]
func num(_ value: Any?) -> Double { (value as? NSNumber)?.doubleValue ?? Double(value as? String ?? "") ?? 0 }
func text(_ value: Any?) -> String { guard let v = value, !(v is NSNull) else { return "—" }; if let n = v as? Double { return String(format: "%.3f", n) }; return String(describing: v) }
func stamp(_ value: Any?) -> Double? {
    guard let s = value as? String else { return nil }
    let f = ISO8601DateFormatter(); f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    return (f.date(from: s) ?? ISO8601DateFormatter().date(from: s))?.timeIntervalSince1970
}
struct Car: Identifiable {
    var id: Int; var name: String; var team: String; var color: String
    var point: SIMD3<Float>?; var heading: Float = 0; var position: Int?; var lap: Int = 0
    var gap = "—"; var interval = "—"; var compound = "—"; var age = 0; var status = ""; var lastLap = "—"
    var speed = "—"; var gear = "—"; var throttle = "—"; var brake = "—"
}
@MainActor final class RaceStore: ObservableObject {
    @Published var serverURL = UserDefaults.standard.string(forKey:"server-url") ?? "" { didSet { UserDefaults.standard.set(serverURL,forKey:"server-url") } }
    @Published var theme = RaceTheme(rawValue: UserDefaults.standard.string(forKey:"race-theme") ?? "tron") ?? .tron {
        didSet { UserDefaults.standard.set(theme.rawValue,forKey:"race-theme") }
    }
    @Published var vehicleScale: Double = min(4,max(0.1,(UserDefaults.standard.object(forKey:"vehicle-scale") as? Double) ?? 1)) {
        didSet { UserDefaults.standard.set(vehicleScale,forKey:"vehicle-scale") }
    }
    @Published var automaticallySelectCircuit = true
    @Published var selectedCircuitID = CircuitCatalog.automatic()?.id ?? ""
    @Published var cars: [Car] = []; @Published var track: [SIMD3<Float>] = []
    @Published var selected = 1; @Published var playing = false; @Published var time: Double = 0
    @Published var speed: Double = 1; @Published var duration: Double = 7200
    @Published var mode = "Live"; @Published var status = "Configure your Pitwall server"
    @Published var title = "Pitwall"; @Published var error: String?
    @Published var feeds: [String: [Row]] = [:]; @Published var weather: Row = [:]; @Published var messages: [Row] = []
    @Published var rotation: Double = 0; @Published var tableScale: Double = 1
    var locations: [Int: [[Double]]] = [:]; var drivers: [Row] = []; var replayFeeds: [String:[Row]] = [:]
    var liveRegistration=LiveCircuitRegistration()
    var liveFrames: [(Double, [Car])] = []; var liveTrail: [Int: [(Double,SIMD3<Float>)]] = [:]
    var telemetryCache: [String:[Row]] = [:]
    struct LiveSnapshot {
        var date: Double; var cars: [Car]; var weather: Row; var messages: [Row]; var feeds: [String:[Row]]; var status: String
    }
    @Published var tvDelay: Double = 0
    @Published var tvPaused = false
    @Published var syncStatus = ""
    var liveBuffer: [LiveSnapshot] = []
    var displayTime: Double = 0
    var displayedSnapshot: Double = -1
    var runner: Task<Void,Never>?
    func start() { if runner == nil { runner = Task { await run() } } }
    var telemetryBusy = false
    var lastTimingSecond = -1
    @Published var replayNotice=""
    var replayCoverage=0.0
    var replaySession = ""; var replayStart: Double = 0; var replayTitle = "Local replay"
    var replayTrack: [SIMD3<Float>] = []; var lastLive: Double = 0; var running = false
    var leader: Int? { cars.filter { $0.position == 1 }.first?.id }
    var highlights: Set<Int> { Set([leader, selected].compactMap { $0 }) }
    var currentLap: Int { cars.map(\.lap).max() ?? 0 }
    var key: String { get { Keychain.read() } set { Keychain.save(newValue) } }
    init() {
     loadReplay()
     if !ProcessInfo.processInfo.arguments.contains("--preview-tabletop") {mode="Tracks";switchMode()}
    }
    func loadReplay() {
        let saved=UserDefaults.standard.string(forKey:"replay-file").flatMap{FileManager.default.urls(for:.documentDirectory,in:.userDomainMask).first?.appendingPathComponent("Replays/"+$0+".json")}
        let alternate=UserDefaults.standard.string(forKey:"replay-file")=="9979" ? Bundle.main.url(forResource:"Monaco2025Replay",withExtension:"json"):nil
        let url = [saved,alternate,Bundle.main.url(forResource:"MonacoReplay",withExtension:"json"),Bundle.main.url(forResource:"MadridReplay",withExtension:"json")].compactMap{$0}.first{FileManager.default.fileExists(atPath:$0.path)}
        do {guard let url else{throw CocoaError(.fileNoSuchFile)};try loadReplay(data:Data(contentsOf:url))}
        catch {status="Select a session to download its replay"}
    }
    func loadReplay(data:Data) throws {
        guard let root=try JSONSerialization.jsonObject(with:data) as? Row,
              let samples=root["locations"] as? [String:[[Double]]],samples.values.contains(where:{$0.contains(where:{$0.count==4 && $0.allSatisfy(\.isFinite) && ($0[1] != 0 || $0[2] != 0 || $0[3] != 0)})}),num(root["duration"])>0,num(root["duration"]).isFinite,
              let outline=root["track"] as? [[Double]],outline.count>3,outline.allSatisfy({$0.count==3 && $0.allSatisfy(\.isFinite)}) else{throw URLError(.cannotParseResponse)}
            let session=root["session"] as? Row ?? [:]
            replaySession=String(Int(num(session["session_key"])));replayStart=stamp(session["date_start"]) ?? 0
            replayTitle="\(text(session["location"])) · \(text(session["session_name"])) · \(Int(num(session["year"])))"
            title=replayTitle
            locations=[:];telemetryCache=[:];lastTimingSecond = -1
            duration = num(root["duration"]); replayFeeds = root["feeds"] as? [String:[Row]] ?? [:]; drivers = replayFeeds["drivers"] ?? []
            for (n, p) in root["locations"] as? [String:[[Double]]] ?? [:] { if let id = Int(n) { locations[id] = p.filter{$0.count==4 && $0.allSatisfy(\.isFinite) && ($0[1] != 0 || $0[2] != 0 || $0[3] != 0)}.sorted{$0[0]<$1[0]} } }
            replayTrack = (root["track"] as? [[Double]] ?? []).map { SIMD3(Float($0[0]),Float($0[1]),Float($0[2])) }
            for topic in replayFeeds.keys { replayFeeds[topic]?.sort { num($0["date_seconds"] ?? $0["date_start_seconds"]) < num($1["date_seconds"] ?? $1["date_start_seconds"]) } };selected = drivers.first(where: { $0["name_acronym"] as? String == "VER" }).map { Int(num($0["driver_number"])) } ?? Int(num(drivers.first?["driver_number"]))
            track = replayTrack; time = max(0,(replayFeeds["laps"] ?? []).filter{num($0["lap_number"]) == 2}.compactMap{$0["date_start_seconds"] as? Double}.min() ?? 120); updateReplay(); status = "HISTORICAL REPLAY · recorded positions"
        if let registration=root["registration"] as? Row,let id=registration["circuit_id"] as? String,let c=CircuitCatalog.all.first(where:{$0.id==id}) {replayTrack=c.track;track=c.track}
        if !locations.values.contains(where:{$0.contains(where:{abs($0[0]-time)<5})}) {time=locations.values.compactMap{$0.first?.first}.min() ?? 0}
        UserDefaults.standard.set(replaySession,forKey:"replay-file")
        let covered=locations.values.map{samples in zip(samples,samples.dropFirst()).reduce(0.0){$0+min(1.1,max(0,$1.1[0]-$1.0[0]))}}.max() ?? 0
        replayCoverage = min(1,max(0,covered/max(1,duration)))
        replayNotice = replayCoverage<0.9 ? "Partial position coverage: \(Int(replayCoverage*100))%. Cars disappear during missing observations; timing continues." : "Recorded positions · all panels share the replay clock."
        if let missing=root["missingFeeds"] as? [String],!missing.isEmpty {replayNotice += " Missing feeds: \(missing.joined(separator:", "))."}
    }
    func sample(_ n: Int, at t: Double) -> (SIMD3<Float>?, Float) {
        RaceMath.sample(locations[n] ?? [], at: t)
    }

    func visible(_ rows: [Row], at t: Double) -> [Row] { rows.filter { ($0["date_seconds"] as? Double ?? $0["date_start_seconds"] as? Double ?? .infinity) <= t } }
    func updateReplay() {
        guard mode == "Replay" else { return }
        if lastTimingSecond == Int(time) && !cars.isEmpty { cars=cars.map { c in var c=c;let (p,h)=sample(c.id,at:time);c.point=p;c.heading=h;return c };applyTelemetry();return };lastTimingSecond=Int(time)
        let pos = visible(replayFeeds["position"] ?? [],at:time); let gaps = visible(replayFeeds["intervals"] ?? [],at:time)
        let allLaps = replayFeeds["laps"] ?? []
        cars = drivers.map { d in
            let n = Int(num(d["driver_number"])); let (p,h) = sample(n,at:time)
            let laps = allLaps.filter { Int(num($0["driver_number"])) == n && num($0["date_start_seconds"]) <= time }
            let lap = laps.max { num($0["lap_number"]) < num($1["lap_number"]) }; let lapN = Int(num(lap?["lap_number"]))
            let done = laps.filter { $0["lap_duration"] is NSNumber && num($0["date_start_seconds"])+num($0["lap_duration"]) <= time }.max { num($0["lap_number"]) < num($1["lap_number"]) }
            let stint = (replayFeeds["stints"] ?? []).filter { Int(num($0["driver_number"])) == n && num($0["lap_start"]) <= Double(lapN) }.max { num($0["stint_number"]) < num($1["stint_number"]) }
            let position = pos.last { Int(num($0["driver_number"])) == n }; let gap = gaps.last { Int(num($0["driver_number"])) == n }
            var car = Car(id:n,name:d["name_acronym"] as? String ?? "\(n)",team:d["team_name"] as? String ?? "",color:d["team_colour"] as? String ?? "42D9FF",point:p,heading:h,position:position.map { Int(num($0["position"])) },lap:lapN)
            car.gap=text(gap?["gap_to_leader"]);car.interval=text(gap?["interval"]);car.compound=stint?["compound"] as? String ?? "—";car.age=max(0,Int(num(stint?["tyre_age_at_start"]))+lapN-Int(num(stint?["lap_start"])));car.lastLap=text(done?["lap_duration"])
            // Historical OUT is only shown after classification publication, never inferred from missing positions.
            if time >= duration-1, let result=(replayFeeds["session_result"] ?? []).first(where:{Int(num($0["driver_number"]))==n}) { car.status=(result["dnf"] as? Bool == true) ? "OUT" : "" }
            return car
        }.sorted { ($0.position ?? 999,$0.id) < ($1.position ?? 999,$1.id) }
        applyTelemetry()
        messages=Array(visible(replayFeeds["race_control"] ?? [],at:time).suffix(30).reversed());weather=visible(replayFeeds["weather"] ?? [],at:time).last ?? [:]
        feeds=replayFeeds.mapValues { visible($0,at:time) }
        feeds["laps"]=allLaps.filter { $0["lap_duration"] is NSNumber && num($0["date_start_seconds"])+num($0["lap_duration"]) <= time }
    }
    func trail(_ n: Int) -> [SIMD3<Float>] {
        guard mode == "Live" || mode == "Replay", highlights.contains(n) else { return [] }
        if mode == "Live" { return liveBuffer.filter { $0.date > displayTime-5 && $0.date <= displayTime }.compactMap { $0.cars.first(where:{$0.id==n})?.point } }
        return stride(from:max(0,time-4),through:time,by:0.2).compactMap { sample(n,at:$0).0 }
    }
    func switchMode() { liveRegistration=LiveCircuitRegistration();lastTimingSecond = -1;playing=false; cars=[]; liveFrames=[];liveTrail=[:];liveBuffer=[];displayedSnapshot = -1;tvPaused=false;error=nil; if mode=="Replay" { track=replayTrack;title=replayTitle;updateReplay();status="HISTORICAL REPLAY" } else if mode=="Tracks" {if automaticallySelectCircuit,let c=CircuitCatalog.automatic() {selectedCircuitID=c.id};feeds=[:];weather=[:];messages=[];if let c=CircuitCatalog.all.first(where:{$0.id==selectedCircuitID}) {track=c.track;title=c.circuit+" · "+c.location;status="TRACK PREVIEW · "+c.elevation} else {track=[];status="Select a circuit"}} else { track=[];status="Connecting to your server…";lastLive=0 } }
    func fetchLive() async {
        guard !key.isEmpty else { status="Enter a scoped Pitwall device key to connect";return }
        do {
            guard let endpoint=URL(string:serverURL),endpoint.scheme == "https",endpoint.host != nil,endpoint.user == nil,endpoint.password == nil else { status="Enter the full HTTPS device endpoint";return }
            var req=URLRequest(url:endpoint);req.setValue("Bearer \(key)",forHTTPHeaderField:"Authorization");req.timeoutInterval=20
            let (data,res)=try await URLSession.shared.data(for:req);guard (res as? HTTPURLResponse)?.statusCode==200 else { throw URLError(.userAuthenticationRequired) }
            guard mode=="Live" else{return};let r=try JSONSerialization.jsonObject(with:data) as! Row
            let session=r["session"] as? Row ?? [:];let newTitle="\(text(session["location"])) · \(text(session["session_name"]))"
            if title != newTitle {liveFrames=[];liveTrail=[:];liveBuffer=[];displayedSnapshot = -1;tvPaused=false};title=newTitle
            let sourceTrack=(r["track"] as? [Row] ?? []).map { SIMD3(Float(num($0["x"])),Float(num($0["y"])),Float(num($0["z"]))) }
            if liveRegistration.configure(provider:Int(num(session["circuit_key"])),outline:sourceTrack) {liveFrames=[];liveTrail=[:];liveBuffer=[];displayedSnapshot = -1}
            track=liveRegistration.track ?? sourceTrack
            let next=(r["cars"] as? [Row] ?? []).map { d -> Car in
                let n=Int(num(d["number"]));let p=d["location"] as? Row;let tele=d["telemetry"] as? Row ?? [:]
                let recent=p.flatMap{stamp($0["date"])}.map{Date().timeIntervalSince1970-$0<15} ?? false
                var c=Car(id:n,name:d["name"] as? String ?? "\(n)",team:d["team"] as? String ?? "",color:d["color"] as? String ?? "42D9FF",point:recent ? liveRegistration.point(SIMD3(Float(num(p?["x"])),Float(num(p?["y"])),0)) : nil,position:(d["position"] as? Int),lap:Int(num(d["lap"])))
                c.gap=text(d["gap"]);c.interval=text(d["interval"]);c.compound=text(d["compound"]);c.age=Int(num(d["tire_age"]));c.status=d["status"] as? String ?? "";c.speed=text(tele["speed"]);c.gear=text(tele["n_gear"]);c.throttle=text(tele["throttle"]);c.brake=text(tele["brake"]);c.lastLap=text(d["last_lap"]);return c
            }
            let now=Date().timeIntervalSince1970;liveFrames.append((now,next));liveFrames=Array(liveFrames.suffix(2));lastLive=now
            for c in next {if let p=c.point {liveTrail[c.id,default:[]].append((now,p));liveTrail[c.id]=Array(liveTrail[c.id,default:[]].suffix(6))}}
            let newFeeds=(r["feeds"] as? [String:Row] ?? [:]).filter{["laps","pit","team_radio","overtakes"].contains($0.key)}.mapValues{Array(($0["data"] as? [Row] ?? []).suffix(80))}
            let l=r["live"] as? Row ?? [:]
            let sourceStatus=r["mode"] as? String == "historical" ? "NO LIVE SESSION · historical snapshot" : l["session_stale"] as? Bool == false ? "LIVE" : "WAITING FOR FRESH POSITIONS"
            liveBuffer.append(LiveSnapshot(date:now,cars:next,weather:r["weather"] as? Row ?? [:],messages:r["messages"] as? [Row] ?? [],feeds:newFeeds,status:sourceStatus))
            liveBuffer.removeAll{$0.date < now-360}
            error=nil
        } catch {guard mode=="Live" else{return};self.error="Live connection unavailable. Retrying.";status="OFFLINE · positions held"}
    }
    func telemetryID() -> String { "\(selected)-\(Int(time/30))" }
    func applyTelemetry() {
        guard mode=="Replay",let rows=telemetryCache[telemetryID()],let r=rows.last(where: { num($0["t"]) <= time }), time-num(r["t"])<5, let i=cars.firstIndex(where:{$0.id==selected}) else{return}
        cars[i].speed=text(r["speed"]);cars[i].gear=text(r["n_gear"]);cars[i].throttle=text(r["throttle"]);cars[i].brake=text(r["brake"])
    }
    func loadTelemetry() async {
        guard mode=="Replay",!telemetryBusy,telemetryCache[telemetryID()]==nil else{return}
        telemetryBusy=true;defer{telemetryBusy=false};let sessionID=replaySession;let id=telemetryID();let driver=selected;let block=floor(time/30)*30
        let start=replayStart
        guard start>0,!replaySession.isEmpty else{return}
        let formatter=ISO8601DateFormatter();var url=URLComponents(string:"https://api.openf1.org/v1/car_data")!
        url.queryItems=[URLQueryItem(name:"session_key",value:replaySession),URLQueryItem(name:"driver_number",value:String(driver)),URLQueryItem(name:"date>",value:formatter.string(from:Date(timeIntervalSince1970:start+block-1))),URLQueryItem(name:"date<",value:formatter.string(from:Date(timeIntervalSince1970:start+block+30)))]
        do {let (data,response)=try await URLSession.shared.data(from:url.url!);guard (response as? HTTPURLResponse)?.statusCode==200,sessionID==replaySession else{return};var rows=try JSONSerialization.jsonObject(with:data) as? [Row] ?? [];for i in rows.indices{rows[i]["t"]=(stamp(rows[i]["date"]) ?? start)-start};rows.sort{num($0["t"])<num($1["t"])};telemetryCache[id]=rows;if telemetryCache.count>30{telemetryCache=Dictionary(uniqueKeysWithValues:Array(telemetryCache.prefix(15)))};applyTelemetry()}catch{}
    }
    func toggleTVPause() {
        if tvPaused { tvDelay=min(300,max(0,Date().timeIntervalSince1970-displayTime-2)) }
        tvPaused.toggle()
    }
    func presentLive(at now: Double) {
        guard let first=liveBuffer.first else { return }
        if !tvPaused { displayTime=RaceMath.liveTime(now:now,delay:tvDelay,oldest:first.date) }
        syncStatus=tvPaused ? "TV SYNC · PAUSED" : now-tvDelay-2 < first.date ? "TV SYNC · building delay buffer" : String(format:"TV SYNC · %.0fs added delay",tvDelay)
        guard !tvPaused || displayedSnapshot < 0 else { return }
        guard let index=RaceMath.latestIndex(liveBuffer.map(\.date),at:displayTime) else{return}
        let current=liveBuffer[index]
        cars=current.cars
        if index+1 < liveBuffer.count {
            let next=liveBuffer[index+1];let interval=next.date-current.date
            if interval > 0 && interval < 6 {
                let fraction=Float(min(1,max(0,(displayTime-current.date)/interval)))
                cars=cars.map { value in var c=value
                    if let p=c.point,let q=next.cars.first(where:{$0.id==c.id})?.point {c.point=p+(q-p)*fraction;c.heading=atan2(q.y-p.y,q.x-p.x)}
                    return c
                }
            }
        }
        if displayedSnapshot != current.date {
            weather=current.weather;messages=current.messages;feeds=current.feeds;displayedSnapshot=current.date
        }
        status=current.status + " · " + syncStatus
        if now-lastLive>15 {status += " · CONNECTION STALE"}
    }
    func run() async {
        guard !running else{return};running=true
        let polling=Task {while !Task.isCancelled {if mode=="Live" {await fetchLive()}else if mode=="Tracks" {refreshAutomaticCircuit()}else{await loadTelemetry()};try? await Task.sleep(for:.seconds(2))}}
        defer{running=false;polling.cancel()};var prev=Date()
        while !Task.isCancelled {
            let now=Date();let dt=now.timeIntervalSince(prev);prev=now
            if mode=="Replay" {if playing {time=min(duration,time+min(dt,0.1)*speed);updateReplay();if time>=duration{playing=false}}}
            else if mode=="Live" {
                presentLive(at: now.timeIntervalSince1970)
            }
            try? await Task.sleep(for:.milliseconds(33))
        }
    }
}
enum Keychain {
 static let query:[String:Any]=[kSecClass as String:kSecClassGenericPassword,kSecAttrService as String:"PitwallVision",kSecAttrAccount as String:"device-key"]
 static func read()->String{var q=query;q[kSecReturnData as String]=true;var result:CFTypeRef?;guard SecItemCopyMatching(q as CFDictionary,&result)==errSecSuccess,let d=result as? Data else{return ""};return String(data:d,encoding:.utf8) ?? ""}
 static func save(_ s:String){SecItemDelete(query as CFDictionary);guard !s.isEmpty else{return};var q=query;q[kSecValueData as String]=Data(s.utf8);q[kSecAttrAccessible as String]=kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly;SecItemAdd(q as CFDictionary,nil)}
}
