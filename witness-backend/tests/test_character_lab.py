"""Character Lab regression: isolated SQLite, fixtures and original fake CLI only."""
import ast
import copy
import json
from pathlib import Path
import subprocess
import os
import sys
from fastapi.testclient import TestClient
import app
import case_store as store
from lab_schema import LAB_FIELDS,FIELDS,GROUPS
from test_cases import new,save,freeze
from test_app import _setup,_wait

def attribute(value,source='operator',confidence='tentative',quote=''):
    return {'value':value,'source':source,'confidence':confidence,'quote':quote}

def test_schema_complete_and_unknown_defaults_backward_compatible():
    client=TestClient(app.app)
    schema=client.get('/api/lab-schema').json();assert len(schema['groups'])==7
    required={'face_width','forehead_width','cheekbone_height','cheek_fullness','jaw_width','chin_width','eye_size','eye_separation','eye_height','eye_shape','eyes','eyebrow_thickness','nose_size','nose_width','nose_length','nose_bridge','lip_fullness','mouth_width','hairstyle','hair','hair_texture','hairline','facial-hair','age','complexion','other_marks','body_weight','shoulder_width','neck_thickness'}
    assert required<=set(FIELDS)
    case=new(client);assert all(a['value'] is None and a['confidence']=='unknown' for a in case['draft']['lab'].values())
    # Old Phase 02 JSON records acquire unknown Lab defaults when read, without rewriting storage.
    with store.connection() as con:
        draft=con.execute('SELECT draft FROM cases WHERE id=?',(case['id'],)).fetchone()[0]
        legacy=json.loads(draft);legacy.pop('lab')
        con.execute('UPDATE cases SET draft=? WHERE id=?',(json.dumps(legacy),case['id']))
    restored=client.get('/api/cases/'+case['id']).json()
    assert set(restored['draft']['lab'])==set(LAB_FIELDS)
    assert all(a['value'] is None for a in restored['draft']['lab'].values())
    with store.connection() as con:assert 'lab' not in json.loads(con.execute('SELECT draft FROM cases WHERE id=?',(case['id'],)).fetchone()[0])

def test_lab_save_quote_validation_and_unknowns():
    client=TestClient(app.app);case=freeze(client,new(client))
    draft=copy.deepcopy(case['draft']);draft['lab']['face_width']=attribute('72')
    draft['lab']['scar']=attribute('Thin mark over left eyebrow')
    saved=save(client,case,draft=draft);assert saved.status_code==200
    case=saved.json();assert case['draft']['lab']['face_width']['value']=='72'
    assert case['draft']['lab']['nose_width']['value'] is None
    for bad in ['-1','101','50.5','nan']:
        broken=copy.deepcopy(draft);broken['lab']['face_width']=attribute(bad)
        assert save(client,case,draft=broken).status_code==422
    broken=copy.deepcopy(draft);broken['lab']['nose_bridge']=attribute('Made up option')
    assert save(client,case,draft=broken).status_code==422
    broken=copy.deepcopy(draft);broken['lab']['hairstyle']=attribute('dark hair','witness',quote='not in testimony')
    assert save(client,case,draft=broken).status_code==422
    broken['lab']['hairstyle']['quote']='dark hair'
    assert save(client,case,draft=broken).status_code==200
    assert client.get('/api/cases/'+case['id']).json()['statements'][0]['text'].startswith('  A fictional')

def test_prompt_concise_all_controls_provenance_no_silent_truncation():
    client=TestClient(app.app);case=freeze(client,new(client))
    draft=copy.deepcopy(case['draft'])
    for key,f in LAB_FIELDS.items():
        draft['lab'][key]=attribute('68' if f['kind']=='slider' else f['options'][0] if f['kind']=='select' else 'supplied detail')
    preview=client.post('/api/cases/'+case['id']+'/prompt-preview',json=draft)
    assert preview.status_code==200
    data=preview.json();assert data['length']==len(data['description']) and data['limit']==2500
    for key,f in LAB_FIELDS.items():assert f['label']+'=' in data['description']
    assert '68/100 relative' in data['description']
    assert 'operator requests (tentative' in data['description']
    assert 'Eye color=' not in data['description'] and 'Estimated age appearance=' not in data['description']
    assert case['statements'][0]['text'] in data['description']
    assert 'may drift' in data['description']
    assert client.get('/api/cases/'+case['id']).json()['revision']==case['revision']
    # Oversized but valid notes are retained exactly; preview reports full length and generation rejects.
    text='A' * 1800
    response=client.post('/api/cases/'+case['id']+'/clarifications',json={'text':text,'source':'operator'})
    case=response.json();case=save(client,case,draft=draft).json()
    large=client.post('/api/cases/'+case['id']+'/prompt-preview',json=draft).json()
    assert large['over_limit'] and large['length']>2500 and text in large['description']
    rejected=client.post('/api/generate',json={'description':'Case request placeholder','case_id':case['id'],'case_revision':case['revision'],'workspace':'lab'})
    assert rejected.status_code==422 and 'No testimony or attributes were truncated' in rejected.json()['detail']
    assert not app._guard.locked()
    record=client.get('/api/cases/'+case['id']).json();assert len(record['jobs'])==0
    assert record['statements'][1]['text']==text

