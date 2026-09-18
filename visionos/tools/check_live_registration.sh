#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
cat > "$TMP/main.swift" <<'SWIFT'
import Foundation
typealias Row=[String:Any]
func num(_ v:Any?)->Double{(v as? NSNumber)?.doubleValue ?? 0}
struct SeasonCircuit:Decodable {let id:String;let points:[[Float]];var track:[SIMD3<Float>]{points.map{SIMD3($0[0],$0[1],$0[2])}}}
enum CircuitCatalog {static var all:[SeasonCircuit]=[]}
enum CircuitScenery {static let providerIDs=[144:"baku",12:"sepang",61:"marina_bay",9:"americas",65:"rodriguez",14:"interlagos",152:"vegas",150:"losail",70:"yas_marina",22:"monaco"]}
CircuitCatalog.all=try JSONDecoder().decode([SeasonCircuit].self,from:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1])))
for (key,id) in CircuitScenery.providerIDs {
 let c=CircuitCatalog.all.first{$0.id==id}!
 let observed=c.track.map{p -> SIMD3<Float> in SIMD3(10*(cos(0.7)*p.x-sin(0.7)*p.y)+4500,10*(sin(0.7)*p.x+cos(0.7)*p.y)-2600,0)}
 var registration=LiveCircuitRegistration();_ = registration.configure(provider:key,outline:observed)
 precondition(registration.track==c.track,"Failed registration \(id)")
 for i in observed.indices {let p=registration.point(observed[i]);precondition(hypot(p.x-c.track[i].x,p.y-c.track[i].y)<0.05,"Coordinate error \(id)")}
 precondition(!registration.configure(provider:key,outline:observed),"Unchanged source invalidates buffer")
 _ = registration.configure(provider:0,outline:observed);precondition(registration.track==nil,"Unknown circuit attached scenery")
 _ = registration.configure(provider:key,outline:Array(observed.prefix(10)));precondition(registration.track==nil,"Incomplete outline accepted")
 print(id,"live transform, caching and rejection passed")
}
SWIFT
swiftc -O "$ROOT/Sources/ReplayRegistration.swift" "$ROOT/Sources/LiveCircuitRegistration.swift" "$TMP/main.swift" -o "$TMP/check"
"$TMP/check" "$ROOT/Sources/Resources/Season2026.json"
