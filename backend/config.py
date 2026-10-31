"""Load the optional local .env without executing shell code or overriding the process environment."""
import os
from pathlib import Path

def load_env(path=None):
    path=Path(path) if path else Path(__file__).resolve().parent.parent/'.env'
    if not path.exists(): return
    for line in path.read_text().splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        key,value=line.split('=',1);key=key.strip();value=value.strip()
        if key not in ('HINGE_DATABASE_URL',): continue
        if len(value)>=2 and value[0]==value[-1] and value[0] in ('"',"'"): value=value[1:-1]
        os.environ.setdefault(key,value)
