import Foundation
@main struct Tests {
 static func main() throws {
    let samples: [[Double]] = [[0,0,0,0],[2,20,40,6],[20,200,400,30]]
    assert(RaceMath.sample(samples,at:-1).0 == nil, "No future positions before first observation")
    assert(RaceMath.sample(samples,at:1).0 == SIMD3<Float>(10,20,3), "XYZ interpolation")
    assert(RaceMath.sample(samples,at:3).0 == SIMD3<Float>(20,40,6), "Do not interpolate across outages")
    assert(RaceMath.sample(samples,at:8).0 == nil, "Stale positions disappear")
    assert(RaceMath.sample(samples,at:30).0 == nil, "Do not extrapolate beyond archive")
    assert(RaceMath.latestIndex([10,12,14],at:11) == 0, "Panels use earlier snapshot, never future data")
    assert(RaceMath.latestIndex([],at:11) == nil)
    assert(RaceMath.liveTime(now:100,delay:30,oldest:10) == 68)
    assert(RaceMath.liveTime(now:100,delay:300,oldest:50) == 50, "Buffer warmup clamps to first received snapshot")
    let path = CommandLine.arguments[1]
    let root = try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:path))) as! [String:Any]
    let locations = root["locations"] as! [String:[[Double]]]
    assert(locations.count == 22)
    var count=0
    for (_,samples) in locations {
        assert(samples.allSatisfy{$0.count==4 && $0.allSatisfy(\.isFinite)})
        assert(zip(samples,samples.dropFirst()).allSatisfy{$0[0]<$1[0]})
        count += samples.count
    }
    assert(count > 100000)
    let feeds=root["feeds"] as! [String:[[String:Any]]]
    let positions=feeds["position"]!
    var latest:[Int:Int]=[:]
    for row in positions.sorted(by:{($0["date_seconds"] as! Double)<($1["date_seconds"] as! Double)}) where (row["date_seconds"] as! Double)<=1800 {
        latest[row["driver_number"] as! Int]=row["position"] as? Int
    }
    assert(latest.count==22 && latest.values.contains(1), "Complete historical order at thirty minutes")
    print("PASS: interpolation, missing/stale samples, delayed snapshot boundaries, buffer warmup, 22 drivers, \(count) ordered observations, historical order")
 }
}
