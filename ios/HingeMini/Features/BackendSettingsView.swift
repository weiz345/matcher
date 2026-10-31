import SwiftUI

struct AuthView: View {
    @Environment(AppStore.self) private var store
    @State private var signup = false
    @State private var email = ""
    @State private var password = ""
    @State private var name = ""
    @State private var age = 27
    var body: some View {
        @Bindable var backend = store.backend
        NavigationStack {
            Form {
                Section {
                    Text(Brand.tagline).font(Theme.serif(30))
                    Picker("Account", selection: $signup) {
                        Text("Log in").tag(false); Text("Create account").tag(true)
                    }.pickerStyle(.segmented)
                    if signup {
                        TextField("Name", text: $name)
                        Stepper("Age: \(age)", value: $age, in: 18...120)
                    }
                    TextField("Email", text: $email).keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never).autocorrectionDisabled().textContentType(.username)
                    SecureField("Password (10+ characters)", text: $password)
                        .textContentType(signup ? .newPassword : .password)
                    Button(signup ? "Create account" : "Log in") {
                        Task {
                            await store.authenticate(signup: signup, email: email, password: password, name: name, age: age)
                            password = ""
                        }
                    }.disabled(store.busy || email.isEmpty || password.count < 10 || (signup && name.isEmpty))
                }
                Section("Supabase") {
                    Text(backend.address).font(.caption).textSelection(.enabled)
                    Text(backend.status).font(.caption)
                    Text("New accounts may require email confirmation before login. No Python server is needed.").font(.footnote)
                }
                Section("Seeded test accounts") {
                    Text("maya@hinge.test · theo@hinge.test · priya@hinge.test · jonah@hinge.test · lena@hinge.test · marcus@hinge.test")
                    Text("Password: HingeTest2026!")
                    Text("Seeded photos are illustrative. There are no automatic messages. Use another signed-in account to reply.")
                }.font(.footnote).foregroundStyle(Theme.secondary)
            }.navigationTitle(Brand.name)
        }
    }
}
