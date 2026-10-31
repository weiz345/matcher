"""Create the iOS source archive, including public connection settings, excluding secrets."""
from pathlib import Path
import plistlib
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parent.parent
source = root / 'ios'
settings = plistlib.loads((source/'HingeMini/Info.plist').read_bytes())
assert settings.get('HingeSupabasePublishableKey')
assert settings.get('HingeSupabaseProjectURL')
files = [p for p in sorted(source.rglob('*')) if p.is_file() and
         not any(part.startswith('.') or part == '__pycache__' for part in p.relative_to(source).parts) and
         p.suffix not in ('.p12', '.p8', '.key', '.sqlite3', '.pyc')]
# Fail rather than silently package private database connection strings.
for path in files:
    data = path.read_bytes()
    assert b'postgresql://' not in data and b'postgres://' not in data, f'Database URI found in {path.name}'
with ZipFile(root/'hinge-mini-ios.zip', 'w', ZIP_DEFLATED) as archive:
    for path in files: archive.write(path, path.relative_to(root))
print(f'Packaged {len(files)} files with public connection settings. Server secrets excluded.')
