import Foundation

// Similarity registration preserves observed lateral positions. Elevation follows
// the modeled road surface, rather than noisy provider Z. Reject poor fits.
enum ReplayRegistration {
 static func register(_ root: inout Row, circuit: SeasonCircuit) -> Bool {
  guard let raw=root["locations"] as? [String:[[Double]]],let feeds=root["feeds"] as? [String:[Row]] else{return false}
  let target=circuit.points.map{ $0.map(Double.init) }
  let laps=(feeds["laps"] ?? []).filter{num($0["lap_number"])>1 && num($0["lap_duration"])>40 && num($0["lap_duration"])<250 && ($0["is_pit_out_lap"] as? Bool != true)}.sorted{num($0["lap_duration"])<num($1["lap_duration"])}
  let goal=resample(target,128)
  guard goal.count==128 else{return false}
  var best:(Double,Double,Double,Double,Double)?
  var attempted=0
  for lap in laps {
   let start=num(lap["date_start_seconds"]),end=start+num(lap["lap_duration"])
   let samples=(raw[String(Int(num(lap["driver_number"])))] ?? []).filter{$0.count==4 && $0[0]>=start && $0[0]<=end}
   guard samples.count>35 else{continue}
   attempted+=1;if attempted>8 {break}
   let source=resample(samples.map{Array($0[1...3])},128)
   guard source.count==128 else{continue}
   for reverse in [false,true] {
    let points=reverse ? Array(source.reversed()):source
    for shift in 0..<128 {
     let q=(0..<128).map{points[($0+shift)%128]}
     let mx=q.map{$0[0]}.reduce(0,+)/128,my=q.map{$0[1]}.reduce(0,+)/128
     let gx=goal.map{$0[0]}.reduce(0,+)/128,gy=goal.map{$0[1]}.reduce(0,+)/128
     var dot=0.0,cross=0.0,den=0.0
     for i in 0..<128 {let x=q[i][0]-mx,y=q[i][1]-my,u=goal[i][0]-gx,v=goal[i][1]-gy;dot+=x*u+y*v;cross+=x*v-y*u;den+=x*x+y*y}
     guard den>0 else{continue}
     let a=dot/den,b=cross/den,tx=gx-a*mx+b*my,ty=gy-b*mx-a*my
     let scale=hypot(a,b)
     guard scale>0.07 && scale<0.13 else{continue}
     var err=0.0
     for i in 0..<128 {let x=a*q[i][0]-b*q[i][1]+tx-goal[i][0],y=b*q[i][0]+a*q[i][1]+ty-goal[i][1];err+=x*x+y*y}
     err=sqrt(err/128)
     if best == nil || err<best!.0 {best=(err,a,b,tx,ty)}
    }
   }
  }
  guard let (rms,a,b,tx,ty)=best,rms<25 else{return false}
  var transformed:[String:[[Double]]]=[:]
  for (driver,rows) in raw {
   transformed[driver]=rows.filter{$0.count==4 && $0.allSatisfy(\.isFinite)}.map {p in
    let x=a*p[1]-b*p[2]+tx,y=b*p[1]+a*p[2]+ty
    var nearest=Double.infinity,z=0.0
    for i in target.indices {
     let q=target[i],r=target[(i+1)%target.count],dx=r[0]-q[0],dy=r[1]-q[1]
     let t=max(0,min(1,((x-q[0])*dx+(y-q[1])*dy)/max(1e-9,dx*dx+dy*dy)))
     let d=pow(x-q[0]-t*dx,2)+pow(y-q[1]-t*dy,2)
     if d<nearest {nearest=d;z=q[2]+t*(r[2]-q[2])}
    }
    return [p[0],x,y,z]
   }
  }
  root["locations"]=transformed;root["track"]=target
  root["registration"]=["circuit_id":circuit.id,"rms_m":rms,"transform":[a,b,tx,ty],"method":"Similarity-aligned recorded XY; modeled road elevation. Approximate, not surveyed."]
  return true
 }
 static func resample(_ points:[[Double]],_ count:Int)->[[Double]] {
  guard points.count>3,points.allSatisfy({$0.count>=3 && $0.allSatisfy(\.isFinite)}) else{return []}
  let p=points+[points[0]];var d=[0.0]
  for i in 1..<p.count {d.append(d.last!+hypot(p[i][0]-p[i-1][0],p[i][1]-p[i-1][1]))}
  guard let total=d.last,total>1 else{return []}
  var j=0
  return (0..<count).map{i in
   let s=Double(i)*total/Double(count)
   while j+1<d.count-1 && d[j+1]<s {j+=1}
   let t=(s-d[j])/max(1e-9,d[j+1]-d[j]);return (0..<3).map{p[j][$0]+t*(p[j+1][$0]-p[j][$0])}
  }
 }
}
