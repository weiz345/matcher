import Foundation
import Observation
import Security

private struct DirectSession: Codable {
    var accessToken: String
    var refreshToken: String
    var expiresAt: TimeInterval
    var userID: String
}

@MainActor @Observable
final class BackendSync {
    var address = Bundle.main.object(forInfoDictionaryKey: "HingeSupabaseProjectURL") as? String ?? ""
    var status = "Sign in with Supabase"
    private var session: DirectSession?
    private var refreshTask: Task<DirectSession, Error>?
    private var key: String { Bundle.main.object(forInfoDictionaryKey: "HingeSupabasePublishableKey") as? String ?? "" }
    private var base: URL { URL(string: address)! }

    private func configure() throws {
        guard let url = URL(string: address), url.scheme == "https", url.host != nil, !key.isEmpty else {
            throw failure("Missing Supabase project URL or publishable key")
        }
        if let value = KeychainToken.load(account: address), let data = value.data(using: .utf8) {
            session = try? JSONDecoder().decode(DirectSession.self, from: data)
        }
    }
    func restore() async throws -> AccountState { try configure(); return try await load() }
    func authenticate(signup: Bool, email: String, password: String, name: String, age: Int) async throws -> AccountState {
        try configure()
        var body: [String: Any] = ["email": email, "password": password]
        if signup { body["data"] = ["name": name, "age": age] }
        let data = try await request(signup ? "/auth/v1/signup" : "/auth/v1/token?grant_type=password", method: "POST", body: body, authenticated: false)
        let value = try dictionary(data)
        guard value["access_token"] != nil else { throw failure("Check your email to confirm your account, then log in.") }
        session = try decodeSession(value)
        try persist()
        return try await load()
    }
    func load() async throws -> AccountState {
        let data = try await rpc("dating_bootstrap")
        status = "Supabase · updates every 3s"
        return try JSONDecoder().decode(AccountState.self, from: data)
    }
    func mutate(_ path: String, method: String = "POST", body: [String: Any] = [:]) async throws -> MutationResult {
        let parts = path.split(separator: "/").map(String.init)
        var action = "", payload = body
        if path == "/api/photos" {
            guard let encoded = body["data"] as? String, let image = Data(base64Encoded: encoded) else { throw failure("Invalid photo") }
            _ = try await token()
            let id = UUID().uuidString.lowercased(), object = "\(session!.userID)/\(id)"
            _ = try await request("/storage/v1/object/dating-photos/\(object)", method: "POST", bytes: image, mime: "image/jpeg")
            do {
                let data = try await rpc("dating_action", ["p_action": "photo_register", "p_body": ["id": id, "mime": "image/jpeg"]])
                return try JSONDecoder().decode(MutationResult.self, from: data)
            } catch { try? await removeObject(object); throw error }
        } else if parts.count == 3 && parts[1] == "photos" {
            let info = try dictionary(await rpc("dating_photo", ["p_id": parts[2]]))
            let data = try await rpc("dating_action", ["p_action": "photo_delete", "p_body": ["id": parts[2]]])
            if let object = info["path"] as? String { try? await removeObject(object) }
            return try JSONDecoder().decode(MutationResult.self, from: data)
        } else if path == "/api/profile" { action = "profile" }
        else if path == "/api/likes" { action = "like" }
        else if parts.count == 4 && parts[1] == "likes" { action = "accept"; payload = ["target": parts[2]] }
        else if path == "/api/pass" { action = "pass" }
        else if path == "/api/passes" { action = "revisit" }
        else if path == "/api/blocks" { action = "block" }
        else if parts.count >= 3 && parts[1] == "conversations" {
            action = method == "DELETE" ? "unmatch" : "message"; payload["conversation"] = parts[2]
        } else { throw failure("Unknown operation") }
        let data = try await rpc("dating_action", ["p_action": action, "p_body": payload])
        status = "Saved to Supabase"
        return try JSONDecoder().decode(MutationResult.self, from: data)
    }
    func older(_ id: String, before: String) async throws -> [ChatMessage] {
        struct Page: Decodable { var messages: [ChatMessage] }
        let data = try await rpc("dating_messages", ["p_conversation": id, "p_before": before])
        return try JSONDecoder().decode(Page.self, from: data).messages
    }
    func photo(_ path: String) async throws -> Data {
        let id = path.split(separator: "/").last.map(String.init) ?? ""
        let info = try dictionary(await rpc("dating_photo", ["p_id": id]))
        guard let object = info["path"] as? String else { throw failure("Photo unavailable") }
        return try await request("/storage/v1/object/authenticated/dating-photos/\(object)")
    }
    func logout() async throws {
        defer { session = nil; KeychainToken.remove(account: address); status = "Signed out" }
        _ = try? await request("/auth/v1/logout?scope=local", method: "POST", body: [:])
    }
    private func removeObject(_ path: String) async throws {
        _ = try await request("/storage/v1/object/dating-photos", method: "DELETE", body: ["prefixes": [path]])
    }
    private func rpc(_ name: String, _ body: [String: Any] = [:]) async throws -> Data {
        try await request("/rest/v1/rpc/\(name)", method: "POST", body: body)
    }
    private func token() async throws -> String {
        guard let session else { throw failure("Please log in", code: 401) }
        if session.expiresAt > Date().timeIntervalSince1970 + 60 { return session.accessToken }
        if refreshTask == nil {
            refreshTask = Task {
                let data = try await self.request("/auth/v1/token?grant_type=refresh_token", method: "POST",
                                                  body: ["refresh_token": session.refreshToken], authenticated: false)
                return try self.decodeSession(self.dictionary(data))
            }
        }
        defer { refreshTask = nil }
        do {
            self.session = try await refreshTask!.value
            try persist()
            return self.session!.accessToken
        } catch {
            if [400, 401].contains((error as NSError).code) {
                self.session = nil; KeychainToken.remove(account: address)
                throw failure("Session expired. Please log in again.", code: 401)
            }
            throw error
        }
    }
    private func request(_ path: String, method: String = "GET", body: [String: Any]? = nil,
                         bytes: Data? = nil, mime: String = "application/json", authenticated: Bool = true) async throws -> Data {
        guard let url = URL(string: path, relativeTo: base), url.host == base.host, url.scheme == "https" else { throw failure("Invalid Supabase URL") }
        var request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 30)
        request.httpMethod = method; request.httpShouldHandleCookies = false
        request.setValue(key, forHTTPHeaderField: "apikey")
        if authenticated { request.setValue("Bearer \(try await token())", forHTTPHeaderField: "Authorization") }
        if let bytes {
            request.httpBody = bytes; request.setValue(mime, forHTTPHeaderField: "Content-Type")
            request.setValue("max-age=0", forHTTPHeaderField: "Cache-Control")
        }
        else if let body {
            request.httpBody = try JSONSerialization.data(withJSONObject: body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        if path.hasPrefix("/storage/v1/object/authenticated/") { request.setValue("no-cache", forHTTPHeaderField: "Cache-Control") }
        let (data, response) = try await URLSession.shared.data(for: request)
        guard let response = response as? HTTPURLResponse else { throw failure("Invalid response") }
        guard (200..<300).contains(response.statusCode) else {
            let value = (try? dictionary(data)) ?? [:]
            throw failure(value["message"] as? String ?? value["msg"] as? String ?? value["error_description"] as? String ?? "Supabase request failed", code: response.statusCode)
        }
        return data
    }
    private func dictionary(_ data: Data) throws -> [String: Any] {
        guard let value = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw failure("Invalid server response") }
        return value
    }
    private func decodeSession(_ value: [String: Any]) throws -> DirectSession {
        guard let access = value["access_token"] as? String, let refresh = value["refresh_token"] as? String,
              let user = value["user"] as? [String: Any], let id = user["id"] as? String else { throw failure("Invalid login response") }
        return DirectSession(accessToken: access, refreshToken: refresh,
                             expiresAt: Date().timeIntervalSince1970 + (value["expires_in"] as? Double ?? 3600), userID: id)
    }
    private func persist() throws {
        guard let session else { return }
        let value = String(decoding: try JSONEncoder().encode(session), as: UTF8.self)
        try KeychainToken.save(value, account: address)
    }
    private func failure(_ message: String, code: Int = 0) -> NSError {
        NSError(domain: "HingeMini.Supabase", code: code, userInfo: [NSLocalizedDescriptionKey: message])
    }
}

enum KeychainToken {
    private static func query(_ account: String) -> [String: Any] {
        [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: "HingeMini.DirectSupabase", kSecAttrAccount as String: account]
    }
    static func load(account: String) -> String? {
        var q = query(account); q[kSecReturnData as String] = true; q[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: CFTypeRef?
        guard SecItemCopyMatching(q as CFDictionary, &result) == errSecSuccess, let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }
    static func remove(account: String) { SecItemDelete(query(account) as CFDictionary) }
    static func save(_ token: String, account: String) throws {
        remove(account: account)
        var q = query(account); q[kSecValueData as String] = Data(token.utf8)
        q[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        let result = SecItemAdd(q as CFDictionary, nil)
        guard result == errSecSuccess else { throw NSError(domain: NSOSStatusErrorDomain, code: Int(result)) }
    }
}
