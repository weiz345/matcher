import SwiftUI
import Observation

@MainActor @Observable
final class AppStore {
    var backend = BackendSync()
    var account: AccountState?
    var selectedTab = 0
    var chatPath: [String] = []
    var activeLike: LikedItem?
    var busy = false
    var notice: String?
    private var version = 0
    private var noticeTask: Task<Void, Never>?

    var discoveryPeople: [Person] { account?.discover ?? [] }
    var likes: [IncomingLike] { account?.likes ?? [] }
    var connections: [Connection] { account?.matches ?? [] }
    func connection(_ id: String) -> Connection? { connections.first { $0.id == id } }
    func showNotice(_ text: String) {
        noticeTask?.cancel(); notice = text
        noticeTask = Task { [weak self] in
            try? await Task.sleep(for: .seconds(4))
            guard !Task.isCancelled else { return }; self?.notice = nil
        }
    }
    func restore() async {
        guard account == nil, !busy else { return }
        busy = true; defer { busy = false }
        do { account = try await backend.restore() }
        catch { backend.status = "Sign in to continue" }
    }
    func authenticate(signup: Bool, email: String, password: String, name: String, age: Int) async {
        guard !busy else { return }; busy = true; defer { busy = false }
        do {
            account = try await backend.authenticate(signup: signup, email: email, password: password, name: name, age: age)
            version += 1; selectedTab = 0; chatPath = []; backend.status = "Connected"
        } catch { showNotice(error.localizedDescription) }
    }
    func refresh() async {
        guard account != nil, !busy else { return }
        let current = version
        do {
            let result = try await backend.load()
            guard current == version, !busy else { return }
            account = result
            if let id = chatPath.last, connection(id) == nil { chatPath = [] }
        } catch {
            guard current == version, !busy else { return }
            backend.status = "Connection unavailable"
            if (error as NSError).code == 401 { account = nil; chatPath = [] }
        }
    }
    @discardableResult func action(_ path: String, method: String = "POST", body: [String: Any] = [:]) async -> MutationResult? {
        guard !busy else { return nil }; busy = true; version += 1; defer { busy = false }
        do {
            let result = try await backend.mutate(path, method: method, body: body)
            account = result.app; version += 1
            if let id = chatPath.last, connection(id) == nil { chatPath = [] }
            return result
        } catch { showNotice(error.localizedDescription); return nil }
    }
    func skip(_ person: Person) { Task { await action("/api/pass", body: ["target": person.id]) } }
    func block(_ person: Person) { Task { await action("/api/blocks", body: ["target": person.id]) } }
    func unmatch(_ id: String) { Task { await action("/api/conversations/\(id)", method: "DELETE") } }
    func sendLike(_ item: LikedItem, comment: String) async -> Bool {
        let kind = item.photo == nil ? "prompt" : "photo"
        let id = item.photo?.split(separator: "/").last.map(String.init) ?? item.prompt?.id ?? ""
        if let result = await action("/api/likes", body: ["target": item.person.id, "itemType": kind, "itemID": id, "comment": comment]) {
            if let id = result.matchID { chatPath = [id]; selectedTab = 2; showNotice("It's a match!") }
            else { showNotice("Like sent") }
            return true
        }
        return false
    }
    func accept(_ like: IncomingLike) async -> Bool {
        if let result = await action("/api/likes/\(like.id)/accept"), let id = result.matchID {
            selectedTab = 2; chatPath = [id]; showNotice("It's a match!"); return true
        }
        return false
    }
    func sendMessage(_ text: String, to id: String, clientID: String) async -> Bool {
        let cleaned = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleaned.isEmpty else { return false }
        return await action("/api/conversations/\(id)/messages", body: ["text": cleaned, "clientID": clientID]) != nil
    }
    func saveProfile(_ person: Person) async -> Bool {
        await action("/api/profile", method: "PUT", body: ["name": person.name, "age": person.age,
                    "location": person.location, "job": person.job, "height": person.height,
                    "prompts": person.prompts.map { ["id": $0.id, "title": $0.title, "answer": $0.answer] }]) != nil
    }
    func upload(_ data: Data) async {
        await action("/api/photos", body: ["data": data.base64EncodedString()])
    }
    func logout() async {
        guard !busy else { return }; busy = true; defer { busy = false }
        do {
            try await backend.logout(); version += 1; account = nil; chatPath = []; activeLike = nil
        } catch { showNotice(error.localizedDescription) }
    }
}
