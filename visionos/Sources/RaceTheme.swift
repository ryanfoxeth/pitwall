import SwiftUI
import UIKit

enum RaceTheme: String, CaseIterable, Identifiable {
    case tron, kart, miniature, grandPrix
    var id: String { rawValue }
    var title: String { switch self { case .tron: "Tron"; case .kart: "Retro Kart"; case .grandPrix: "Grand Prix"; case .miniature: "F1 Miniature" } }
    var detail: String { switch self {
    case .grandPrix: "Detailed formula cars · team liveries · driver numbers"
    case .tron: "Leader and followed driver ride lightcycles · grid blocks"
    case .kart: "Chunky karts · bright barriers · low-poly park"
    case .miniature: "Open-wheel cars · asphalt · red-and-white curbs"
    } }
    var accent: Color { switch self { case .tron: .cyan; case .kart: .orange; case .grandPrix: .red; case .miniature: .mint } }
    var ground: UIColor { switch self { case .tron: UIColor(white:0.035,alpha:1); case .kart: UIColor(red:0.24,green:0.65,blue:0.25,alpha:1); case .miniature, .grandPrix: UIColor(red:0.13,green:0.28,blue:0.18,alpha:1) } }
    var road: UIColor { switch self { case .tron: UIColor(white:0.09,alpha:1); case .kart: UIColor(red:0.28,green:0.29,blue:0.30,alpha:1); case .miniature, .grandPrix: UIColor(white:0.19,alpha:1) } }
}
