#!/usr/bin/env python3
"""Save a Supabase DB connection URI privately. Input is hidden; no secret is printed."""
import getpass
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit,parse_qsl,urlencode,urlunsplit

root=Path(__file__).resolve().parent.parent
value=getpass.getpass('Paste the full Supabase Session pooler URI (hidden): ').strip()
parsed=urlsplit(value)
if parsed.scheme not in ('postgres','postgresql') or not parsed.hostname or not parsed.username or not parsed.password:
    raise SystemExit('Expected a full PostgreSQL URI with username and password; nothing saved.')
if parsed.port==6543: raise SystemExit('Use the Session pooler on port 5432, not the transaction pooler.')
if any(c in value for c in ('\n','\r')) or 'YOUR_PASSWORD' in value or 'URL_ENCODED_PASSWORD' in value:
    raise SystemExit('Replace placeholders with the real, URL-encoded password; nothing saved.')
query=dict(parse_qsl(parsed.query));query['sslmode']='require'
value=urlunsplit(parsed._replace(query=urlencode(query)))
path=root/'.env'
lines=path.read_text().splitlines() if path.exists() else []
lines=[line for line in lines if not line.strip().startswith('HINGE_DATABASE_URL=')]
lines.append('HINGE_DATABASE_URL='+value)
fd,temp=tempfile.mkstemp(prefix='.env-',dir=root)
try:
    os.fchmod(fd,0o600)
    with os.fdopen(fd,'w') as output: output.write('\n'.join(lines)+'\n')
    os.replace(temp,path)
finally:
    if os.path.exists(temp): os.unlink(temp)
print('Saved .env with owner-only permissions. No database changes have been made.')
