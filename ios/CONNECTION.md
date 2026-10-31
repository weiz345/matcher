# Direct Supabase connection

Project URL: **https://izwszmyuzxmmgchguvao.supabase.co**

The publishable key and project URL are bundled in `HingeMini/Info.plist`. No additional setup is needed to point this copy of the app at the configured project.

**iPhone / simulator → Supabase Auth + PostgreSQL RPC + private Storage**

There is no intermediate Python API. The installed app works over the internet on different Wi-Fi networks, without the container or laptop running. The browser version needs only static hosting for its HTML/JavaScript files; its data requests also go directly to Supabase.

Supabase Auth validates sessions. Database functions and row-level security enforce access. Photos live in the private `dating-photos` bucket and are downloaded with the signed-in user's token. No database password or service-role key is included in this archive. The public publishable key alone cannot read private user data.

Test accounts: `maya@hinge.test`, `theo@hinge.test`, `priya@hinge.test`, `jonah@hinge.test`, `lena@hinge.test`, `marcus@hinge.test`. Shared development password: `HingeTest2026!`. New accounts require email confirmation in the current project configuration.

The server-only `.env` is used for admin migrations/test fixture setup, not by the iOS app. Rotating that database password does not require rebuilding or changing the app.
