import SwiftUI

struct LikeSheet: View {
    @Environment(AppStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    let item: LikedItem
    @State private var comment = ""
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                HStack {
                    Text("Like \(item.person.name)").font(Theme.serif(28))
                    Spacer(); Button("Cancel") { dismiss() }
                }
                if let photo = item.photo {
                    DemoPhoto(name: photo).frame(height: 290).clipShape(RoundedRectangle(cornerRadius: 12))
                }
                if let prompt = item.prompt { PromptCard(prompt: prompt) }
                TextField("Add a comment", text: $comment, axis: .vertical)
                    .lineLimit(2...4).padding().background(Theme.card, in: RoundedRectangle(cornerRadius: 12))
                    .onChange(of: comment) { _, value in comment = String(value.prefix(300)) }
                PlumButton(title: "Send like", icon: "heart", disabled: store.busy) {
                    Task {
                        if await store.sendLike(item, comment: comment.trimmingCharacters(in: .whitespacesAndNewlines)) { dismiss() }
                    }
                }
                Text("If they like you back, you can message each other.")
                    .font(.caption).foregroundStyle(Theme.secondary)
            }.padding(24)
        }.background(Theme.page)
    }
}