def test_update_snapshot_parent_revision_persistence(tmp_path,monkeypatch):
    client=_setup(tmp_path,monkeypatch,'success');case=freeze(client,new(client))
    draft=copy.deepcopy(case['draft']);draft['lab']['face_width']=attribute('70');draft['lab']['hair_texture']=attribute('80')
    case=save(client,case,draft=draft).json();ids=[]
    for number in range(2):
        response=client.post('/api/generate',json={'description':'Case request placeholder','case_id':case['id'],'case_revision':case['revision'],'workspace':'lab'})
        assert response.status_code==202
        second=client.post('/api/generate',json={'description':'Duplicate case request','case_id':case['id'],'case_revision':case['revision'],'workspace':'lab'})
        assert second.status_code==409
        job=_wait(client,response.json()['job_id']);assert job['status']=='complete'
        ids.append(job['job_id'])
    result=client.get('/api/cases/'+case['id']).json()
    assert result['versions'][-1]['parent_id']==ids[0]
    assert result['versions'][-1]['case_revision']==case['revision']
    assert result['versions'][-1]['workspace']=='lab'
    assert result['last_generated_draft']['lab']['face_width']['value']=='70'
    draft['lab']['face_width']=attribute('25');case=save(client,case,draft=draft).json()
    assert case['last_generated_draft']['lab']['face_width']['value']=='70'
    with store.connection() as con:
        snapshot=json.loads(con.execute('SELECT draft FROM jobs WHERE id=?',(ids[-1],)).fetchone()[0])
        assert snapshot['lab']['face_width']['value']=='70' and snapshot['_case_revision']<case['revision']
        assert snapshot['_workspace']=='lab'
    code="""from fastapi.testclient import TestClient
import app
client=TestClient(app.app)
case=client.get('/api/cases/CASE').json()
assert case['draft']['lab']['face_width']['value']=='25'
assert case['last_generated_draft']['lab']['face_width']['value']=='70'
assert len(case['versions'])==2
assert client.get('/images/JOB').status_code==200
print('Character Lab persistence in fresh process: PASS')
""".replace('CASE',case['id']).replace('JOB',ids[-1])
    env=os.environ.copy();env['WITNESSTRACE_DATA_DIR']=str(store.DATA)
    run=subprocess.run([sys.executable,'-c',code],env=env,cwd=Path(app.__file__).parent,capture_output=True,text=True,timeout=30)
    assert run.returncode==0,run.stderr

def test_original_adapter_unchanged_since_phase02():
    root=Path(app.__file__).parent
    def functions(path):return {n.name:ast.dump(n) for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef)}
    before=functions(root/'tests/fixtures/phase03_app.py');after=functions(root/'app.py')
    for name in ['prompt_for','run_job','snapshot_generated','validate_generated_image','durable_run_job']:
        assert before[name]==after[name],name

def test_older_text_save_preserves_lab_and_neutral_is_not_unknown():
    client=TestClient(app.app);case=freeze(client,new(client))
    draft=copy.deepcopy(case['draft']);draft['lab']['face_width']=attribute('50')
    case=save(client,case,draft=draft).json()
    older=copy.deepcopy(case['draft']);older.pop('lab')
    response=save(client,case,draft=older)
    assert response.status_code==200
    case=response.json();assert case['draft']['lab']['face_width']['value']=='50'
    preview=client.post('/api/cases/'+case['id']+'/prompt-preview',json=case['draft']).json()
    assert 'Face width=neutral relative setting (50/100 relative)' in preview['description']
    assert 'operator requests (tentative' in preview['description']
    draft=copy.deepcopy(case['draft']);draft['lab']['face_width']={'value':None,'confidence':'unknown','source':'operator','quote':''}
    case=save(client,case,draft=draft).json()
    preview=client.post('/api/cases/'+case['id']+'/prompt-preview',json=case['draft']).json()
    assert 'Face width=' not in preview['description']

def test_lab_generation_failure_and_explicit_retry(tmp_path,monkeypatch):
    from test_app import _fake_binary
    client=_setup(tmp_path,monkeypatch,'claim-only');case=freeze(client,new(client))
    draft=copy.deepcopy(case['draft']);draft['lab']['face_width']=attribute('70')
    case=save(client,case,draft=draft).json()
    payload={'description':'Case request placeholder','case_id':case['id'],'case_revision':case['revision'],'workspace':'lab'}
    first=client.post('/api/generate',json=payload).json();failed=_wait(client,first['job_id'])
    assert failed['status']=='failed'
    assert client.get('/api/cases/'+case['id']).json()['versions']==[]
    assert not app._guard.locked()
    _fake_binary(tmp_path/'claim-only','success')
    retry=client.post('/api/generate',json=payload);assert retry.status_code==202
    result=_wait(client,retry.json()['job_id']);assert result['status']=='complete'
    restored=client.get('/api/cases/'+case['id']).json()
    assert len(restored['jobs'])==2 and len(restored['versions'])==1
    assert restored['versions'][0]['case_revision']==case['revision']
    assert restored['last_generated_draft']['lab']['face_width']['value']=='70'
    assert restored['statements']==case['statements']
