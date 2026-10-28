"""Verify saved I1 evidence without starting services or changing source files."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
result = json.loads((OUT / 'browser-results.json').read_text())
assert not result.get('fatal'), result.get('fatal')
assert result['services_stopped']
assert all(check['passed'] for check in result['checks'])
assert not [e for e in result['errors'] if 'message' in e], 'JavaScript page exceptions'
assert not [s for s in result['screenshots'] if not s['source_rendered']]
assert not [s for s in result['screenshots'] if s.get('brokenImages')], 'Broken image assets'
for theme in ['dark', 'light']:
    for width in [1920, 1440, 1280, 768, 390]:
        for screen in ['landing', 'login', 'register', 'workspace', 'new', 'library', 'compare', 'settings']:
            name = f'{theme}-{width}-{screen}.png'
            entry = next(s for s in result['screenshots'] if s['file'] == name)
            assert entry['theme'] == theme, name
            assert entry['viewport']['width'] == width, name
            assert (OUT / name).read_bytes().startswith(b'\x89PNG\r\n\x1a\n'), name
manifest = json.loads((OUT / 'source-manifest.json').read_text())
for entry in manifest:
    actual = (ROOT / entry['file']).read_bytes()
    assert hashlib.sha256(actual).hexdigest() == entry['sha256'], entry['file']
    base = subprocess.check_output(['git', 'show', 'f89093e:' + entry['file']], cwd=ROOT)
    assert actual == base, entry['file']
files = {entry['file']: hashlib.sha256((OUT / entry['file']).read_bytes()).hexdigest()
         for entry in result['screenshots']}
(OUT / 'screenshot-sha256.json').write_text(json.dumps(files, indent=2) + '\n')
print(f"PASS: {len(files)} screenshot hashes; 80 correct viewport/theme states; "
      f"{len(result['checks'])} browser checks; {len(manifest)} unchanged source/config/asset files.")
print('PASS: zero JavaScript page exceptions, no broken image assets, owned services stopped.')
print('Existing overflow is a documented observation, not an evidence-verification failure.')
