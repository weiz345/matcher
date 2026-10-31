import SwiftUI

@main
struct HingeMiniApp: App {
    @State private var store = AppStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
                .tint(Theme.plum)
                .preferredColorScheme(.light)
        }
    }
}
