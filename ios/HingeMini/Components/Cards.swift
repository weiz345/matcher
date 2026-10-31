import SwiftUI
import UIKit

struct DemoPhoto: View {
    @Environment(AppStore.self) private var store
    let name: String
    @State private var image: UIImage?
    var body: some View {
        GeometryReader { geometry in
            Group {
                if let image { Image(uiImage: image).resizable().scaledToFill() }
                else { Rectangle().fill(Theme.beige).overlay(Image(systemName: "person")) }
            }.frame(width: geometry.size.width, height: geometry.size.height).clipped()
        }
        .task(id: name) {
            image = nil
            guard name.hasPrefix("/api/photos/") else { return }
            if let data = try? await store.backend.photo(name) { image = UIImage(data: data) }
        }
        .accessibilityLabel("Profile photo")
    }
}

struct Avatar: View {
    let name: String
    var size: CGFloat = 52
    var body: some View {
        DemoPhoto(name: name).frame(width: size, height: size).clipShape(Circle())
    }
}

struct HeartButton: View {
    let action: () -> Void
    var body: some View {
        Button(action: action) {
            Image(systemName: "heart").font(.system(size: 24))
                .foregroundStyle(Theme.plum)
                .frame(width: 48, height: 48)
                .background(Theme.card, in: Circle())
                .shadow(color: Theme.ink.opacity(0.08), radius: 6, y: 2)
        }
        .accessibilityLabel("Like this item")
    }
}

struct PromptCard: View {
    let prompt: Prompt
    var like: (() -> Void)? = nil
    var body: some View {
        VStack(alignment: .leading, spacing: 15) {
            Text(prompt.title).font(.subheadline.weight(.medium))
            Text(prompt.answer).font(Theme.serif(30)).fixedSize(horizontal: false, vertical: true)
            if let like {
                HStack { Spacer(); HeartButton(action: like) }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(24)
        .background(Theme.card, in: RoundedRectangle(cornerRadius: 12))
    }
}

struct PersonDetail: View {
    @Environment(AppStore.self) private var store
    let person: Person
    var allowsLikes = true
    var body: some View {
        VStack(spacing: 16) {
            ForEach(Array(person.photos.enumerated()), id: \.offset) { index, photo in
                DemoPhoto(name: photo)
                    .aspectRatio(4 / 5, contentMode: .fit)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                    .overlay(alignment: .bottomTrailing) {
                        if allowsLikes {
                            HeartButton { store.activeLike = LikedItem(person: person, photo: photo) }.padding(16)
                        }
                    }
            }
            vitals
            ForEach(person.prompts) { prompt in
                PromptCard(prompt: prompt, like: allowsLikes ? {
                    store.activeLike = LikedItem(person: person, prompt: prompt)
                } : nil)
            }
        }.padding(.horizontal, 8)
    }
    private var vitals: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(spacing: 22) {
                Label("\(person.age)", systemImage: "birthday.cake")
                Label(person.height, systemImage: "ruler")
            }
            Divider()
            Label(person.job, systemImage: "briefcase")
            Label(person.location, systemImage: "mappin.and.ellipse")
            Label("Long-term relationship", systemImage: "heart")
        }
        .font(.subheadline).frame(maxWidth: .infinity, alignment: .leading)
        .padding(22).background(Theme.card, in: RoundedRectangle(cornerRadius: 12))
    }
}

struct EmptyState: View {
    let title: String
    let message: String
    var body: some View {
        ContentUnavailableView {
            Label(title, systemImage: "heart")
        } description: { Text(message) }
    }
}
