# Direct Supabase setup

The app now calls Supabase directly. It uses **Supabase Auth**, checked PostgreSQL RPCs with row-level security, and the private **dating-photos** Storage bucket. Python is optional legacy code, not a runtime dependency of the clients.

## Configured project

Project: `https://izwszmyuzxmmgchguvao.supabase.co`

Public URL/publishable key: `supabase-config.js` for web; `ios/HingeMini/Info.plist` for iOS. Publishable keys are intended to ship in clients; they require user authentication and access policies. Never put a database URI, password, secret key, or service-role key in a client.

## Database deployment

`migrations/20261030_direct_clients.sql` and `migrations/20261031_photo_access.sql` were applied to this project. It creates only the new `dating` schema, public `dating_*` RPCs, a profile trigger on new Auth users, Storage bucket, and explicitly named policies. Legacy private `hinge` tables are untouched. Apply both migrations in filename order via the SQL editor or a server-side psycopg connection to set up another project. Also change both clients' public settings.

- `dating.profiles/prompts/photos`: own profile and photo metadata.
- `dating.likes`: per-item likes and comments; sender is auth.uid().
- `dating.conversations/messages`: reciprocal pairs and persisted messages; users may read/send only in an active conversation they belong to.
- `dating.blocks/passes`: visibility and discovery state.
- `public.dating_bootstrap`: bounded account/discovery/likes/matches snapshot.
- `public.dating_action`: validated transactional mutations; serializes writes for this small MVP.
- `public.dating_messages`: participant-checked cursor pagination.
- `public.dating_photo`: visible photo path metadata.

Tables have RLS enabled. `authenticated` can SELECT only allowed rows and cannot write tables directly. Anonymous users cannot execute the RPCs. SECURITY DEFINER helpers have an empty search path and qualified table names; helpers accepting arbitrary profile IDs are not granted to clients. Public RPCs always derive identity from auth.uid() and never accept an acting account ID.

Keep `dating` out of exposed Data API schemas (only public RPC wrappers are needed). Do not grant anonymous/private-schema table writes or remove the policies. Existing policies in an unrelated application should be reviewed if sharing the same project/bucket.

## Photos

Storage bucket `dating-photos` is private, max 3 MB per JPEG/PNG. Path: `AUTH_USER_UUID/PHOTO_UUID`. Clients upload with their JWT, register the uploaded object through a validated RPC, and fetch via authenticated Storage. Owners can remove their files; blocked users cannot fetch each other's photos. Storage authorization uses a per-request check; new uploads use zero cache lifetime and clients revalidate downloads. Files already downloaded cannot be recalled from a device. Clients clean up objects when metadata registration fails or on deletion; operational orphan cleanup is a future improvement.

## Auth and test identities

The project requires email confirmation. New accounts receive Supabase's confirmation email; login works after confirmation. Configure production SMTP and Site URL/redirect allowlist in Supabase before public deployment. No app-generated invitation/verification email is sent by the fixture tests.

`seed_direct.py` explicitly provisions only the six requested development identities through the server-side database connection and uploads their bundled illustrative photos through user-authenticated Storage. It does not reset existing users/passwords. These preconfirmed fixtures are for development only; remove them before launch. Other legacy custom accounts/messages are not copied into Supabase Auth or `dating` automatically.

Clients persist refresh/access sessions (Keychain on iOS, localStorage in web) and refresh expiring tokens. Sign-out clears the local session and revokes that session's refresh access; access JWTs already issued remain valid until expiry. Never treat a client-side sign-out as immediate JWT revocation.

## Tests and admin credentials

Migrations and test fixture creation use `HINGE_DATABASE_URL` from the private root `.env`. Use the Session pooler URI on port 5432 with SSL. This is an admin/setup credential only; regular app operation needs no DB URI or Python server.

```sh
uvx --with 'psycopg[binary]>=3.2,<4' python supabase/test_direct.py
uvx --with playwright --with 'psycopg[binary]>=3.2,<4' python supabase/browser_smoke.py
```

Tests create uniquely named temporary Auth users, then perform application requests using those users' JWTs and public key. One check impersonates a regular authenticated SQL role to verify RLS and denied direct writes. Cleanup removes only exact generated test IDs and their data, never resets a schema or touches existing users. Do not run tests on a production project without operational review.

Old PostgreSQL-only adapter tests and Python API mutation checks remain available for the optional legacy backend, but do not test these direct-client RPCs. Supabase hosting includes data/Auth/Storage; web HTML/JS still needs static hosting. The installed native app needs no separately hosted server.
