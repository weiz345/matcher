# Account-based SQLite API

Start `python3 backend/server.py` from the project root. Database defaults to `~/.local/share/hinge-mini/app.sqlite3`; pass `--db PATH` to change it. The server serves the web client and API on port 8000. Do not use `python -m http.server`.

## Authentication

`POST /api/signup` accepts `{email,password,name,age}`. `POST /api/login` accepts `{email,password}`. Both return `{token,app}` and set an HttpOnly SameSite cookie. Native clients use `Authorization: Bearer TOKEN`, stored in Keychain; browser code uses the cookie. `POST /api/logout` with `{}` revokes the current session. Session lifetime: 30 days. Password minimum: 10 characters; adults only. Seeded test accounts and passwords are in the root README.

All endpoints below require authentication. Mutations accept JSON unless DELETE; responses contain `{app, ...}` with updated account state. Every write is transactional. API errors use `{error}` and an appropriate HTTP status; inaccessible profiles/conversations return 404. Cross-origin browser writes are rejected. Login/sign-up are throttled to 20 attempts per IP/email per minute (process-local).

## API

- `GET /api/app`: own profile, discovery (up to 100), incoming likes (up to 100), active matches (up to 100), and each match's latest 100 messages.
- `PUT /api/profile`: `{name,age,location,job,height,prompts:[{id?,title,answer}]}`. Requires 1–3 prompts; IDs are assigned by the server for new prompts. Only the signed-in account is changed.
- `POST /api/photos`: `{data:BASE64_JPEG_OR_PNG}` up to 3 MB decoded, 6 photos per account. Photos are stored as SQLite BLOBs. Clients downscale to 1200 pixels.
- `GET /api/photos/ID`: authenticated image response, denied across blocks.
- `DELETE /api/photos/ID`: owner only.
- `POST /api/likes`: `{target,itemType:"photo"|"prompt",itemID,comment?}`. Item must belong to target. Returns `matchID` when reciprocal likes produce an active conversation. A duplicate like is idempotent.
- `POST /api/likes/USER_ID/accept`: `{}`; creates reciprocal like and match. Requires an existing incoming like.
- `POST /api/pass`: `{target}`. Hides a discoverable person / incoming like.
- `DELETE /api/passes`: revisits passed profiles, without reopening ended matches.
- `GET /api/conversations/ID/messages?before=MESSAGE_ID`: up to 100 messages older than cursor, in chronological order. Omit cursor for newest messages.
- `POST /api/conversations/ID/messages`: `{text,clientID}`. Text 1–1000 characters. `clientID` is a per-message UUID; retries with the same ID cannot duplicate a message. Only active-match participants may read or send.
- `DELETE /api/conversations/ID`: unmatch; both users lose access. Ended pairs cannot rematch in this MVP.
- `POST /api/blocks`: `{target}`. Hides accounts in both directions, removes likes, ends any match, and revokes conversation/photo access across the block.
- `GET /api/health`: public health check.

Clients poll `/api/app` every 3 seconds while active. Messages originate only from authenticated sender accounts; clients cannot set another sender. There is no WebSocket/push transport or automatic response. No Standouts, Roses, or ranking.

## Tables and upgrade

`accounts`, `auth_sessions`, `photos`, `prompts`, `user_likes`, `conversations`, `chat_messages`, `user_blocks`, `passes`. Foreign keys enforce ownership links; unique pair and message keys prevent duplicate matches/messages. Session tokens and passwords are never stored in plaintext.

Legacy `sessions`, `documents`, and `profiles` tables from the snapshot prototype are left intact, unused. `/api/state`, `/api/session`, and `/api/catalog` have been removed. Old anonymous snapshots are not imported as accounts. New account tables are created idempotently, and existing accounts are not overwritten on restart.

Use a persistent volume for the database directory. For a live backup use Python's `sqlite3.Connection.backup()`; copying only the .sqlite3 file while the server is running may miss WAL changes. Restore a backup to a test environment periodically.

## Verification and limits

Run `./scripts/test.sh` from the root; see README for Playwright setup. Tests create independent temporary databases and never reset your running database.

Local development server: no TLS, email verification, password recovery, account deletion, reporting/moderation, durable distributed throttling, or production hosting hardening. Use HTTPS, `--secure-cookies`, proper volumes/backups, and remove known test accounts before deployment. Limits on discovery and active matches are intended for this small MVP; a larger service needs full pagination and a dedicated database/deployment design. iOS still needs Xcode/device testing.

Focused mutation checks (isolated source copies, no live database changes):

```sh
python3 backend/mutation_check.py
```

The eight selected mutations remove conversation membership/active checks, block visibility, password verification, reciprocal-like requirements, photo deletion ownership, idempotent message insertion, and liked-item ownership. The runner verifies an unmodified baseline before each mutant and requires an assertion failure to count it as detected. This is targeted mutation testing, not exhaustive mutation coverage.

## Supabase/PostgreSQL

Set `HINGE_DATABASE_URL` in `.env` or the server environment to enable PostgreSQL, and install `requirements-postgres.txt` (or use `./scripts/start_server.sh`). Health reports `postgresql`. See `../supabase/README.md` for setup and validation. The app's auth and API remain in Python; Supabase Auth/Storage/Realtime are not used. Data lives in a private `hinge` schema. PostgreSQL test accounts require explicit `--seed-test-accounts`; SQLite continues to seed by default. Existing SQLite data is not copied automatically.
