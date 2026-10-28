"""Phase 04: isolated fake CLI only; real generation evidence is separate."""
import copy
import hashlib
import json
import sqlite3
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
import pytest
import app
import case_store as store
from test_app import _setup,_wait,_fake_binary
from test_cases import new,freeze,save


def generate(client,case):
    r=client.post('/api/generate',json={'description':'Case generation request','case_id':case['id'],'case_revision':case['revision']})
    assert r.status_code==202,r.text
    assert _wait(client,r.json()['job_id'])['status']=='complete'
    return client.get('/api/cases/'+case['id']).json()

def payload(client,case,parent=None,instruction='Make the nose longer. Add a full beard.'):
    body={'revision':case['revision'],'parent_id':parent or case['versions'][-1]['id'],'draft':case['draft'],'instruction':instruction,'request_key':uuid.uuid4().hex}
    r=client.post('/api/cases/'+case['id']+'/refinement-preview',json=body)
    assert r.status_code==200,r.text
    body['reviewed_prompt']=r.json()['description']
    return body

def refine(client,case,body):
    r=client.post('/api/cases/'+case['id']+'/refine',json=body)
    assert r.status_code==202,r.text
    assert _wait(client,r.json()['job_id'])['status']=='complete'
    return client.get('/api/cases/'+case['id']).json()

def test_revision_metadata_lineage_immutability_selection_and_branch(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));original=case['statements'][0]['text'];v1=case['versions'][0]
    body=payload(c,case);case=refine(c,case,body);v2=case['versions'][1]
    assert v2['parent_id']==v1['id'] and v2['id']!=v1['id']
    assert v2['original_prompt']==original and v2['refinement_prompt']==body['instruction']
    assert v2['generation_prompt']==body['reviewed_prompt'] and v2['outcome']=='complete'
    assert v2['attribute_snapshot']['attributes']['eyes']['value'] is None
    assert v2['generation_job_id']==v2['id'] and v2['mode']=='prompt_regeneration' and v2['width']==512
    assert v2['image_path']!=case['versions'][0]['image_path']
    assert hashlib.sha256(c.get(v2['image_url']).content).hexdigest()==v2['sha256']
    for preferred in [False,True]:
        r=c.post('/api/cases/'+case['id']+'/selection',json={'version_id':v1['id'],'preferred':preferred});assert r.status_code==200
    case=c.get('/api/cases/'+case['id']).json();assert case['selected_version_id']==case['preferred_version_id']==v1['id']
    body=payload(c,case,v1['id'],'Make the forehead slightly wider.');assert 'Add a full beard' not in body['reviewed_prompt']
    case=refine(c,case,body);assert case['versions'][-1]['parent_id']==v1['id']
    assert case['preferred_version_id']==v1['id'] and len(case['versions'])==3 and len(case['refinements'])==2
    assert case['statements'][0]['text']==original and len(case['statements'])==1
    # Repeated completion is idempotent and cannot revise stored metadata or create duplicate events.
    before=case
    store.finish_job(SimpleNamespace(job_id=case['versions'][-1]['id'],status='complete'),app.OUTPUTS)
    assert c.get('/api/cases/'+case['id']).json()==before
    with store.connection() as con:
        with pytest.raises(sqlite3.IntegrityError):con.execute("UPDATE version_details SET metadata='{}'")
        with pytest.raises(sqlite3.IntegrityError):con.execute("DELETE FROM refinement_requests")


def test_refinement_accumulation_budget_and_review_staleness(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)))
    case=refine(c,case,payload(c,case,instruction='Change hairstyle to tied-back.'))
    body=payload(c,case,instruction='Increase cheek fullness. Preserve the rest.')
    assert 'Change hairstyle to tied-back.' in body['reviewed_prompt'] and 'Increase cheek fullness.' in body['reviewed_prompt']
    body['instruction']='Different explicit request'
    assert c.post('/api/cases/'+case['id']+'/refine',json=body).status_code==409
    assert not app._guard.locked()
    oversized={**body,'instruction':'x'*1800,'reviewed_prompt':''}
    preview=c.post('/api/cases/'+case['id']+'/refinement-preview',json=oversized).json()
    assert preview['over_limit'] and 'x'*1800 in preview['description'] and preview['length']==len(preview['description'])
    assert c.post('/api/cases/'+case['id']+'/refine',json=oversized).status_code==422
    assert len(c.get('/api/cases/'+case['id']).json()['jobs'])==2


