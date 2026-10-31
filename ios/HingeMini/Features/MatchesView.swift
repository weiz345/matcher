import SwiftUI

struct MatchesView: View {
    @Environment(AppStore.self) private var store
    var body: some View {
        List {
            ForEach(store.connections) { connection in
                NavigationLink(value: connection.id) {
                    HStack(spacing: 14) {
                        Avatar(name: connection.person.photos.first ?? "", size: 58)
                        VStack(alignment: .leading, spacing: 6) {
                            Text(connection.person.name).font(.headline)
                            Text(connection.messages.last?.text ?? "Say hello")
                                .font(.subheadline).foregroundStyle(Theme.secondary).lineLimit(1)
                        }
                    }.padding(.vertical, 8)
                }
            }
            if store.connections.isEmpty { Text("Mutual likes open a conversation here.") }
            Section { Text(store.backend.status).font(.caption).foregroundStyle(Theme.secondary) }
        }.scrollContentBackground(.hidden).background(Theme.page).navigationTitle("Matches")
            .refreshable { await store.refresh() }
    }
}

struct ChatView: View {
    @Environment(AppStore.self) private var store
    let personID: String // Conversation ID, kept stable for navigation.
    @State private var message = ""
    @State private var clientID = UUID().uuidString
    @State private var history: [ChatMessage] = []
    @State private var confirming: String?
    @State private var hasMore = true
    @State private var loading = false
    private func combined(_ recent: [ChatMessage]) -> [ChatMessage] {
        var seen = Set<String>()
        return (history + recent).filter { seen.insert($0.id).inserted }
            .sorted { (Int($0.id) ?? 0) < (Int($1.id) ?? 0) }
    }
    var body: some View {
        Group {
            if let connection = store.connection(personID) {
                let items = combined(connection.messages)
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(spacing: 16) {
                            if hasMore && items.count >= 100, let first = items.first {
                                Button("Load older messages") {
                                    loading = true
                                    Task {
                                        do {
                                            let older = try await store.backend.older(personID, before: first.id)
                                            history = older + history; hasMore = older.count == 100
                                        } catch { store.showNotice(error.localizedDescription) }
                                        loading = false
                                    }
                                }.disabled(loading)
                            }
                            ForEach(items) { item in
                                HStack(alignment: .bottom, spacing: 7) {
                                    if item.mine { Spacer(minLength: 38) }
                                    else { Avatar(name: connection.person.photos.first ?? "", size: 28) }
                                    Text(item.text).padding(14)
                                        .background(item.mine ? Theme.palePlum : Theme.beige, in: RoundedRectangle(cornerRadius: 18))
                                    if !item.mine { Spacer(minLength: 38) }
                                }.id(item.id)
                            }
                            Color.clear.frame(height: 1).id("bottom")
                        }.padding()
                    }
                    .onChange(of: connection.messages.last?.id) { _, _ in
                        withAnimation { proxy.scrollTo("bottom", anchor: .bottom) }
                    }
                    .onAppear { proxy.scrollTo("bottom", anchor: .bottom) }
                }
                .safeAreaInset(edge: .bottom) {
                    HStack(alignment: .bottom) {
                        TextField("Send a message", text: $message, axis: .vertical)
                            .lineLimit(1...4).padding(12)
                            .background(Theme.card, in: RoundedRectangle(cornerRadius: 20))
                            .onChange(of: message) { _, value in message = String(value.prefix(1000)); clientID = UUID().uuidString }
                        Button {
                            let sentText = message
                            Task {
                                if await store.sendMessage(sentText, to: personID, clientID: clientID), message == sentText {
                                    message = ""; clientID = UUID().uuidString
                                }
                            }
                        } label: { Image(systemName: "arrow.up.circle.fill").font(.system(size: 36)) }
                            .disabled(store.busy || message.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                            .accessibilityLabel("Send message")
                    }.padding().background(Theme.page)
                }
                .toolbar {
                    Menu("Options") {
                        Button("Unmatch", role: .destructive) { confirming = "Unmatch" }
                        Button("Block", role: .destructive) { confirming = "Block" }
                    }
                }
                .confirmationDialog("\(confirming ?? "End") this connection?", isPresented: Binding(get: { confirming != nil }, set: { if !$0 { confirming = nil } }), titleVisibility: .visible) {
                    Button(confirming ?? "Confirm", role: .destructive) {
                        if confirming == "Block" { store.block(connection.person) } else { store.unmatch(personID) }
                        confirming = nil
                    }
                }
            } else { EmptyState(title: "Conversation unavailable", message: "The match may have ended.") }
        }.background(Theme.page)
            .navigationTitle(store.connection(personID)?.person.name ?? "Chat")
            .navigationBarTitleDisplayMode(.inline)
    }
}
