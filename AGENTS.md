# Project context

Read `PROJECT_MEMORY.md` and `README.md` before changing this project. `PROJECT_MEMORY.md` records current architecture, implemented scope, verification limits, and proposed features. Keep accepted decisions/current state updated there; distinguish proposals from implementation.

Never put credentials, privileged keys, database connection strings, or user tokens into memory files, client code, logs, or distributable ZIPs. Client publishable Supabase settings are intentionally public.

Do not describe static Swift parsing as an Xcode build. The current clients connect directly to Supabase; the legacy Python data API is not required for their operation.
