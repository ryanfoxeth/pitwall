import SwiftUI
import CryptoKit

struct ReplaySession:Identifiable,Sendable {
 let id:Int;let meeting:Int;let title:String;let name:String;let start:Double;let end:Double;let circuitKey:Int
 init?(_ r:Row) {
  guard let start=stamp(r["date_start"]),let end=stamp(r["date_end"]),end<Date().timeIntervalSince1970,r["is_cancelled"] as? Bool != true,["Race","Sprint","Qualifying","Sprint Qualifying","Practice 1","Practice 2","Practice 3"].contains(text(r["session_name"])) else{return nil}
  id=Int(num(r["session_key"]));meeting=Int(num(r["meeting_key"]));name=text(r["session_name"]);title="\(text(r["location"])) · \(name)";self.start=start;self.end=end;circuitKey=Int(num(r["circuit_key"]))
 }
}
actor ReplayDownloads {
 static let shared=ReplayDownloads()
 let folder=FileManager.default.urls(for:.cachesDirectory,in:.userDomainMask)[0].appendingPathComponent("OpenF1",isDirectory:true)
 let archives=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("Replays",isDirectory:true)
 func path(_ id:Int)->URL {archives.appendingPathComponent("\(id).json")}
 func cached(_ id:Int)->Bool {FileManager.default.fileExists(atPath:path(id).path)}
 func fetch(_ topic:String,_ query:[String:String],cached:Bool=true) async throws->[Row] {
  try FileManager.default.createDirectory(at:folder,withIntermediateDirectories:true)
  var u=URLComponents(string:"https://api.openf1.org/v1/"+topic)!
  u.queryItems=query.sorted{$0.key<$1.key}.map{URLQueryItem(name:$0.key,value:$0.value)}
  let key=SHA256.hash(data:Data(u.url!.absoluteString.utf8)).map{String(format:"%02x",$0)}.joined()
  let file=folder.appendingPathComponent(key+".json")
  if cached,let data=try? Data(contentsOf:file),let rows=try? JSONSerialization.jsonObject(with:data) as? [Row] {return rows}
  var last:Error=URLError(.badServerResponse)
  for attempt in 0..<5 {
   try Task.checkCancellation()
   do {
    var request=URLRequest(url:u.url!);request.timeoutInterval=90
    let (data,response)=try await URLSession.shared.data(for:request)
    let code=(response as? HTTPURLResponse)?.statusCode ?? 0
    if code==404 {return []}
    guard code==200 else {throw NSError(domain:"OpenF1",code:code,userInfo:[NSLocalizedDescriptionKey:"OpenF1 returned HTTP \(code)"])}
    guard let rows=try JSONSerialization.jsonObject(with:data) as? [Row] else{throw URLError(.cannotParseResponse)}
    try data.write(to:file,options:.atomic);try await Task.sleep(for:.milliseconds(400));return rows
   } catch {if error is CancellationError {throw error};last=error;try await Task.sleep(for:.seconds(attempt==0 ? 2:10))}
  }
  throw last
 }
 func sessions() async throws->[ReplaySession] {
  try await fetch("sessions",["year":"2026"],cached:false).compactMap(ReplaySession.init).sorted{$0.start>$1.start}
 }
 func archive(_ s:ReplaySession,progress:@escaping @Sendable (String) async->Void) async throws->Data {
  if let data=try? Data(contentsOf:path(s.id)){return data}
  let key=["session_key":String(s.id)]
  guard let session=try await fetch("sessions",key).first else{throw URLError(.resourceUnavailable)}
  var feeds:[String:[Row]]=[:];var missing:[String]=[]
  for topic in ["drivers","laps","stints","position","intervals","race_control","weather","pit","session_result","team_radio","overtakes"] {
   await progress("Downloading \(s.title): \(topic)")
   do {feeds[topic]=try await fetch(topic,key)} catch {
    if topic=="drivers" || topic=="laps" || topic=="position" {throw error}
    missing.append(topic);feeds[topic]=[]
   }
  }
  let finish=(feeds["race_control"] ?? []).filter{text($0["message"])=="SESSION FINISHED"}.compactMap{stamp($0["date"])}.max()
  let lastLap=(feeds["laps"] ?? []).filter{num($0["lap_duration"])>0}.compactMap{r -> Double? in guard let start=stamp(r["date_start"]) else{return nil};return start+num(r["lap_duration"])}.max() ?? s.end
  // Scheduled date_end is not the actual end after red flags or delays.
  let downloadEnd=finish.map{max($0,lastLap)+15} ?? max(s.end,lastLap+15)
  var locations:[String:[[Double]]]=[:];let formatter=ISO8601DateFormatter();formatter.formatOptions=[.withInternetDateTime,.withFractionalSeconds]
  for sec in stride(from:0.0,to:downloadEnd-s.start,by:300) {
   await progress("Downloading \(s.title): positions \(Int(100*sec/(downloadEnd-s.start)))%")
   var query=key;query["date>"]=formatter.string(from:Date(timeIntervalSince1970:s.start+sec-0.001));query["date<"]=formatter.string(from:Date(timeIntervalSince1970:min(downloadEnd,s.start+sec+300)))
   let rows=try await fetch("location",query)
   for r in rows {
    guard let date=stamp(r["date"]),num(r["x"]) != 0 || num(r["y"]) != 0 || num(r["z"]) != 0 else{continue};let t=date-s.start,n=String(Int(num(r["driver_number"])))
    locations[n,default:[]].append([t,num(r["x"]),num(r["y"]),num(r["z"])])
   }
  }
  for n in Array(locations.keys) {
   var previous:Int?;locations[n]=locations[n]!.sorted{$0[0]<$1[0]}.filter{p in let bucket=Int(p[0]);if previous==bucket{return false};previous=bucket;return true}
  }
  guard locations.values.contains(where:{$0.count>30}) else{throw NSError(domain:"Replay",code:1,userInfo:[NSLocalizedDescriptionKey:"No recorded car positions are available for this session."])}
  for topic in Array(feeds.keys) {
   feeds[topic]=feeds[topic]!.map {original in var r=original;for k in ["date","date_start","date_end"] {if let t=stamp(r[k]){r[k+"_seconds"]=t-s.start}};return r}
  }
  let laps=(feeds["laps"] ?? []).filter{num($0["lap_number"])>1 && num($0["lap_duration"])>40 && num($0["lap_duration"])<250 && ($0["is_pit_out_lap"] as? Bool != true)}.sorted{num($0["lap_duration"])<num($1["lap_duration"])}
  var track:[[Double]]=[]
  for lap in laps {let start=num(lap["date_start_seconds"]),end=start+num(lap["lap_duration"]);let samples=(locations[String(Int(num(lap["driver_number"])))] ?? []).filter{$0[0]>=start && $0[0]<=end};if samples.count>35 {track=samples.map{Array($0[1...3])};break}}
  guard track.count>35 else{throw NSError(domain:"Replay",code:2,userInfo:[NSLocalizedDescriptionKey:"No complete recorded lap is available to build this session’s track."])}
  var root:Row=["session":session,"duration":downloadEnd-s.start,"locations":locations,"track":track,"feeds":feeds,"missingFeeds":missing,"provenance":"User-downloaded OpenF1 observations sampled at 1 Hz. Missing positions are not fabricated."]
  if s.circuitKey==22,let circuit=CircuitCatalog.all.first(where:{$0.id=="monaco"}) {await progress("Aligning Monaco race to the detailed scenery…");_ = ReplayRegistration.register(&root,circuit:circuit)}
  let data=try JSONSerialization.data(withJSONObject:root)
  try FileManager.default.createDirectory(at:archives,withIntermediateDirectories:true);try data.write(to:path(s.id),options:.atomic)
  return data
 }
}

