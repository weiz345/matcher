import SwiftUI
import PhotosUI
import UIKit

struct ProfileView: View {
    @Environment(AppStore.self) private var store
    @State private var draft: Person?
    @State private var selectedPhoto: PhotosPickerItem?
    @State private var photoBusy = false
    @State private var confirmLogout = false
    var body: some View {
        Form {
            if let profile = draft {
                Section("Your basics") {
                    TextField("Name", text: field(\Person.name)).onChange(of: draft?.name) { _, _ in draft?.name = String((draft?.name ?? "").prefix(40)) }
                    Stepper("Age: \(profile.age)", value: Binding(get: { draft?.age ?? 27 }, set: { draft?.age = $0 }), in: 18...120)
                    TextField("Location", text: field(\Person.location))
                    TextField("Work", text: field(\Person.job))
                }
                Section("Photos") {
                    ForEach(store.account?.me.photos ?? [], id: \.self) { photo in
                        HStack {
                            DemoPhoto(name: photo).frame(width: 80, height: 100).clipShape(RoundedRectangle(cornerRadius: 8))
                            Spacer()
                            Button("Remove", role: .destructive) {
                                Task { await store.action(photo, method: "DELETE") }
                            }.disabled(store.busy || photoBusy)
                        }
                    }
                    if (store.account?.me.photos.count ?? 0) < 6 {
                        PhotosPicker(selection: $selectedPhoto, matching: .images) {
                            Label(photoBusy ? "Uploading…" : "Add photo", systemImage: "plus")
                        }.disabled(store.busy || photoBusy)
                    }
                }
                Section("Written prompts") {
                    ForEach(Array(profile.prompts.enumerated()), id: \.element.id) { index, _ in
                        TextField("Prompt", text: promptField(index, title: true))
                        TextField("Answer", text: promptField(index, title: false), axis: .vertical)
                            .font(Theme.serif(24)).lineLimit(2...5)
                    }
                    if profile.prompts.count < 3 {
                        Button("Add prompt") {
                            draft?.prompts.append(Prompt(id: UUID().uuidString, title: "Together, we could", answer: ""))
                        }
                    }
                }
                Section {
                    Button("Save profile") {
                        Task { if await store.saveProfile(profile) { draft = store.account?.me; store.showNotice("Profile saved") } }
                    }.disabled(store.busy)
                    Text(store.backend.status).font(.caption).foregroundStyle(Theme.secondary)
                }
            }
            Section {
                Button("Log out", role: .destructive) { confirmLogout = true }
                Text("Your account and photos are stored on the server. Messages are written by other signed-in users.")
                    .font(.caption).foregroundStyle(Theme.secondary)
            }
        }.scrollContentBackground(.hidden).background(Theme.page).navigationTitle("Your profile")
            .onAppear { if draft == nil { draft = store.account?.me } }
            .confirmationDialog("Log out? Unsaved profile edits will be lost.", isPresented: $confirmLogout) {
                Button("Log out", role: .destructive) { Task { await store.logout() } }
            }
            .onChange(of: selectedPhoto) { _, item in
                guard let item else { return }
                photoBusy = true
                Task { @MainActor in
                    defer { photoBusy = false; selectedPhoto = nil }
                    guard let data = try? await item.loadTransferable(type: Data.self), let image = UIImage(data: data) else {
                        store.showNotice("Could not load that photo"); return
                    }
                    let longest = max(image.size.width, image.size.height)
                    guard longest > 0 else { return }
                    let scale = min(1, 1200 / longest)
                    let size = CGSize(width: image.size.width * scale, height: image.size.height * scale)
                    let rendered = UIGraphicsImageRenderer(size: size).image { _ in image.draw(in: CGRect(origin: .zero, size: size)) }
                    if let jpeg = rendered.jpegData(compressionQuality: 0.8) { await store.upload(jpeg) }
                }
            }
    }
    private func field(_ key: WritableKeyPath<Person, String>) -> Binding<String> {
        Binding(get: { draft?[keyPath: key] ?? "" }, set: { draft?[keyPath: key] = String($0.prefix(80)) })
    }
    private func promptField(_ index: Int, title: Bool) -> Binding<String> {
        Binding(get: {
            guard let draft, draft.prompts.indices.contains(index) else { return "" }
            return title ? draft.prompts[index].title : draft.prompts[index].answer
        }, set: { value in
            guard draft?.prompts.indices.contains(index) == true else { return }
            if title { draft?.prompts[index].title = String(value.prefix(100)) }
            else { draft?.prompts[index].answer = String(value.prefix(300)) }
        })
    }
}
