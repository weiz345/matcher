# Hinge Mini project memory

This is durable project context, not a transcript or secret store. Read it alongside README.md and the current code. Verify running processes/URLs before reporting availability. New feature ideas below are not implemented or approved product decisions.

## User intent and working preferences

- Build a minimal Hinge-inspired dating app, initially web and then native SwiftUI for iPhone.
- The user wants communication between real accounts on laptop and phone, including different Wi-Fi networks.
- Prefer action, runnable local tests, clear status, and easy-to-download iOS source ZIPs.
- The user explicitly requested preserving project context and the roadmap in memory.
- Applicable user-supplied Perforce operational instructions still apply if any Perforce operation is needed; none is required for this standalone project.

## Location, architecture, and artifacts

- Project root: `/home/zhengw/hinge-mini` in a Linux container.
- Current clients connect DIRECTLY to hosted Supabase Auth, PostgreSQL RPCs, and private Storage over HTTPS.
- Public project URL: `https://izwszmyuzxmmgchguvao.supabase.co`.
- Web public configuration: `supabase-config.js`; transport/session logic: `supabase-client.js`; UI: `app.js`, `index.html`, `style.css`.
- iPhone source: `ios/HingeMini.xcodeproj`; target iOS 17+, Xcode 16+; no third-party Swift packages.
- iOS direct transport, session refresh, and Keychain logic: `ios/HingeMini/Data/BackendSync.swift`.
- iOS public project URL and publishable key are bundled in `ios/HingeMini/Info.plist`. No backend address or database password belongs in the app.
- iOS ZIP: `hinge-mini-ios.zip`; rebuild with `python3 scripts/package_ios.py`.
- Last configured web/download URL: `http://10.244.21.93:8000`; ZIP at `/hinge-mini-ios.zip`. This private container address is not public across Wi-Fi networks.
- `python3 scripts/serve_web.py` serves only allowlisted static files/downloads, never `.env` or backend code. The Python DATA API was stopped when direct clients were enabled.
- The installed native app needs only internet and Supabase; it does not need the laptop/container running. Web files still need static hosting; use a public static host for cross-network browser access.
- The ZIP is SOURCE for an iPhone app, opened in Xcode and run in an iPhone simulator/on a device. It is not a double-clickable native macOS app, compiled IPA, or signed release.

## Implemented product scope

- Supabase Auth signup/login, email confirmation handling, session refresh, local logout.
- Persistent profiles/prompts and private photo upload/download/deletion.
- Likes on specific photos/prompts with optional comments; incoming likes; reciprocal likes create one match.
- Persistent messaging between actual signed-in matched accounts, polling every 3 seconds, older-message pagination.
- Basic unmatching and blocking, including access checks on conversations and photos.
- Six preconfirmed development accounts: maya/theo/priya/jonah/lena/marcus at `hinge.test`. Test credentials are documented in README.md, not repeated here.
- Development profiles use bundled illustrative stock photos, not verified identities. See `ios/ASSET_SOURCES.md`.
- No scripted replies, Standouts, Roses, advanced filters, or ranking scores.
- Unmatching is terminal for that pair in the MVP; no unblock/rematch UI.

## Supabase implementation and security boundaries

