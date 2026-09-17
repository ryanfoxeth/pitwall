import Foundation

enum RaceMath {
    static func latestIndex(_ times: [Double], at time: Double) -> Int? {
        var low = 0, high = times.count
        while low < high {
            let middle = (low + high) / 2
            if times[middle] <= time { low = middle + 1 } else { high = middle }
        }
        return low > 0 ? low - 1 : nil
    }
    static func sample(_ samples: [[Double]], at time: Double) -> (SIMD3<Float>?, Float) {
        var low = 0, high = samples.count
        while low < high {
            let middle = (low + high) / 2
            if samples[middle][0] <= time { low = middle + 1 } else { high = middle }
        }
        guard low > 0 else { return (nil, 0) }
        let i = low - 1
        let p = samples[i]
        guard time - p[0] <= 5 else { return (nil, 0) }
        let q = samples[min(i + 1, samples.count - 1)]
        let duration = q[0] - p[0]
        let fraction = duration > 0 && duration <= 5 ? min(1, max(0, (time - p[0]) / duration)) : 0
        return (SIMD3(Float(p[1] + (q[1]-p[1])*fraction), Float(p[2] + (q[2]-p[2])*fraction), Float(p[3] + (q[3]-p[3])*fraction)), Float(atan2(q[2]-p[2], q[1]-p[1])))
    }
    static func liveTime(now: Double, delay: Double, oldest: Double) -> Double {
        max(oldest, now - min(300, max(0, delay)) - 2)
    }
}
