# Hinge Mini — direct Supabase iPhone app

Native SwiftUI client, iOS 17+, Xcode 16+. It connects **directly to Supabase over HTTPS**. No Python backend, local server address, API package, or database password is needed by the iPhone app.

## Run on your Mac

1. Open `HingeMini.xcodeproj` in Xcode 16+.
2. Select HingeMini and an iPhone simulator, then Run.
3. Log in with `maya@hinge.test` / `HingeTest2026!`, or create an account with your real email.
4. For new accounts, confirm the email from Supabase before logging in. The project currently requires email confirmation.
5. Use `theo@hinge.test` with the same test password on another device/browser to test matching and chat.

For a physical iPhone, set your development team and a unique bundle identifier in Signing & Capabilities. An internet connection is sufficient; your phone and laptop can be on different Wi-Fi networks. No container or laptop server needs to be running for the installed iOS app.

## Bundled configuration

`HingeMini/Info.plist` includes `HingeSupabaseProjectURL` and `HingeSupabasePublishableKey`. This publishable key is intended for client apps; it does not grant privileged database access. Database passwords and service-role keys are not included. See CONNECTION.md.

## Features and access controls

Supabase Auth handles sign-up, login, token refresh, email confirmation, and logout. Access/refresh tokens are stored in Keychain. PostgreSQL functions derive the acting account from the verified Auth JWT; clients cannot set a sender. Row-level security protects tables, private Storage policies protect photos, and checked RPCs enforce reciprocal matching, unmatching, and blocking.

Profiles, photos, likes with comments, incoming likes, matches, and messages are persistent. Chats poll every 3 seconds and support older history. Messages come only from signed-in accounts. No Standouts, Roses, rankings, or scripted replies.

## Source map

- `Data/BackendSync.swift`: direct Auth, REST RPC, Storage, token refresh, Keychain.
- `Data/AppStore.swift`: UI state and actions.
- `Data/Models.swift`: response models.
- `Components/Cards.swift`: private photo loading and prompt/profile cards.
- `Features/`: Auth, Discover, Likes, Matches/chat, Profile.
- `Theme/Theme.swift`: brand, colors, typography.

## Validation

Direct Auth/REST/Storage integration tests and browser flows run against disposable test users in the configured Supabase project. Static Swift syntax, project references, assets, and plist checks run in Linux. Xcode compilation, simulator, and physical-device validation still require your Mac and remain outstanding.

This is an independent Hinge-inspired MVP. Seeded photos are illustrative; see ASSET_SOURCES.md. Remove known development accounts and add moderation/reporting, recovery/account deletion, monitoring, and a release review before public launch. Old custom-backend accounts/data remain in the private `hinge` schema; they are not automatically migrated into Supabase Auth. The six known development identities were recreated separately for this direct version.