- Direct tables in `dating`: profiles, prompts, photos, likes, conversations, messages, blocks, passes.
- Public RPCs: `dating_bootstrap`, `dating_action`, `dating_messages`, `dating_photo`.
- Identity derives from verified `auth.uid()`, not supplied sender IDs. RPCs check ownership, mutual matching, active membership, and blocks.
- RLS enabled; authenticated users can SELECT only allowed rows, not directly mutate tables. Anonymous callers cannot use these RPCs. Private helpers have restricted grants and qualified names/empty search paths.
- Private bucket `dating-photos`; JPEG/PNG, max 3 MB; up to 6 profile photos; object paths are `AUTH_USER_UUID/PHOTO_UUID`.
- Applied migrations: `supabase/migrations/20261030_direct_clients.sql` and `20261031_photo_access.sql`.
- Photo access was hardened with a per-request authorization check after an additional known-URL regression test; uploads use zero cache lifetime and clients revalidate downloads. Previously downloaded copies cannot be recalled.
- Signup currently REQUIRES email confirmation (`mailer_autoconfirm=false`). Proper production sender/SMTP, redirect/deep links, resend UX, recovery, and delivery testing still need work.
- iOS credentials/tokens use Keychain; web sessions use localStorage. Publishable client keys are public; privileged credentials must remain server-side.
- Supabase sign-out revokes refresh access and clears local state; existing access JWTs remain valid until expiry.
- `.env` holds the server-only DB URI for admin migrations/test setup, not app runtime. Never print/package it or store its contents in memory. A DB password was exposed in chat earlier; rotation was advised but completion has not been verified.

## Historical implementation and migration limits

- Original demo used browser localStorage, then SQLite session snapshots, then an account-based Python/SQLite API.
- The optional legacy Python API later supported Supabase PostgreSQL through `backend/storage.py` and `HINGE_DATABASE_URL`.
- Legacy SQLite path: `~/.local/share/hinge-mini/app.sqlite3`; legacy hosted custom-auth data in private `hinge` schema. Both were left intact.
- The direct version uses new Supabase Auth identities/`dating` data; it does not automatically migrate arbitrary legacy passwords, profiles, or messages. The six development identities were recreated for direct Auth.
- Do not restore old instructions telling users to enter a Python backend URL in the current iOS app.

## Tests, verification, and limitations

- `./scripts/test.sh --backend-only`: 11 legacy account/SQLite API regressions.
- `./scripts/test.sh`: legacy regressions plus current direct integration and browser tests.
- Current direct integration suite: `supabase/test_direct.py`, seven real Auth/REST/Storage/RLS cases. Uses user JWTs for tested actions; admin DB access only provisions/cleans exact disposable user IDs.
- Current direct browser suite: `supabase/browser_smoke.py`; static-only host, two-person matching/messages, refresh, private photos, persistence, unmatch/block, logout/mobile layout. Asserts ZERO Python API requests.
- Final direct integration and browser reruns passed after photo authorization hardening. Swift static checks passed.
- `python3 backend/mutation_check.py`: eight selected mutations caught in the OLD Python API. This is NOT mutation coverage of new Supabase SQL/RLS.
- `uvx --with tree-sitter --with tree-sitter-swift python scripts/check_ios.py`: syntax/project/plist/assets checks only.
- iOS has NOT been compiled/tested in Xcode or on a physical device in this Linux workspace. State this clearly; static parsing is not compilation.
- Do not reset hosted schemas or existing users for tests. Fixture cleanup must target only generated IDs and owned Storage files. Browser test selection must use account IDs, since simultaneous fixtures may share display names.
- Current listing limits: 100 discovery profiles/likes/matches, 100 recent messages per match plus older-history cursor.
- Production gaps include reporting/moderation, recovery/account deletion, SMTP/redirects, operational monitoring/backups, removal of known test accounts, orphan object cleanup, and release/device review.

## Latest requested roadmap — not implemented

1. **Proper email signup**: user wants production-quality email signup. Email confirmation already exists; assess SMTP/domain authentication, confirmation/resend screens, iOS universal/deep links, password recovery, and abuse controls. Do not claim SMTP or end-to-end email delivery has been verified.
2. **Photo verification**: user asks about adding it. Clarify the badge's meaning. Candidate MVP: consented selfie submission with human review; stronger option: third-party liveness/verification provider comparing a user's own selfie/profile. Never let clients self-set verified status. Invalidate verification on relevant photo replacement. Provider onboarding/device testing adds calendar time.
3. **Image-based similarity filter/sort**: user asks how to implement and how long, not yet an instruction to build. Clarify whether they mean general visual style or another similarity criterion. A proposed non-identifying implementation uses general visual embeddings, pgvector, and a checked search RPC/Edge Function, returning only eligible unblocked profiles. Respect opt-in, minimize upload retention, delete embeddings with photos/accounts, and avoid exposing embeddings/global private image search to clients. Do not silently implement facial identification or sensitive-trait inference.
4. **One per person?**: likely asks about account policy; confirm that interpretation if implementing. Recommendation under discussion: one active dating profile per person, multiple photos per profile. One verified email is not proof of one human. Phone verification can reduce duplication but has recycled/shared-number and recovery tradeoffs. No one-person policy has been implemented or accepted yet.

