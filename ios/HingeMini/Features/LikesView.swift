import SwiftUI

struct LikesView: View {
    @Environment(AppStore.self) private var store
    var body: some View {
        ScrollView {
            LazyVStack(spacing: 20) {
                ForEach(store.likes) { like in
                    NavigationLink { IncomingProfile(person: like.person, like: like) } label: {
                        VStack(alignment: .leading, spacing: 14) {
                            DemoPhoto(name: like.person.photos.first ?? "").frame(height: 300).clipped()
                            VStack(alignment: .leading, spacing: 12) {
                                Text("Liked your \(like.itemType)").font(.caption).foregroundStyle(Theme.plum)
                                Text("\(like.person.name), \(like.person.age)").font(Theme.serif(28))
                                if !like.comment.isEmpty { Text("“\(like.comment)”").foregroundStyle(Theme.secondary) }
                                Text("View profile →").font(.subheadline.weight(.semibold))
                            }.padding([.horizontal, .bottom])
                        }.background(Theme.card, in: RoundedRectangle(cornerRadius: 16))
                            .clipShape(RoundedRectangle(cornerRadius: 16))
                    }.buttonStyle(.plain)
                }
                if store.likes.isEmpty { EmptyState(title: "All caught up", message: "Incoming likes from other accounts appear here.") }
            }.padding()
        }.background(Theme.page).navigationTitle("Likes You").refreshable { await store.refresh() }
    }
}

struct IncomingProfile: View {
    @Environment(AppStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    let person: Person
    let like: IncomingLike
    @State private var blocking = false
    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Liked your \(like.itemType)").font(.caption).foregroundStyle(Theme.plum)
                    if let prompt = store.account?.me.prompts.first(where: { $0.id == like.itemID }) {
                        PromptCard(prompt: prompt)
                    } else if like.itemType == "photo", store.account?.me.photos.contains("/api/photos/\(like.itemID)") == true {
                        DemoPhoto(name: "/api/photos/\(like.itemID)").frame(height: 180)
                    } else { Text("The original item has been removed.").font(.caption) }
                    if !like.comment.isEmpty { Text("“\(like.comment)”").font(Theme.serif(23)) }
                }.padding()
                PersonDetail(person: person, allowsLikes: false)
            }
        }.background(Theme.page).navigationTitle(person.name)
            .toolbar { Button("Block") { blocking = true } }
            .confirmationDialog("Block \(person.name)?", isPresented: $blocking, titleVisibility: .visible) {
                Button("Block", role: .destructive) { store.block(person); dismiss() }
            }
            .safeAreaInset(edge: .bottom) {
                HStack {
                    Button("Pass") { store.skip(person); dismiss() }.padding()
                    PlumButton(title: "Like back", icon: "heart", disabled: store.busy) {
                        Task { if await store.accept(like) { dismiss() } }
                    }
                }.padding().background(Theme.page)
            }
    }
}