struct ReplayLibraryView:View {
 @EnvironmentObject var race:RaceStore
 @Environment(\.openWindow) var openWindow
 @State private var sessions:[ReplaySession]=[]
 @State private var cached:Set<Int>=[]
 @State private var selectedID=0
 @State private var message=""
 @State private var busy=false
 @State private var operation:Task<Void,Never>?
 var body:some View {
  VStack(alignment:.leading,spacing:10) {
   Text("2026 session replays").font(.title2.bold())
   Picker("Session",selection:$selectedID) {
    Text("Choose a session").tag(0)
    ForEach(sessions){s in Text("\(Date(timeIntervalSince1970:s.start).formatted(date:.abbreviated,time:.omitted)) · \(s.title)\(cached.contains(s.id) ? " ✓":"")").tag(s.id)}
   }.disabled(busy)
   HStack {
    Button(cached.contains(selectedID) ? "Play saved replay":"Download & play",systemImage:"play.circle") {startDownload(all:false)}.disabled(busy || selectedID==0)
    Button("Download all \(sessions.count)"){startDownload(all:true)}.disabled(busy || sessions.isEmpty)
    if busy {Button("Cancel"){operation?.cancel()}}
   }
   if let url=Bundle.main.url(forResource:"Monaco2025Replay",withExtension:"json") {
    Button("Play Monaco 2025 · alternate archive") {do{try race.loadReplay(data:Data(contentsOf:url));race.mode="Replay";race.switchMode();race.playing=true;openWindow(id:"tabletop-resizable")}catch{message=error.localizedDescription}}.disabled(busy)
   }
   if busy {ProgressView()}
   Text(message).font(.caption).foregroundStyle(.secondary)
   Text("Completed practices, qualifying, sprints and Grands Prix. Downloads are saved on this device; keep Pitwall open during a season download. Coverage depends on OpenF1. All panels follow the replay clock.").font(.caption)
  }.task {do {sessions=try await ReplayDownloads.shared.sessions();for s in sessions {if await ReplayDownloads.shared.cached(s.id){cached.insert(s.id)}};selectedID=sessions.first(where:{$0.circuitKey==22 && $0.name=="Race"})?.id ?? sessions.first?.id ?? 0;message="\(sessions.count) completed sessions · \(cached.count) saved"}catch{message=error.localizedDescription}}
 }
 func startDownload(all:Bool) {
  busy=true
  operation=Task {
   var failures=0
   let requested=all ? sessions.sorted{($0.name=="Race" ? 0:1,$0.start)<($1.name=="Race" ? 0:1,$1.start)}:sessions.filter{$0.id==selectedID}
   for s in requested {
    do {
     try Task.checkCancellation()
     let data=try await ReplayDownloads.shared.archive(s){m in await MainActor.run{message=m}}
     cached.insert(s.id)
     if !all {try race.loadReplay(data:data);race.mode="Replay";race.switchMode();race.playing=true;openWindow(id:"tabletop-resizable")}
    } catch {if Task.isCancelled{message="Download cancelled. Completed chunks are kept for retry.";break};failures+=1;message=error.localizedDescription;if !all{break}}
   }
   if !Task.isCancelled && failures==0 {message=all ? "Season download complete · \(cached.count) saved":"Replay ready"}
   else if all && !Task.isCancelled {message="\(cached.count) saved · \(failures) sessions unavailable or failed. Retry to resume."}
   busy=false
  }
 }
}
