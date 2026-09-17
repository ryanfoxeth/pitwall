#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
cat > "$TMP/main.swift" <<'SWIFT'
import Foundation
typealias Row=[String:Any]
func num(_ v:Any?)->Double{(v as? NSNumber)?.doubleValue ?? 0}
struct SeasonCircuit:Decodable {let id:String;let points:[[Float]]}
let catalog=try JSONDecoder().decode([SeasonCircuit].self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
let c=catalog.first{$0.id=="monaco"}!
let observed=c.points.enumerated().map {i,p -> [Double] in
 let x=Double(p[0]),y=Double(p[1]);return [Double(i)*100/Double(c.points.count),10*(cos(0.7)*x-sin(0.7)*y)+4500,10*(sin(0.7)*x+cos(0.7)*y)-2600,42]
}
var root:Row=["locations":["16":observed],"feeds":["laps":[["driver_number":16,"lap_number":2,"lap_duration":100,"date_start_seconds":0]]]]
precondition(ReplayRegistration.register(&root,circuit:c))
let info=root["registration"] as! Row
precondition(num(info["rms_m"])<0.01)
let rows=(root["locations"] as! [String:[[Double]]])["16"]!
for i in rows.indices {precondition(abs(rows[i][0]-observed[i][0])<0.0001);precondition(hypot(rows[i][1]-Double(c.points[i][0]),rows[i][2]-Double(c.points[i][1]))<0.01)}
var empty:Row=["locations":[String:[[Double]]](),"feeds":["laps":[Row]()]]
precondition(!ReplayRegistration.register(&empty,circuit:c))
print("Replay registration passed: rotation, translation, scale, timestamp preservation and missing-data rejection")
SWIFT
swiftc -O "$ROOT/Sources/ReplayRegistration.swift" "$TMP/main.swift" -o "$TMP/check"
"$TMP/check" "$ROOT/Sources/Resources/Season2026.json"
