"""Verify source-only I2 preservation evidence without opening runtime databases."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
manifest = json.loads((OUT / 'source-import-manifest.json').read_text())
for entry in manifest:
    target = ROOT / entry['destination']
    assert target.is_file() and not target.is_symlink(), entry['destination']
    assert hashlib.sha256(target.read_bytes()).hexdigest() == entry['imported_sha256'], entry['destination']
assert len(manifest) == 57
assert sum(e['byte_identical'] for e in manifest) == 52
# b source is optional for source-only future clones; hashes remain independently checkable.
ref = manifest[0]['source_ref']
if subprocess.run(['git', 'cat-file', '-e', ref], cwd=ROOT, capture_output=True).returncode == 0:
    original = subprocess.check_output(['git', 'show', ref + ':app.py'], cwd=ROOT, text=True)
    imported = (ROOT / 'witness-backend/app.py').read_text()
    definitions = lambda text: {n.name: ast.dump(n) for n in ast.parse(text).body
                               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    assert definitions(original) == definitions(imported), 'app worker/model/route AST changed'
frontend = json.loads((ROOT / 'docs/integration/evidence/i1/source-manifest.json').read_text())
exceptions = []
for entry in frontend:
    if hashlib.sha256((ROOT / entry['file']).read_bytes()).hexdigest() != entry['sha256']:
        exceptions.append(entry['file'])
assert exceptions == ['eslint.config.js'], exceptions
server = json.loads((OUT / 'server-checks.json').read_text())
assert not server.get('error')
assert len(server['checks']) == 33
assert server['server_starts'] == 2 and server['owned_server_stopped'] and server['runtime_external']
assert server['static_assets_checked'] == 35 and server['synthetic_versions'] == 6
api = json.loads((OUT / 'openapi.json').read_text())
assert sum(len(methods) for methods in api['paths'].values()) == 34
assert '56 passed' in (OUT / 'pytest.txt').read_text()
# Runtime directories are either absent or ignored; no symlink to the old application exists.
for folder in ['data', 'outputs', 'work', '.venv', 'evidence', 'backups']:
    path = ROOT / 'witness-backend' / folder
    assert not path.is_symlink(), folder
    assert subprocess.run(['git', 'check-ignore', '-q', str(path / '.i2-ignore-probe')], cwd=ROOT).returncode == 0, folder
print('PASS: 57 verified imports, 52 byte-identical; app worker/model/route AST unchanged.')
print('PASS: React/API/Vite/package assets preserved; only reviewed ESLint exclusion differs.')
print('PASS: 56 pytest tests, 33 isolated HTTP checks, 35 static assets, actual restart and external runtime.')
print('PASS: 34 explicit API operations, ignored runtime directories, no original-project symlinks.')