def test_concurrent_idempotency_isolation_late_selection(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));case=generate(c,case)
    other=freeze(c,new(c));body=payload(c,case);path='/api/cases/'+case['id']+'/refine'
    bad={**body,'revision':other['revision']}
    assert c.post('/api/cases/'+other['id']+'/refine',json=bad).status_code==404
    assert c.post('/api/cases/'+other['id']+'/selection',json={'version_id':case['versions'][0]['id']}).status_code==404
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:c.post(path,json=body),range(2)))
    assert all(r.status_code in [202,409] for r in responses)
    accepted=next(r.json() for r in responses if r.status_code==202)
    chosen=case['versions'][0]['id'];assert c.post('/api/cases/'+case['id']+'/selection',json={'version_id':chosen}).status_code==200
    assert _wait(c,accepted['job_id'])['status']=='complete'
    assert c.post(path,json=body).json()['job_id']==accepted['job_id']
    assert c.post(path,json={**body,'instruction':'different'}).status_code==409
    record=c.get('/api/cases/'+case['id']).json();assert len(record['refinements'])==1 and len(record['versions'])==3
    assert record['selected_version_id']==chosen and record['versions'][-1]['parent_id']==case['versions'][-1]['id']
    assert c.get('/api/cases/'+other['id']).json()['versions']==[]


def test_failure_retry_bad_image_and_restart(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));v1=case['versions'][0];body=payload(c,case)
    _fake_binary(tmp_path/'success','claim-only')
    r=c.post('/api/cases/'+case['id']+'/refine',json=body);job=_wait(c,r.json()['job_id']);assert job['status']=='failed'
    assert c.get(job.get('image_url') or '/images/'+job['job_id']).status_code==404
    assert len(c.get('/api/cases/'+case['id']).json()['versions'])==1
    # Same network request does not start a new attempt after failure.
    assert c.post('/api/cases/'+case['id']+'/refine',json=body).json()['job_id']==job['job_id']
    _fake_binary(tmp_path/'success','success');body['request_key']=uuid.uuid4().hex;case=refine(c,case,body)
    assert len(case['versions'])==2 and [r['status'] for r in case['refinements']]==['failed','complete']
    store.initialize();record=c.get('/api/cases/'+case['id']).json();assert record['versions']==case['versions']
    assert c.get(v1['image_url']).status_code==200
    store.image_path(v1['id']).write_bytes(b'corruption')
    bad=payload # Parent must pass checksum before prompt review or job creation.
    body['parent_id']=v1['id'];body['request_key']=uuid.uuid4().hex
    assert c.post('/api/cases/'+case['id']+'/refinement-preview',json=body).status_code==409
    assert len(c.get('/api/cases/'+case['id']).json()['versions'])==2


def test_rejected_stale_blank_unknown_and_interrupted_refinement(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));body=payload(c,case)
    case=save(c,case).json()
    assert c.post('/api/cases/'+case['id']+'/refine',json=body).status_code==409
    assert not app._guard.locked()
    body=payload(c,case)
    assert c.post('/api/cases/'+case['id']+'/refine',json={**body,'instruction':'   '}).status_code==422
    assert c.post('/api/cases/'+case['id']+'/refine',json={**body,'parent_id':'a'*32}).status_code==404
    job=app.Job(job_id=uuid.uuid4().hex,description='Refinement',style='forensic',case_id=case['id'])
    store.start_job(job,case['id'],case['revision'],'refinement',store.Refinement(**body))
    store.initialize();store.initialize()
    record=c.get('/api/cases/'+case['id']).json()
    assert record['refinements'][-1]['status']=='failed' and len(record['versions'])==1
    assert record['selected_version_id']==case['versions'][0]['id']
    assert c.get('/api/jobs/'+job.job_id).json()['image_url'] is None


def test_finish_rejects_invalid_image_and_preferred_does_not_clear_selection(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));v1=case['versions'][0]
    # Preferred can be set independently before any explicit selection record exists.
    with store.connection() as con:con.execute('DELETE FROM selections WHERE case_id=?',(case['id'],))
    record=c.post('/api/cases/'+case['id']+'/selection',json={'version_id':v1['id'],'preferred':True}).json()
    assert record['selected_version_id']==v1['id']
    body=payload(c,case);job=app.Job(job_id=uuid.uuid4().hex,description='Refinement',style='forensic',case_id=case['id'])
    store.start_job(job,case['id'],case['revision'],'refinement',store.Refinement(**body))
    (app.OUTPUTS/(job.job_id+'.png')).write_bytes(b'not a real image')
    job.status='complete';job.image_url='/images/'+job.job_id
    with pytest.raises(Exception):store.finish_job(job,app.OUTPUTS)
    job.status='failed';job.image_url=None;job.message='Invalid image';store.finish_job(job,app.OUTPUTS)
    result=c.get('/api/cases/'+case['id']).json();assert len(result['versions'])==1 and result['refinements'][-1]['status']=='failed'
    assert c.get('/images/'+job.job_id).status_code==404
