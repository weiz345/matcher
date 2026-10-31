# Hinge Mini — direct Supabase dating MVP

Web and native SwiftUI clients connect directly to Supabase Auth, PostgreSQL RPCs, and private photo Storage. **The Python API is no longer required.** No advanced filters, Standouts, ranking, or scripted chat replies.

## Try it

The running static web host is at http://10.244.21.93:8000. To host the files yourself:

```sh
python3 scripts/serve_web.py --host 0.0.0.0 --port 8000
```

This process serves only allowlisted public web/download files. All account/data/photo requests go to Supabase over HTTPS. You can deploy those static files to a public static host to use the browser UI across different networks; the private container address itself is not public.

Download `hinge-mini-ios.zip`, open `ios/HingeMini.xcodeproj` in Xcode 16+, and run on an iPhone/simulator. The installed iOS app needs only internet access, with no laptop/container server running. See [iPhone instructions](ios/README.md).

## Accounts

Create an account with a real email and confirm it before login. The current Supabase project requires email confirmation. Development identities are preconfirmed:

`maya@hinge.test`, `theo@hinge.test`, `priya@hinge.test`, `jonah@hinge.test`, `lena@hinge.test`, `marcus@hinge.test`

All use **HingeTest2026!**. Use different accounts on two devices or browser profiles; like a prompt/photo, like back, and exchange messages. Neither seeded users nor the server send automated replies. Unmatching ends access for both participants; blocking also hides photos and profiles. This MVP has no unblock/rematch UI.

Legacy custom-backend records remain untouched in the `hinge` schema. Direct accounts use Supabase Auth and the `dating` schema. Custom passwords cannot be carried over as Supabase passwords; existing real users need a planned migration or new Auth accounts. The six development identities were provisioned separately.

## Configuration and permissions

Public web settings: `supabase-config.js`. iOS settings: `ios/HingeMini/Info.plist`. They contain only the project URL and **publishable** client key. No secret or database password is required on clients.

Server-only `.env` is used for migrations and isolated test-user setup. It is ignored by Git, excluded from the iOS ZIP, and not served. It is not required during normal app use. See [Supabase setup](supabase/README.md) for schema, policies, and deployment details.

## Tests

```sh
# Historical optional Python API / SQLite regression tests
./scripts/test.sh --backend-only

# Actual direct Supabase integration + browser tests (admin test setup requires .env)
./scripts/test.sh

# Swift static checks (Xcode still required for compilation/device checks)
uvx --with tree-sitter --with tree-sitter-swift python scripts/check_ios.py

# Rebuild the downloadable iOS source ZIP
python3 scripts/package_ios.py
```

The seven direct integration cases use real Auth JWTs and test private storage, ownership, matching, message delivery/idempotency, RLS, unmatch/block, and token refresh/revocation. Browser tests use a static-only host and assert zero Python API calls. Disposable test users are created/removed by exact generated IDs; existing profiles and schemas are never reset. First-time Playwright setup: `uvx --with playwright python -m playwright install chromium`.

Legacy backend mutations (`python3 backend/mutation_check.py`) cover the old Python API, not the new SQL RPCs. Do not interpret them as direct-Supabase mutation coverage.

## Limits

This is a local-development MVP with real account boundaries, not a production-ready dating service. Remove known test users before public launch, configure email delivery/redirect URLs, backups, moderation/reporting, password recovery, account deletion, monitoring, and review client/RLS behavior on devices. Auth logout removes local credentials and revokes refresh access; already-issued Supabase access JWTs remain valid until expiry.

Chats poll every 3 seconds; listing limits are 100 profiles/likes/matches and 100 recent messages per match, with older-message pagination. Seeded stock photos are illustrative, not endorsements or actual dating profiles; see [sources](ios/ASSET_SOURCES.md). This is an independent Hinge-inspired prototype.

### Separate image similarity lab

An isolated synthetic-gallery experiment is documented in [image_lab/README.md](image_lab/README.md). It provides uploaded/gallery queries, top-k visual neighbors and same-image perturbation checks on port 8001. It uses no Supabase data and makes no demographic, BMI or identity predictions.
