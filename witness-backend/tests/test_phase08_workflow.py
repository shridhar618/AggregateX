"""Final workflow integration with isolated fake CLI; never live image generation."""
import hashlib
import uuid
from test_app import _setup
from test_cases import new, freeze
from test_refinement import generate, payload, refine
from test_sketchpad import body as sketch_body
from test_enhance import adjustment_body
import case_store as store


def test_full_revision_chain_report_and_database_reopen(tmp_path, monkeypatch):
    c = _setup(tmp_path, monkeypatch, 'success')
    case = freeze(c, new(c))
    statements = case['statements']
    case = generate(c, case)
    initial = case['versions'][-1]
    case = refine(c, case, payload(c, case, instruction='Slightly thicker eyebrows.'))
    refined = case['versions'][-1]
    assert refined['parent_id'] == initial['id']
    response = c.post(f"/api/cases/{case['id']}/local-edits", json=sketch_body(case))
    assert response.status_code == 201, response.text
    case = c.get('/api/cases/' + case['id']).json()
    sketch = case['versions'][-1]
    assert sketch['parent_id'] == refined['id']
    adjustment = adjustment_body(sketch['id'], contrast=18)
    # Same source dimensions as the real local sketch fixture.
    from test_sketchpad import png
    adjustment['png'] = png()
    response = c.post(f"/api/cases/{case['id']}/enhancements", json=adjustment)
    assert response.status_code == 201, response.text
    case = c.get('/api/cases/' + case['id']).json()
    enhanced = case['versions'][-1]
    assert enhanced['parent_id'] == sketch['id']
    response = c.post(f"/api/cases/{case['id']}/reports", json={'version_id': enhanced['id'], 'request_key': uuid.uuid4().hex})
    assert response.status_code == 201, response.text
    report = response.json()
    store.initialize()  # Reopen persisted schema; do not replace or recreate records.
    reopened = c.get('/api/cases/' + case['id']).json()
    assert reopened['statements'] == statements
    assert reopened['draft']['attributes']['eyes']['value'] is None
    assert reopened['versions'] == case['versions']
    for v in reopened['versions']:
        assert hashlib.sha256(c.get(v['image_url']).content).hexdigest() == v['sha256']
    for meta in report['files'].values():
        assert hashlib.sha256(c.get(meta['url']).content).hexdigest() == meta['sha256']
    exported = c.get(report['files']['json']['url']).json()
    assert exported['statements'] == statements
    assert exported['selected_version']['id'] == enhanced['id']


def test_report_for_older_revision_preserves_complete_history_and_case_isolation(tmp_path, monkeypatch):
    c = _setup(tmp_path, monkeypatch, 'success')
    case = generate(c, freeze(c, new(c)))
    selected = case['versions'][0]
    case = generate(c, case)
    other = freeze(c, new(c))
    before = c.get('/api/cases/' + other['id']).json()
    request = {'version_id': selected['id'], 'request_key': uuid.uuid4().hex}
    response = c.post(f"/api/cases/{case['id']}/reports", json=request)
    assert response.status_code == 201, response.text
    report = response.json()
    data = c.get(report['files']['json']['url']).json()
    assert data['selected_version']['id'] == selected['id']
    assert [v['id'] for v in data['revision_history']] == [v['id'] for v in case['versions']]
    assert c.post(f"/api/cases/{other['id']}/reports", json=request).status_code == 404
    for kind in ['pdf', 'json', 'png']:
        assert c.get(f"/api/cases/{other['id']}/reports/{report['id']}/{kind}").status_code == 404
    assert c.get('/api/cases/' + other['id']).json() == before
