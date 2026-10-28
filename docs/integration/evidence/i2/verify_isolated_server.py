"""HTTP verification of preserved backend on 8022 with disposable synthetic data.
All generation here uses an explicit fake CLI fixture, never the user's real Codex.
"""
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid

import httpx
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[4]
BACKEND = ROOT / 'witness-backend'
OUT = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:8022'
RESULT = {'mode': 'synthetic fake-CLI HTTP verification; no live AI generation', 'checks': [],
          'response_shapes': {}, 'port': 8022, 'server_starts': 0}


def checked(name, condition):
    assert condition, name
    RESULT['checks'].append(name)
    print('PASS ' + name, flush=True)


def shape(value):
    if isinstance(value, dict):
        return {'type': 'object', 'keys': sorted(value)}
    if isinstance(value, list):
        return {'type': 'array', 'item': shape(value[0]) if value else None}
    return {'type': type(value).__name__}


def api(method, path, body=None, status=200, raw=False):
    response = httpx.request(method, BASE + path, json=body, timeout=30)
    assert response.status_code == status, (method, path, response.status_code)
    if response.headers.get('content-type', '').startswith('application/json'):
        value = response.json()
        # Record contracts without storing fixture records or prompt payloads.
        RESULT['response_shapes'][method + ' ' + path] = shape(value)
        return response if raw else value
    return response


def data_url(data):
    return 'data:image/png;base64,' + base64.b64encode(data).decode()


def completed(handle):
    for _ in range(160):
        result = api('GET', '/api/jobs/' + handle['job_id'])
        if result['status'] != 'working':
            checked('validated fake-CLI job completed', result['status'] == 'complete' and bool(result['image_url']))
            return result
        time.sleep(.05)
    raise AssertionError('isolated fixture job timed out')


