import Foundation

/// One display scale for the whole season, independent of circuit, theme and yaw.
/// Encloses the largest authored neighborhood at any rotation (Baku: 3513 m
/// diagonal), and the tallest themed scene (295 m). Checked by native validation.
enum TabletopScale {
 static let horizontalMeters:Float = 3600
 static let verticalMeters:Float = 350
 static func metersToDisplay(_ available:SIMD3<Float>)->Float {
  0.96 * min(available.x/horizontalMeters,min(available.z/horizontalMeters,available.y/verticalMeters))
 }
}
