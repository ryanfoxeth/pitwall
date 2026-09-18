import Foundation

/// Fit the provider outline once; transform every car into the same catalog frame.
/// Reject incomplete/poor fits rather than putting cars onto unrelated scenery.
struct LiveCircuitRegistration {
 private var source:[SIMD3<Float>]=[]
 private var circuitID=""
 private var coefficients:[Double]?
 var track:[SIMD3<Float>]?
 mutating func configure(provider:Int,outline:[SIMD3<Float>])->Bool {
  let id=CircuitScenery.providerIDs[provider] ?? ""
  guard source != outline || circuitID != id else{return false}
  let previous=coefficients;let previousID=circuitID
  source=outline;circuitID=id;coefficients=nil;track=nil
  guard outline.count>35,outline.allSatisfy({$0.x.isFinite && $0.y.isFinite}),let c=CircuitCatalog.all.first(where:{$0.id==id}) else{return previous != nil}
  let samples=outline.enumerated().map{i,p in [Double(i)*100/Double(outline.count),Double(p.x),Double(p.y),0.0]}
  var data:Row=["locations":["0":samples],"feeds":["laps":[["driver_number":0,"lap_number":2,"lap_duration":100,"date_start_seconds":0]]]]
  if ReplayRegistration.register(&data,circuit:c),let info=data["registration"] as? Row,let transform=info["transform"] as? [Double] {coefficients=transform;track=c.track}
  return previous != coefficients || previousID != circuitID
 }
 func point(_ p:SIMD3<Float>)->SIMD3<Float> {
  guard let t=coefficients,let road=track else{return p}
  let x=Float(t[0]*Double(p.x)-t[1]*Double(p.y)+t[2]),y=Float(t[1]*Double(p.x)+t[0]*Double(p.y)+t[3])
  var nearest=Float.infinity,z:Float=0
  for i in road.indices {
   let a=road[i],b=road[(i+1)%road.count];let dx=b.x-a.x,dy=b.y-a.y
   let u=max(0,min(1,((x-a.x)*dx+(y-a.y)*dy)/max(1e-8,dx*dx+dy*dy)))
   let distance=(x-a.x-u*dx)*(x-a.x-u*dx)+(y-a.y-u*dy)*(y-a.y-u*dy)
   if distance<nearest {nearest=distance;z=a.z+u*(b.z-a.z)}
  }
  return SIMD3(x,y,z)
 }
}