## Estimates discussed as planning ranges, not guarantees

- Proper email signup hardening on existing Supabase Auth: approximately 1–2 focused days, plus external DNS/email delivery verification.
- Manual selfie review flow: approximately 1–3 days. Third-party liveness provider integration: approximately 3–7 development days plus provider approval/device testing.
- General visual-style similarity prototype: approximately 2–4 days; usable web+iOS feature with access controls, cleanup, and relevance testing: approximately 1–2 weeks.
- One-active-profile/verified-phone controls: approximately 1–3 days once policy/provider and recovery behavior are decided. Perfect unique-human enforcement is not guaranteed by email/phone.
- These estimates assume the current codebase, available provider access, and testing time; do not treat them as promised completion times or accepted feature scope.

## Separate synthetic visual-similarity lab (2026-10-30)

Implemented isolated `image_lab/` with downloadable SFHQ synthetic samples, CLIP ViT-B/32 quantized ONNX CPU embeddings, cosine top-k search, upload/gallery queries and local browser UI. Server currently at `http://10.244.21.93:8001`; launch with `./scripts/start_image_lab.sh --host 0.0.0.0 --port 8001`. Existing dating app remains port 8000. No Supabase/account integration or uploaded-query disk persistence. Local dev server has no authentication and is intended for trusted-network research.

Downloaded two checksummed sample archives (700 + 750), yielding 1,450 distinct image file hashes. Model ~89 MB; total local data ~392 MB. Not a full large-scale corpus. Data/model/index ignored by Git. Download, build, evaluation, test commands and provenance in `image_lab/README.md`. Dataset includes varied apparent ages; never treat this as adult dating-profile seed data.

Implemented baseline center crop versus averaged original/mirror/inner84% crop representations, selectable query mirror/80% crop/12-degree rotation. No ethnicity/gender/BMI/body-frame labels, inference or filtering. General visual resemblance, not face identity confidence. Demographic preferences require supplied profile fields; face photos do not reliably determine BMI/body frame. Genuine cross-camera-angle robustness remains untested and requires a consented/synthetic grouped multi-view dataset.

Verification: 1,450-image index built in 91.9 seconds CPU. Three references × four same-image transforms × two representations: original image ranked first in every check; this is only a sanity check, not pose or demographic validation. API integration checks passed (top-k order/count, self exclusion/retrieval, file upload, invalid inputs, origin/path restrictions). Playwright Chromium passed gallery/image loads, top-k and flip searches, evaluation display, upload and 390px mobile overflow check, no JS errors. Desktop screenshot visually reviewed. Tests: `python3 image_lab/test_lab.py`; `uvx --with playwright python image_lab/test_browser.py` against running lab. No dating-app or Supabase changes required.

Image lab progress display: added persistent progress bar, count/percentage, elapsed duration, throughput and ETA refreshed every 2s. Builder atomically writes batch progress and loading/saving/complete/failure phases, plus terminal percentage/rate/ETA; completed elapsed time includes model initialization and saving for new builds. Existing run remains 91.9s for embedding 1,450 images. Download duration is separate. API checks and Chromium UI tests passed; UI test additionally verifies simulated 25% progress/75s ETA and real completed state. Full index was not rebuilt for this presentation change.