def main():
    with socket.socket() as sock:
        if sock.connect_ex(('127.0.0.1', 8022)) == 0:
            raise RuntimeError('Refusing to disturb an occupied 8022 listener')
    process = None
    with tempfile.TemporaryDirectory(prefix='witnesstrace-i2-') as runtime:
        runtime = Path(runtime)
        runtime.chmod(0o700)
        fake = runtime / 'fake-codex'
        fake.write_text(f'''#!{sys.executable}
import os,sys,time
from pathlib import Path
from PIL import Image,ImageDraw
_ = sys.stdin.read()
time.sleep(.08)
p = Path(os.environ['CODEX_HOME'])/'generated_images'/'fixture.png'
p.parent.mkdir(parents=True,exist_ok=True)
im=Image.new('RGB',(512,512),'white');d=ImageDraw.Draw(im)
for box,color in [((0,0,255,255),'#557799'),((256,0,511,255),'#997755'),((0,256,255,511),'#559977'),((256,256,511,511),'#775599')]:d.rectangle(box,fill=color)
for x in range(0,512,16):d.line((x,0,511-x,511),fill='white',width=2)
im.save(p)
print('Explicit synthetic fake-CLI fixture, not AI output')
''')
        fake.chmod(0o700)
        env = os.environ.copy()
        env.update(WITNESSTRACE_DATA_DIR=str(runtime / 'data'),
                   WITNESSTRACE_OUTPUTS_DIR=str(runtime / 'outputs'),
                   WITNESSTRACE_WORK_DIR=str(runtime / 'work'),
                   CODEX_HOME=str(runtime / 'fake-cli-home'), CODEX_BIN=str(fake))
        env.pop('WITNESSTRACE_PORT', None)  # Exercise the launcher's safe default 8022.
        log = open(runtime / 'server.log', 'w')

        def start():
            nonlocal process
            # Deliberately launch from a different cwd; start.sh owns app-dir resolution.
            process = subprocess.Popen([str(BACKEND / 'start.sh')], cwd=runtime, env=env, stdout=log, stderr=log)
            RESULT['server_starts'] += 1
            for _ in range(120):
                if process.poll() is not None:
                    raise RuntimeError('Isolated server exited during startup')
                try:
                    if httpx.get(BASE + '/api/health', timeout=.5).status_code == 200:
                        return
                except httpx.HTTPError:
                    pass
                time.sleep(.1)
            raise RuntimeError('Isolated server startup timeout')

        def stop():
            if process and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()

        try:
            start()
            checked('launcher starts independently on its default 8022', True)
            health = api('GET', '/api/health')
            checked('health states tool availability caveat', 'real generation' in health['message'])
            checked('isolated store starts empty', api('GET', '/api/cases') == [])
            page = api('GET', '/')
            checked('standalone preserved workbench HTML served', 'sketch-canvas' in page.text and 'panel-enhance' in page.text)
            assets = [p for p in (BACKEND / 'static').rglob('*') if p.is_file()]
            for asset in assets:
                response = httpx.get(BASE + '/static/' + asset.relative_to(BACKEND / 'static').as_posix(), timeout=10)
                assert response.status_code == 200
                assert hashlib.sha256(response.content).digest() == hashlib.sha256(asset.read_bytes()).digest()
            checked('all preserved static/icon/worker assets byte-identical over HTTP', bool(assets))
            RESULT['static_assets_checked'] = len(assets)
            schema = api('GET', '/api/lab-schema')
            checked('45 Character Lab fields in seven groups', len(schema['groups']) == 7 and sum(len(g['fields']) for g in schema['groups']) == 45)
            enhancements = api('GET', '/api/enhance-schema')
            checked('actual enhancement controls and presets', len(enhancements['controls']) == 11 and len(enhancements['presets']) == 5)
            case = api('POST', '/api/cases', {'title': 'I2 entirely synthetic HTTP case', 'synthetic': True}, 201)
            other = api('POST', '/api/cases', {'title': 'I2 separate synthetic isolation case', 'synthetic': True}, 201)
            cid = case['id']
            prefix = '/api/cases/' + cid
            original = '  Entirely fictional adult with short dark hair. Eye color and age are unknown.\n  '
            draft = case['draft']
            draft['lab']['face_width'] = {'value': '60', 'confidence': 'tentative', 'source': 'operator', 'quote': ''}
            draft['attributes']['hair'] = {'value': 'Black', 'confidence': 'tentative', 'source': 'witness', 'quote': 'dark hair'}
            case = api('PUT', prefix, {'revision': case['revision'], 'original': original, 'draft': draft})
            case = api('POST', prefix + '/freeze', {'revision': case['revision'], 'text': original})
            checked('exact original testimony frozen with Unknown/source/uncertainty preserved',
                    case['statements'][0]['text'] == original and case['frozen_at'] and
                    case['draft']['attributes']['eyes']['value'] is None and
                    case['draft']['lab']['face_width']['confidence'] == 'tentative')
            case = api('POST', prefix + '/clarifications', {'text': 'Synthetic operator note for I2 checks.', 'source': 'operator'}, 201)
            api('PUT', prefix, {'revision': case['revision'], 'original': 'Attempted overwrite', 'draft': case['draft']}, 409)
            checked('frozen testimony rejects replacement', True)
            preview = api('POST', prefix + '/prompt-preview', case['draft'])
            checked('prompt preview includes exact recorded account', original in preview['description'] and not preview['over_limit'])
            handle = api('POST', '/api/generate', {'description': 'Synthetic caller description', 'case_id': cid,
                         'case_revision': case['revision'], 'workspace': 'lab', 'style': 'forensic'}, 202)
            completed(handle)
            case = api('GET', prefix)
            initial = case['versions'][-1]
            generated = api('GET', '/images/' + initial['id']).content
            checked('persisted initial image SHA-256 and Lab workspace',
                    generated.startswith(b'\x89PNG\r\n\x1a\n') and hashlib.sha256(generated).hexdigest() == initial['sha256'] and initial['workspace'] == 'lab')
            api('POST', prefix + '/selection', {'version_id': initial['id'], 'preferred': True})
            refinement = {'parent_id': initial['id'], 'instruction': 'Slightly broader forehead for synthetic QA.',
                          'draft': case['draft'], 'revision': case['revision'], 'request_key': uuid.uuid4().hex}
            review = api('POST', prefix + '/refinement-preview', refinement)
            refinement['reviewed_prompt'] = review['description']
            handle = api('POST', prefix + '/refine', refinement, 202)
            replay = api('POST', prefix + '/refine', refinement, 202)
            checked('refinement retry reuses persisted request key', replay['job_id'] == handle['job_id'])
            completed(handle)
            case = api('GET', prefix)
            refined = case['versions'][-1]
            checked('refinement immutable child lineage', refined['parent_id'] == initial['id'])
            project = api('GET', prefix + '/versions/' + refined['id'] + '/sketch')
            raw = api('GET', project['source_url']).content
            image = Image.open(io.BytesIO(raw)).convert('RGBA')
            ImageDraw.Draw(image).line((10, 10, 70, 70), fill='#173dcc', width=4)
            edited = io.BytesIO(); image.save(edited, format='PNG')
            sketch = api('POST', prefix + '/local-edits', {'parent_id': refined['id'], 'request_key': uuid.uuid4().hex,
                         'png': data_url(edited.getvalue()), 'project': {'schema_version': 1, 'source_version_id': refined['id'],
                         'operations': [{'tool': 'line', 'points': [[10,10,.5],[70,70,.5]], 'color': '#173dcc', 'width': 4, 'opacity': 1}]}}, 201)
            opened = api('GET', prefix + '/versions/' + sketch['version_id'] + '/sketch')
            checked('saved editable sketch project retains operations', len(opened['project']['operations']) == 1)
            source = api('GET', prefix + '/versions/' + sketch['version_id'] + '/enhance')
            pixels = api('GET', source['source_url']).content
            # Defaults are an identity operation; no browser filter algorithm is simulated here.
            enhanced = api('POST', prefix + '/enhancements', {'parent_id': sketch['version_id'], 'source_id': source['source_id'],
                           'request_key': uuid.uuid4().hex, 'png': data_url(pixels),
                           'adjustments': enhancements['defaults'], 'engine': 'rgba-worker-v1'}, 201)
            checked('identity enhancement saves new immutable revision', enhanced['version_id'] != sketch['version_id'])
            api('POST', prefix + '/imports', {'image': data_url(pixels), 'filename': 'entirely-synthetic-pattern.png',
                'consent': True, 'request_key': uuid.uuid4().hex}, 201)
            case = api('GET', prefix)
            multi = {'parent_id': enhanced['version_id'], 'draft': case['draft'], 'revision': case['revision'], 'request_key': uuid.uuid4().hex}
            review = api('POST', prefix + '/multiview-preview', multi)
            checked('multi-view clearly text-only 2D', not review['image_reference_used'] and '2D' in review['description'])
            multi['reviewed_prompt'] = review['description']
            handle = api('POST', prefix + '/multiview', multi, 202); completed(handle)
            sheet = handle['job_id']
            layouts = api('POST', prefix + '/views/' + sheet + '/layouts', {'checked': True, 'note': 'Synthetic quadrants only, not faces',
                          'panels': [{'angle': a, 'rect': rect} for a,rect in zip(['front','left','right','three_quarter'],
                          [[0,0,256,256],[256,0,256,256],[0,256,256,256],[256,256,256,256]])]}, 201)
            for panel in layouts['panels']:
                data = api('GET', prefix + '/views/' + sheet + '/layouts/' + layouts['id'] + '/' + panel['angle'] + '.png').content
                assert hashlib.sha256(data).hexdigest() == panel['sha256']
            checked('four reviewed multi-view crops match checksums', True)
            checked('multi-view history persisted', len(api('GET', prefix + '/multiview')['requests']) == 1)
            report_request = {'version_id': enhanced['version_id'], 'request_key': uuid.uuid4().hex}
            report = api('POST', prefix + '/reports', report_request, 201)
            same = api('POST', prefix + '/reports', report_request, 201)
            checked('report request retry is idempotent', same['id'] == report['id'])
            checked('report list includes persisted bundle', len(api('GET', prefix + '/reports')) == 1)
            report_bytes = {}
            for extension, meta in report['files'].items():
                response = api('GET', meta['url'], raw=True); report_bytes[extension] = response.content
                assert len(response.content) == meta['bytes']
                assert hashlib.sha256(response.content).hexdigest() == meta['sha256']
            checked('PDF JSON PNG exports match saved SHA-256 and byte counts', report_bytes['pdf'].startswith(b'%PDF-') and report_bytes['png'].startswith(b'\x89PNG'))
            exported = json.loads(report_bytes['json'])
            checked('report exact testimony and all 45 attribute rows', exported['statements'][0]['text'] == original and len(exported['attribute_summary']) == 45)
            checked('report HTML preview served', 'Persisted report snapshot' in api('GET', report['preview_url']).text)
            direct_png = api('GET', prefix + '/versions/' + enhanced['version_id'] + '/export.png').content
            direct_json = api('GET', prefix + '/versions/' + enhanced['version_id'] + '/export.json')
            checked('direct JSON PNG exports work', direct_png.startswith(b'\x89PNG') and direct_json['statements'][0]['text'] == original)
            for suffix in ['/versions/' + initial['id'] + '/sketch', '/versions/' + initial['id'] + '/enhance',
                           '/versions/' + initial['id'] + '/pixels', '/versions/' + initial['id'] + '/export.png',
                           '/versions/' + initial['id'] + '/export.json', '/reports/' + report['id'] + '/pdf']:
                api('GET', '/api/cases/' + other['id'] + suffix, status=404)
            checked('case-scoped edits pixels and exports reject other-case IDs', True)
            api('GET', '/images/not-a-record', status=404)
            for path in ['/static/%2e%2e/case_store.py', '/images/%2e%2e%2fcase_store.py']:
                assert httpx.get(BASE + path, timeout=10).status_code == 404
            checked('invalid IDs and path traversal do not expose source files', True)
            case = api('POST', prefix + '/selection', {'version_id': enhanced['version_id']})
            before = json.loads(json.dumps(case))
            hashes = {v['id']: v['sha256'] for v in before['versions']}
            stop(); start()
            after = api('GET', prefix)
            checked('actual isolated restart retains testimony versions selection preferred',
                    after['statements'] == before['statements'] and after['versions'] == before['versions'] and
                    after['selected_version_id'] == before['selected_version_id'] and after['preferred_version_id'] == before['preferred_version_id'])
            for version, digest in hashes.items():
                assert hashlib.sha256(api('GET', '/images/' + version).content).hexdigest() == digest
            for extension, meta in report['files'].items():
                assert api('GET', meta['url'], raw=True).content == report_bytes[extension]
            checked('all revision and report bytes unchanged after restart', True)
            con = sqlite3.connect(runtime / 'data/witness.sqlite3')
            checked('SQLite integrity and foreign keys pass', con.execute('pragma integrity_check').fetchone()[0] == 'ok' and not con.execute('pragma foreign_key_check').fetchall())
            RESULT['synthetic_cases'] = con.execute('select count(*) from cases').fetchone()[0]
            RESULT['synthetic_versions'] = con.execute('select count(*) from versions').fetchone()[0]
            con.close()
            RESULT['runtime_external'] = all(not Path(env[key]).is_relative_to(ROOT) for key in ('WITNESSTRACE_DATA_DIR','WITNESSTRACE_OUTPUTS_DIR','WITNESSTRACE_WORK_DIR'))
            checked('all runtime roots outside repository', RESULT['runtime_external'])
            # OpenAPI contains schemas, not records or credentials.
            response = httpx.get(BASE + '/openapi.json', timeout=10)
            assert response.status_code == 200
            (OUT / 'openapi.json').write_text(json.dumps(response.json(), indent=2) + '\n')
        except Exception as error:
            RESULT['error'] = type(error).__name__ + ': ' + str(error)
            raise
        finally:
            stop(); log.close()
            RESULT['owned_server_stopped'] = process is None or process.poll() is not None
            (OUT / 'server-checks.json').write_text(json.dumps(RESULT, indent=2) + '\n')


if __name__ == '__main__':
    main()
