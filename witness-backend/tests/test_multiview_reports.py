"""Phase 07 isolated fake CLI fixtures and real locally generated PDFs; no live AI."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import pytest
from fastapi.testclient import TestClient
import app
import case_store as store
import report_store
from test_app import _setup,_wait,_fake_binary
from test_cases import new,freeze,save
from test_refinement import generate


def view_request(c,case,parent=None):
    body={'parent_id':parent or case['versions'][-1]['id'],'revision':case['revision'],'draft':case['draft'],'request_key':uuid.uuid4().hex}
    response=c.post('/api/cases/'+case['id']+'/multiview-preview',json=body);assert response.status_code==200,response.text
    body['reviewed_prompt']=response.json()['description'];return body


def concept(c,case,body=None):
    body=body or view_request(c,case);response=c.post('/api/cases/'+case['id']+'/multiview',json=body);assert response.status_code==202,response.text
    result=_wait(c,response.json()['job_id']);assert result['status']=='complete',result
    return c.get('/api/cases/'+case['id']).json(),body


def test_multiview_prompt_snapshot_parent_and_format(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));parent=case['versions'][0];body=view_request(c,case)
    assert case['statements'][0]['text'] in body['reviewed_prompt'] and all(s in body['reviewed_prompt'] for s in ['2×2','FRONT','LEFT PROFILE','RIGHT PROFILE','THREE-QUARTER','Text-only','Unknown'])
    assert parent['id'] in body['reviewed_prompt'] and len(body['reviewed_prompt'])<=2500
    case,body=concept(c,case,body);v=case['versions'][-1];assert v['parent_id']==parent['id'] and v['mode']==v['creation_kind']=='concept_multiview' and v['workspace']=='multiview'
    assert v['image_format']=='PNG' and v['source_revision']['sha256']==parent['sha256'] and v['generation_route'].startswith('Existing authenticated Codex CLI')
    assert not v['image_reference_used'] and v['generation_prompt']==body['reviewed_prompt']
    assert hashlib.sha256(c.get(v['image_url']).content).hexdigest()==v['sha256']
    views=c.get('/api/cases/'+case['id']+'/multiview').json();assert views['requests'][0]['layout'] is None and views['requests'][0]['status']=='complete'
    assert case['statements'][0]['text'].startswith('  A fictional') and case['draft']['attributes']['eyes']['value'] is None


def test_multiview_budget_staleness_isolation_and_repeated_requests(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));body=view_request(c,case);path='/api/cases/'+case['id']+'/multiview'
    altered=copy.deepcopy(body);altered['reviewed_prompt']='Caller text must not replace account';assert c.post(path,json=altered).status_code==409 and not app._guard.locked()
    other=freeze(c,new(c));assert c.post('/api/cases/'+other['id']+'/multiview-preview',json=body).status_code==404
    big=copy.deepcopy(body);big['draft']['lab']['clothing']={'value':'x'*100,'confidence':'tentative','source':'operator','quote':''}
    case=c.post('/api/cases/'+case['id']+'/clarifications',json={'text':'A'*1800,'source':'operator'}).json();big['revision']=case['revision'];preview=c.post(path+'-preview',json=big).json();assert preview['over_limit'] and 'A'*1800 in preview['description']
    assert c.post(path,json=big).status_code==422 and not app._guard.locked()
    # Stale revision fails before any job is created.
    assert c.post(path,json=body).status_code==409
    with store.connection() as con:assert con.execute('SELECT COUNT(*) FROM multiview_requests').fetchone()[0]==0


def test_multiview_concurrency_idempotency_and_late_selection(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));case=generate(c,case);body=view_request(c,case);path='/api/cases/'+case['id']+'/multiview'
    with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:c.post(path,json=body),range(2)))
    assert all(r.status_code in [202,409] for r in responses);accepted=next(r.json() for r in responses if r.status_code==202)
    chosen=case['versions'][0]['id'];assert c.post('/api/cases/'+case['id']+'/selection',json={'version_id':chosen}).status_code==200
    assert _wait(c,accepted['job_id'])['status']=='complete'
    assert c.post(path,json=body).json()['job_id']==accepted['job_id']
    changed=copy.deepcopy(body);changed['draft']['style']='portrait';assert c.post(path,json=changed).status_code==409
    result=c.get('/api/cases/'+case['id']).json();assert result['selected_version_id']==chosen and result['versions'][-1]['parent_id']==case['versions'][-1]['id']
    assert len(c.get(path).json()['requests'])==1


def test_multiview_failure_retry_and_restart_interruption(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));body=view_request(c,case);path='/api/cases/'+case['id']+'/multiview'
    _fake_binary(tmp_path/'success','claim-only');r=c.post(path,json=body);assert _wait(c,r.json()['job_id'])['status']=='failed'
    assert len(c.get('/api/cases/'+case['id']).json()['versions'])==1
    assert c.get('/images/'+r.json()['job_id']).status_code==404
    _fake_binary(tmp_path/'success','success');body['request_key']=uuid.uuid4().hex;case,_=concept(c,case,body);assert len(case['versions'])==2
    pending=app.Job(job_id=uuid.uuid4().hex,description='pending concept',style='forensic',case_id=case['id']);request=app.multiview_store.Request(**{**body,'request_key':uuid.uuid4().hex})
    store.start_job(pending,case['id'],case['revision'],'multiview',multiview=request);store.initialize();store.initialize()
    assert c.get('/api/jobs/'+pending.job_id).json()['status']=='failed' and len(c.get('/api/cases/'+case['id']).json()['versions'])==2


def test_panels_require_explicit_review_bounds_and_case_ownership(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));case,_=concept(c,case);v=case['versions'][-1];path=f"/api/cases/{case['id']}/views/{v['id']}/layouts"
    panels=[{'angle':angle,'rect':rect} for angle,rect in zip(['front','left','right','three_quarter'],[[0,0,256,256],[256,0,256,256],[0,256,256,256],[256,256,256,256]])]
    assert c.post(path,json={'checked':False,'panels':panels}).status_code==422
    bad=copy.deepcopy(panels);bad[1]['rect']=[0,0,256,256];assert c.post(path,json={'checked':True,'panels':bad}).status_code==422
    response=c.post(path,json={'checked':True,'panels':panels,'note':'Fixture geometry review only; not real faces.'});assert response.status_code==201,response.text
    layout=response.json();url=path+'/'+layout['id']+'/front.png';image=c.get(url);assert image.status_code==200
    panel=next(p for p in layout['panels'] if p['angle']=='front');assert hashlib.sha256(image.content).hexdigest()==panel['sha256'] and Image.open(io.BytesIO(image.content)).size==(256,256)
    other=freeze(c,new(c));assert c.get(url.replace(case['id'],other['id'])).status_code==404
    assert c.get(path+'/'+layout['id']+'/back.png').status_code==404
    store.image_path(v['id']).write_bytes(b'corrupt sheet');assert c.get(url).status_code==409
    with store.connection() as con:
        with pytest.raises(sqlite3.IntegrityError):con.execute('DELETE FROM multiview_layouts')


def make_report(c,case,version=None):
    body={'version_id':version or case['versions'][-1]['id'],'request_key':uuid.uuid4().hex};response=c.post('/api/cases/'+case['id']+'/reports',json=body);assert response.status_code==201,response.text
    return response.json(),body


def test_pdf_json_png_contents_persisted_state_and_no_internal_paths(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');text='  Witness’s exact words: dark hair.\nEye color remains uncertain.  ';case=generate(c,freeze(c,new(c),text));case=c.post('/api/cases/'+case['id']+'/clarifications',json={'text':'  Operator addendum — no confirmed beard.  ','source':'operator'}).json()
    before=c.get('/api/cases/'+case['id']).json();report,body=make_report(c,case);pdf=c.get(report['files']['pdf']['url']);assert pdf.status_code==200 and pdf.content.startswith(b'%PDF-')
    path=tmp_path/'actual-report.pdf';path.write_bytes(pdf.content);parsed=subprocess.run(['pdftotext','-layout',str(path),'-'],capture_output=True,text=True,check=True).stdout
    assert 'WitnessTrace AI' in parsed and 'Illustrative Facial Composite Report' in parsed and 'Witness’s exact words: dark hair.' in parsed and 'Eye color remains uncertain.' in parsed
    assert case['id'] in parsed and case['versions'][0]['id'] in parsed and 'Revision history' in parsed and 'Unknown' in parsed and 'Operator addendum' in parsed
    exported=c.get(report['files']['json']['url']).json();assert exported['statements'][0]['text']==text and exported['statements'][1]['source']=='operator'
    assert len(exported['attribute_summary'])==45 and exported['selected_version']['id']==case['versions'][0]['id']
    serialized=json.dumps(exported);assert 'image_path' not in serialized and 'project_url' not in serialized and str(store.DATA) not in serialized and 'codex-response.txt' not in serialized
    png=c.get(report['files']['png']['url']);assert Image.open(io.BytesIO(png.content)).format=='PNG'
    for extension in ['pdf','png','json']:
        data=c.get(report['files'][extension]['url']).content;assert hashlib.sha256(data).hexdigest()==report['files'][extension]['sha256']
        assert case['id'] in report['files'][extension]['filename'] and body['version_id'] in report['files'][extension]['filename']
    preview=c.get(report['preview_url']);assert preview.status_code==200 and 'Witness’s exact words' in preview.text and 'sandbox' not in preview.text
    assert c.get('/api/cases/'+case['id']).json()==before
    # Subsequent persisted modifications cannot rewrite this immutable export snapshot.
    c.post('/api/cases/'+case['id']+'/clarifications',json={'text':'Later clarification excluded from prior report','source':'operator'})
    assert b'Later clarification' not in c.get(report['files']['json']['url']).content
    assert c.post('/api/cases/'+case['id']+'/reports',json=body).json()['id']==report['id']


def test_report_isolation_corrupt_image_failure_rollback_and_json_without_pdf(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));other=freeze(c,new(c));report,body=make_report(c,case)
    assert c.post('/api/cases/'+other['id']+'/reports',json={**body,'request_key':uuid.uuid4().hex}).status_code==404
    assert c.get(report['files']['pdf']['url'].replace(case['id'],other['id'])).status_code==404
    assert c.get(f"/api/cases/{other['id']}/versions/{body['version_id']}/export.json").status_code==404
    before_count=len(c.get('/api/cases/'+case['id']+'/reports').json())
    with monkeypatch.context() as m:
        m.setattr(report_store,'make_pdf',lambda *args:(_ for _ in ()).throw(RuntimeError('fixture report failure')))
        assert c.post('/api/cases/'+case['id']+'/reports',json={**body,'request_key':uuid.uuid4().hex}).status_code==503
    assert len(c.get('/api/cases/'+case['id']+'/reports').json())==before_count
    assert c.get(f"/api/cases/{case['id']}/versions/{body['version_id']}/export.json").status_code==200
    store.image_path(body['version_id']).write_bytes(b'broken source')
    assert c.post('/api/cases/'+case['id']+'/reports',json={**body,'request_key':uuid.uuid4().hex}).status_code==409
    # Previously created export is independent of source damage and remains checksummed.
    assert c.get(report['files']['pdf']['url']).status_code==200
    path,_=report_store.read_file(case['id'],report['id'],'pdf');path.write_bytes(b'broken export')
    assert c.get(report['files']['pdf']['url']).status_code==409


def test_report_post_write_failure_cleanup_and_readable_unicode_policy(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));body={'version_id':case['versions'][0]['id'],'request_key':uuid.uuid4().hex};original_open=Path.open
    def fail(self,*args,**kwargs):
        if self.name=='report.json' and args and args[0]=='xb':raise OSError('explicit fixture partial export failure')
        return original_open(self,*args,**kwargs)
    with monkeypatch.context() as m:
        m.setattr(Path,'open',fail);assert c.post('/api/cases/'+case['id']+'/reports',json=body).status_code==503
    assert c.get('/api/cases/'+case['id']+'/reports').json()==[] and not list(store.DATA.rglob('report.pdf'))
    assert c.post('/api/cases/'+case['id']+'/reports',json=body).status_code==201
    unicode_case=generate(c,freeze(c,new(c),'A fictional adult. Unknown eyes. 漢字'))
    r=c.post('/api/cases/'+unicode_case['id']+'/reports',json={'version_id':unicode_case['versions'][0]['id'],'request_key':uuid.uuid4().hex});assert r.status_code==422
    metadata=c.get(f"/api/cases/{unicode_case['id']}/versions/{unicode_case['versions'][0]['id']}/export.json");assert metadata.status_code==200 and '漢字' in metadata.text


def test_multiview_and_report_fresh_process_persistence(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));case,_=concept(c,case);report,_=make_report(c,case);version=case['versions'][-1]
    code=f'''from fastapi.testclient import TestClient
import app,hashlib
c=TestClient(app.app)
v=c.get('/api/cases/{case['id']}/multiview').json()['requests'][-1]
assert v['status']=='complete' and v['job_id']=='{version['id']}'
assert hashlib.sha256(c.get('/images/{version['id']}').content).hexdigest()=='{version['sha256']}'
r=c.get('/api/cases/{case['id']}/reports').json()[0]
assert r['id']=='{report['id']}'
assert c.get(r['files']['pdf']['url']).content.startswith(b'%PDF-')
print('fresh-process sheets/reports persistence PASS')
'''
    env=os.environ.copy();env['WITNESSTRACE_DATA_DIR']=str(store.DATA);r=subprocess.run([sys.executable,'-c',code],env=env,cwd=Path(app.__file__).parent,capture_output=True,text=True,timeout=30);assert r.returncode==0,r.stderr


def test_report_current_persisted_requests_distinct_from_selected_snapshot(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));draft=copy.deepcopy(case['draft']);draft['attributes']['hair']={'value':'Black','confidence':'tentative','source':'operator','quote':''};case=save(c,case,draft=draft).json()
    report,_=make_report(c,case);data=c.get(report['files']['json']['url']).json()
    assert data['persisted_case_settings']['attributes']['hair']['value']=='Black' and data['selected_attribute_snapshot']['attributes']['hair']['value'] is None
    path=tmp_path/'changed-draft.pdf';path.write_bytes(c.get(report['files']['pdf']['url']).content);text=subprocess.run(['pdftotext',str(path),'-'],capture_output=True,text=True,check=True).stdout
    assert 'Current saved draft changes since selected revision' in text and 'Black' in text and 'not asserted to appear' in text
