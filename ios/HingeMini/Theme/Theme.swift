import SwiftUI

enum Theme {
    static let page = Color(red: 0.97, green: 0.965, blue: 0.953)
    static let plum = Color(red: 0.404, green: 0.161, blue: 0.373)
    static let palePlum = Color(red: 0.824, green: 0.769, blue: 0.831)
    static let beige = Color(red: 0.933, green: 0.882, blue: 0.859)
    static let ink = Color(red: 0.102, green: 0.102, blue: 0.102)
    static let secondary = Color(red: 0.435, green: 0.416, blue: 0.420)
    static let line = Color(red: 0.91, green: 0.894, blue: 0.882)
    static let card = Color.white
    static func serif(_ size: CGFloat) -> Font {
        .system(size: size, weight: .semibold, design: .serif)
    }
}

enum Brand {
    static let name = "Hinge Mini"
    static let tagline = "A little more connection."
}

struct PlumButton: View {
    let title: String
    var icon: String? = nil
    var disabled = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                if let icon { Image(systemName: icon) }
                Text(title).fontWeight(.semibold)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 16)
        }
        .buttonStyle(.plain)
        .foregroundStyle(Theme.card)
        .background(Theme.plum.opacity(disabled ? 0.4 : 1), in: Capsule())
        .disabled(disabled)
    }
}
