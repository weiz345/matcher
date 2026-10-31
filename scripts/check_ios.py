"""Static Swift syntax/project check; does not replace Xcode compilation.
Run: uvx --with tree-sitter --with tree-sitter-swift python scripts/check_ios.py
"""
from pathlib import Path
import json
import plistlib
import re
import xml.etree.ElementTree as ET
from tree_sitter import Language, Parser
import tree_sitter_swift
root = Path(__file__).resolve().parent.parent / 'ios'
parser = Parser(Language(tree_sitter_swift.language()))
files = list((root/'HingeMini').rglob('*.swift'))
for file in files:
    tree = parser.parse(file.read_bytes())
    assert not tree.root_node.has_error, f'Swift syntax errors in {file}'
    assert len(file.read_text().splitlines()) < 300, file
project = (root/'HingeMini.xcodeproj/project.pbxproj').read_text()
for file in files: assert file.relative_to(root/'HingeMini').as_posix() in project, file
ids = set(re.findall(r'^([A-F0-9]{24}) =',project,re.M))
assert set(re.findall(r'\b[A-F0-9]{24}\b',project)) <= ids
for file in root.rglob('Contents.json'): json.loads(file.read_text())
plistlib.loads((root/'HingeMini/Info.plist').read_bytes())
ET.parse(root/'HingeMini.xcodeproj/xcshareddata/xcschemes/HingeMini.xcscheme')
print(f'PASS: {len(files)} Swift files parse; project references, scheme, plist, and asset manifests are valid.')
print('Xcode compilation / simulator tests still required on macOS.')
