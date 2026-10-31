import Foundation

struct Prompt: Identifiable, Codable, Hashable {
    var id: String
    var title: String
    var answer: String
}
struct Person: Identifiable, Codable, Hashable {
    var id: String
    var name: String
    var age: Int
    var job: String
    var location: String
    var height: String
    var photos: [String]
    var prompts: [Prompt]
}
struct LikedItem: Identifiable {
    var person: Person
    var photo: String?
    var prompt: Prompt?
    var id: String { person.id + (photo ?? prompt?.id ?? "") }
}
struct IncomingLike: Identifiable, Codable {
    var id: String
    var person: Person
    var comment: String
    var itemType: String
    var itemID: String
}
struct ChatMessage: Identifiable, Codable {
    var id: String
    var text: String
    var mine: Bool
    var senderID: String
    var createdAt: Int
}
struct Connection: Identifiable, Codable {
    var id: String
    var person: Person
    var messages: [ChatMessage]
}
struct AccountState: Codable {
    var me: Person
    var discover: [Person]
    var likes: [IncomingLike]
    var matches: [Connection]
}
struct MutationResult: Decodable {
    var app: AccountState
    var matchID: String?
}
