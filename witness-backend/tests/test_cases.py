"""Case lifecycle and durable image tests; all generator calls use an isolated fake CLI."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient
import app
import case_store as store
from test_app import _setup, _wait


def new(client,synthetic=False):
    response=client.post('/api/cases',json={'title':'Fictional test case','synthetic':synthetic})
    assert response.status_code==201
    return response.json()


def save(client,case,original=None,draft=None):
    body={'revision':case['revision'],'draft':draft or case['draft']}
    if original is not None:body['original']=original
    return client.put('/api/cases/'+case['id'],json=body)


def freeze(client,case,text='  A fictional adult with dark hair.\nUncertain eyes.  '):
    response=client.post('/api/cases/'+case['id']+'/freeze',json={'text':text,'revision':case['revision']})
    assert response.status_code==200,response.text
    return response.json()


def test_original_exact_freeze_append_and_db_constraints():
    client=TestClient(app.app);case=new(client)
    text='  Witness’s exact Unicode words\n  Unknown eye color.  '
    case=save(client,case,text).json()
    assert case['statements'][0]['text']==text
    blocked=client.post('/api/generate',json={'description':'Unfrozen case request','case_id':case['id'],'case_revision':case['revision']})
    assert blocked.status_code==409
    assert not app._guard.locked()
    case=freeze(client,case,text)
    assert case['statements'][0]['text']==text
    assert case['statements'][0]['source']=='witness'
    assert case['frozen_at'] and case['statements'][0]['created_at']
    assert save(client,case,'Replacement').status_code==409
    assert client.post('/api/cases/'+case['id']+'/freeze',json={'revision':case['revision'],'text':'Replacement original'}).status_code==409
    response=client.post('/api/cases/'+case['id']+'/clarifications',json={'text':'  Additional uncertainty.  ','source':'witness'})
    assert response.status_code==201
    updated=response.json();assert updated['statements'][0]['text']==text
    assert sum(s['kind']=='original' for s in updated['statements'])==1
    assert updated['statements'][1]['text']=='  Additional uncertainty.  '
    with store.connection() as con:
        with pytest.raises(sqlite3.IntegrityError):con.execute("UPDATE statements SET text='edited' WHERE case_id=? AND kind='original'",(case['id'],))
        with pytest.raises(sqlite3.IntegrityError):con.execute("DELETE FROM statements WHERE case_id=?",(case['id'],))
        with pytest.raises(sqlite3.IntegrityError):con.execute("UPDATE statements SET text='edited' WHERE case_id=? AND kind='clarification'",(case['id'],))
        with pytest.raises(sqlite3.IntegrityError):con.execute("UPDATE cases SET frozen_at=NULL WHERE id=?",(case['id'],))
        with pytest.raises(sqlite3.IntegrityError):con.execute('INSERT INTO statements VALUES(?,?,?,?,?,?)',('duplicate',case['id'],'original','other','witness',store.now()))


def test_attributes_quotes_uncertainty_and_stale_revision():
    client=TestClient(app.app);case=freeze(client,new(client))
    draft=case['draft'];assert all(a['value'] is None and a['confidence']=='unknown' for a in draft['attributes'].values())
    draft['attributes']['hair']={'value':'Black','confidence':'tentative','source':'witness','quote':'not in account'}
    assert save(client,case,draft=draft).status_code==422
    draft['attributes']['hair']['quote']='dark hair'
    updated=save(client,case,draft=draft).json()
    assert updated['draft']['attributes']['hair']['confidence']=='tentative'
    assert updated['draft']['attributes']['eyes']['value'] is None
    assert save(client,case,draft=draft).status_code==409
    draft['attributes']['hair']['quote']=''
    assert save(client,updated,draft=draft).status_code==422
    draft['attributes']['hair']={'value':None,'confidence':'certain','source':'operator','quote':''}
    assert save(client,updated,draft=draft).status_code==422
    draft['attributes']['hair']={'value':None,'confidence':'unknown','source':'operator','quote':''}
    draft['attributes']['age']={'value':'101','confidence':'tentative','source':'operator','quote':''}
    assert save(client,updated,draft=draft).status_code==422


def test_case_generation_versions_restart_and_image_integrity(tmp_path,monkeypatch):
    client=_setup(tmp_path,monkeypatch,'success');case=freeze(client,new(client))
    ids=[]
    for _ in range(2):
        response=client.post('/api/generate',json={'description':'Caller prompt must not replace frozen account','style':'portrait','case_id':case['id'],'case_revision':case['revision']})
        assert response.status_code==202,response.text
        job=_wait(client,response.json()['job_id']);assert job['status']=='complete',job
        ids.append(job['job_id'])
    saved=client.get('/api/cases/'+case['id']).json()
    assert len(saved['versions'])==2
    assert saved['versions'][1]['parent_id']==ids[0]
    first=client.get('/images/'+ids[0]);assert first.status_code==200
    assert saved['versions'][0]['sha256']==hashlib.sha256(first.content).hexdigest()
    with store.connection() as con:
        job=con.execute('SELECT * FROM jobs WHERE id=?',(ids[0],)).fetchone()
        assert 'A fictional adult with dark hair' in job['description']
        assert 'Caller prompt' not in job['description'] and job['style']=='forensic'
    # Separate Python process, fresh app import and memory map; same SQLite and case image folder.
    code='''import json
from fastapi.testclient import TestClient
import app
client=TestClient(app.app)
case=client.get('/api/cases/CASE').json()
assert len(case['versions'])==2
assert client.get('/api/jobs/JOB').json()['status']=='complete'
image=client.get('/images/JOB')
assert image.status_code==200
print(json.dumps({'case_id':case['id'],'versions':len(case['versions']),'image_bytes':len(image.content)}))
'''.replace('CASE',case['id']).replace('JOB',ids[0])
    env=os.environ.copy();env['WITNESSTRACE_DATA_DIR']=str(store.DATA)
    completed=subprocess.run([sys.executable,'-c',code],cwd=Path(app.__file__).parent,env=env,text=True,capture_output=True,timeout=30)
    assert completed.returncode==0,completed.stderr
    store.initialize();assert client.get('/api/cases/'+case['id']).json()['statements']==saved['statements']
    path=store.image_path(ids[0]);path.write_bytes(b'corrupted fixture')
    assert client.get('/images/'+ids[0]).status_code==409


def test_paths_and_unknowns_rejected(tmp_path):
    client=TestClient(app.app)
    for path in ['/api/cases/not-an-id','/images/not-an-id','/images/%2e%2e%2fapp.py','/images/'+('a'*32)]:
        assert client.get(path).status_code==404
    with pytest.raises(Exception):store.safe_path('../escape','a'*32,'.png')
    with pytest.raises(Exception):store.safe_path('a'*32,'b'*32,'.txt')
    (store.DATA/'cases').mkdir(parents=True)
    outside=tmp_path/'outside';outside.mkdir()
    (store.DATA/'cases'/('a'*32)).symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError):store.safe_path('a'*32,'b'*32,'.png')
    assert client.post('/api/cases',json={'title':'  '}).status_code==422
    case=new(client)
    assert client.put('/api/cases/'+case['id'],json={'revision':0,'draft':case['draft'],'image_path':'../bad'}).status_code==422


def test_restart_interruption_and_migration_preserves_cases():
    client=TestClient(app.app);case=new(client,True)
    case=save(client,case,'A synthetic fictional character.').json()
    job=app.Job(job_id='a'*32,description='Case request',style='forensic',case_id=case['id'])
    store.start_job(job,case['id'],case['revision'])
    store.initialize();store.initialize()
    status=client.get('/api/jobs/'+job.job_id).json()
    assert status['status']=='failed' and 'restarted' in status['message']
    assert client.get('/api/cases/'+case['id']).json()['statements'][0]['text']=='A synthetic fictional character.'
    with store.connection() as con:
        assert con.execute('PRAGMA user_version').fetchone()[0]==1
        assert con.execute('PRAGMA journal_mode').fetchone()[0]=='wal'


def test_original_generation_functions_unchanged():
    root=Path(app.__file__).parent
    original=ast.parse((root/'tests/fixtures/phase02_app.py').read_text())
    current=ast.parse((root/'app.py').read_text())
    for name in ['prompt_for','run_job','snapshot_generated','validate_generated_image']:
        def function(tree):return ast.dump(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name))
        assert function(original)==function(current),name


def test_failed_case_job_persists_without_false_version(tmp_path,monkeypatch):
    client=_setup(tmp_path,monkeypatch,'claim-only');case=freeze(client,new(client))
    response=client.post('/api/generate',json={'description':'Case request placeholder','case_id':case['id'],'case_revision':case['revision']})
    assert response.status_code==202
    job=_wait(client,response.json()['job_id'])
    assert job['status']=='failed' and job['image_url'] is None
    store.initialize()
    record=client.get('/api/cases/'+case['id']).json()
    assert len(record['versions'])==0
    assert record['jobs'][0]['status']=='failed'
    assert any(e['kind']=='generation_failed' for e in record['events'])
    assert client.get('/images/'+job['job_id']).status_code==404


def test_legacy_images_remain_retrievable_after_restart(tmp_path,monkeypatch):
    client=_setup(tmp_path,monkeypatch,'success')
    response=client.post('/api/generate',json={'description':'A fictional character with unknown traits','style':'portrait'})
    job=_wait(client,response.json()['job_id']);assert job['status']=='complete'
    before=client.get(job['image_url']).content
    monkeypatch.setattr(app,'_jobs',{})
    store.initialize()
    assert client.get(job['image_url']).content==before
    assert client.get('/api/jobs/'+job['job_id']).json()['status']=='complete'
    assert store.list_cases()==[]


def test_worker_start_failure_releases_guard(monkeypatch):
    client=TestClient(app.app,raise_server_exceptions=False)
    def fail_start(self):raise RuntimeError('fixture start failure')
    monkeypatch.setattr(app.threading.Thread,'start',fail_start)
    # Call endpoint directly: monkeypatching all threads would also affect TestClient's portal.
    with pytest.raises(RuntimeError):
        app.generate(app.GenerateRequest(description='A fictional character with dark hair'))
    assert not app._guard.locked()
    with store.connection() as con:
        assert con.execute('SELECT status FROM jobs').fetchone()[0]=='failed'


def test_legacy_symlink_and_persisted_path_traversal_rejected(tmp_path,monkeypatch):
    client=_setup(tmp_path,monkeypatch,'success');case=freeze(client,new(client))
    response=client.post('/api/generate',json={'description':'Case image request','case_id':case['id'],'case_revision':case['revision']})
    job=_wait(client,response.json()['job_id']);assert job['status']=='complete'
    with store.connection() as con:
        con.execute('UPDATE versions SET path=? WHERE id=?',('../../app.py',job['job_id']))
    assert client.get(job['image_url']).status_code==404
    external=tmp_path/'private.png';external.write_bytes(b'private fixture bytes')
    malicious=app.OUTPUTS/(('b'*32)+'.png');malicious.symlink_to(external)
    assert client.get('/images/'+('b'*32)).status_code==404


def test_operator_note_cannot_be_relabelled_as_witness_quote():
    client=TestClient(app.app);case=freeze(client,new(client))
    response=client.post('/api/cases/'+case['id']+'/clarifications',json={'text':'Operator invention: bright blue eyes','source':'operator'})
    case=response.json();draft=case['draft']
    draft['attributes']['eyes']={'value':'Blue','confidence':'tentative','source':'witness','quote':'bright blue eyes'}
    assert save(client,case,draft=draft).status_code==422
    draft['attributes']['eyes']['source']='operator'
    assert save(client,case,draft=draft).status_code==200
