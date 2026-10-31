import SwiftUI

struct RootView: View {
    @Environment(AppStore.self) private var store
    var body: some View {
        @Bindable var store = store
        Group {
            if store.account == nil { AuthView() }
            else {
                TabView(selection: $store.selectedTab) {
                    NavigationStack { DiscoverView() }
                        .tabItem { Label("Discover", systemImage: "h.circle") }.tag(0)
                    NavigationStack { LikesView() }
                        .tabItem { Label("Likes You", systemImage: "heart") }.badge(store.likes.count).tag(1)
                    NavigationStack(path: $store.chatPath) {
                        MatchesView().navigationDestination(for: String.self) { ChatView(personID: $0) }
                    }.tabItem { Label("Matches", systemImage: "bubble.left.and.bubble.right") }.tag(2)
                    NavigationStack { ProfileView() }
                        .tabItem { Label("Profile", systemImage: "person.crop.circle") }.tag(3)
                }
            }
        }
        .foregroundStyle(Theme.ink)
        .sheet(item: $store.activeLike) { LikeSheet(item: $0).presentationDragIndicator(.visible) }
        .overlay(alignment: .top) {
            if let notice = store.notice {
                Text(notice).font(.subheadline).padding().foregroundStyle(Theme.card)
                    .background(Theme.plum, in: Capsule()).padding().allowsHitTesting(false)
            }
        }
        .task {
            await store.restore()
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(3))
                guard !Task.isCancelled else { return }
                await store.refresh()
            }
        }
    }
}

struct DiscoverView: View {
    @Environment(AppStore.self) private var store
    @State private var blocking = false
    var body: some View {
        Group {
            if let person = store.discoveryPeople.first {
                ScrollView { PersonDetail(person: person).padding(.bottom, 76) }
                    .id(person.id)
                    .navigationTitle(person.name)
                    .toolbar { Button("Block") { blocking = true } }
                    .confirmationDialog("Block \(person.name)?", isPresented: $blocking, titleVisibility: .visible) {
                        Button("Block", role: .destructive) { store.block(person) }
                    }
                    .overlay(alignment: .bottomLeading) {
                        Button { store.skip(person) } label: {
                            Image(systemName: "xmark").font(.title2).frame(width: 56, height: 56)
                                .background(Theme.card, in: Circle()).shadow(radius: 3)
                        }.padding().disabled(store.busy).accessibilityLabel("Pass on \(person.name)")
                    }
            } else {
                VStack {
                    EmptyState(title: "You're all caught up", message: "Check your likes or revisit passed profiles.")
                    PlumButton(title: "Revisit passed profiles", disabled: store.busy) {
                        Task { await store.action("/api/passes", method: "DELETE") }
                    }.padding()
                }.navigationTitle("Discover")
            }
        }.background(Theme.page).refreshable { await store.refresh() }
    }
}
