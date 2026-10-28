"""Local-edit backend tests: isolated fake CLI + PNG fixtures, never live AI."""
import base64
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
from fastapi.testclient import TestClient
import pytest
import app
import case_store as store
from test_app import _setup
from test_cases import new,freeze
from test_refinement import generate,payload,refine


def png(size=(512,512),color='red'):
    out=io.BytesIO();Image.new('RGBA',size,color).save(out,format='PNG')
    return 'data:image/png;base64,'+base64.b64encode(out.getvalue()).decode()

def body(case,operations=None,size=(512,512),parent=None,source=None):
    return {'parent_id':parent or case['versions'][-1]['id'],'request_key':uuid.uuid4().hex,'png':png(size),'project':{'schema_version':1,'source_version_id':source or case['versions'][-1]['id'],'operations':operations or [{'tool':'line','points':[[5,5,1],[40,40,1]],'width':4,'color':'#ff0000','opacity':1}]}}

def test_local_save_lineage_bytes_metadata_testimony_and_reopen(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));v1=case['versions'][0];original_bytes=c.get(v1['image_url']).content;request=body(case)
    result=c.post('/api/cases/'+case['id']+'/local-edits',json=request);assert result.status_code==201,result.text
    saved=result.json();record=c.get('/api/cases/'+case['id']).json();v=record['versions'][-1]
    assert len(record['versions'])==2 and v['parent_id']==v1['id'] and v['id']==saved['version_id']
    assert v['mode']==v['creation_kind']=='local_canvas_edit' and v['modified_illustration'] and v['generation_job_id'] is None and v['source']=='artist'
    assert v['workspace']=='sketch' and v['outcome']=='saved'
    assert record['statements']==case['statements'] and record['last_generated_draft']==case['last_generated_draft']
    image=c.get(v['image_url']);assert image.status_code==200 and hashlib.sha256(image.content).hexdigest()==v['sha256']==saved['sha256']
    assert c.get(v1['image_url']).content==original_bytes
    opened=c.get(f"/api/cases/{case['id']}/versions/{v['id']}/sketch").json();assert opened['modified_illustration'] and opened['project']['source_version_id']==v1['id']
    assert opened['project']['operations'][0]['tool']=='line'
    with store.connection() as con:
        with pytest.raises(sqlite3.IntegrityError):con.execute('DELETE FROM local_edits')
    # A local save must not touch or lock the AI-generation adapter.
    assert not app._guard.locked() and len(record['refinements'])==0


def test_local_edit_case_isolation_and_source_validation(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));other=generate(c,freeze(c,new(c)));request=body(case)
    assert c.post('/api/cases/'+other['id']+'/local-edits',json=request).status_code==404
    assert c.get(f"/api/cases/{other['id']}/versions/{case['versions'][0]['id']}/sketch").status_code==404
    request['project']['source_version_id']=other['versions'][0]['id'];assert c.post('/api/cases/'+case['id']+'/local-edits',json=request).status_code==404
    case=generate(c,case);request=body(case,source=case['versions'][0]['id'])
    assert c.post('/api/cases/'+case['id']+'/local-edits',json=request).status_code==422
    assert len(c.get('/api/cases/'+case['id']).json()['versions'])==2


def test_png_validation_crop_transform_dimensions_and_project_limits(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));path='/api/cases/'+case['id']+'/local-edits';request=body(case)
    for invalid in ['data:image/jpeg;base64,'+request['png'].split(',')[1],'data:image/png;base64,notbase64','data:image/png;base64,'+base64.b64encode(b'not a PNG'*20).decode()]:
        assert c.post(path,json={**request,'png':invalid}).status_code==422
    for size in [(20,100),(600,512)]:assert c.post(path,json={**request,'png':png(size)}).status_code==422
    for operation in [{'tool':'crop','rect':[500,0,200,100]},{'tool':'crop','rect':[0,0,1,100]},{'tool':'line','points':[[0,0,1],[513,0,1]]},{'tool':'text','points':[[5,5,1]],'text':''},{'tool':'liquify'},{'tool':'line','points':[[0,0,1],[10,10,1]],'color':'url(bad)'}]:
        bad=copy.deepcopy(request);bad['project']['operations']=[operation];assert c.post(path,json=bad).status_code==422
    crop=body(case,[{'tool':'crop','rect':[20,30,240,320]},{'tool':'rotate'},{'tool':'flip'}],size=(320,240))
    response=c.post(path,json=crop);assert response.status_code==201,response.text
    record=c.get('/api/cases/'+case['id']).json();v=record['versions'][-1];assert (v['width'],v['height'])==(320,240)
    # PNG that claims valid dimensions but has truncated pixel stream must fail decode.
    bad=copy.deepcopy(request);data=base64.b64decode(bad['png'].split(',')[1]);bad['png']='data:image/png;base64,'+base64.b64encode(data[:-30]).decode()
    assert c.post(path,json=bad).status_code==422


def test_local_idempotency_concurrent_retry_and_collision_cleanup(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));request=body(case);path='/api/cases/'+case['id']+'/local-edits'
    with ThreadPoolExecutor(max_workers=2) as executor:responses=list(executor.map(lambda _:c.post(path,json=request),range(2)))
    assert all(r.status_code==201 for r in responses)
    assert responses[0].json()['version_id']==responses[1].json()['version_id']
    assert len(c.get('/api/cases/'+case['id']).json()['versions'])==2
    assert c.post(path,json={**request,'png':png(color='blue')}).status_code==409
    # A filesystem collision is a failed save, never overwrite/delete the existing image.
    version_id=uuid.uuid4().hex;target=store.safe_path(case['id'],version_id,'.png');target.write_bytes(b'untouched collision fixture')
    monkeypatch.setattr(app.sketch_store.uuid,'uuid4',lambda:type('ID',(),{'hex':version_id})())
    request['request_key']='e'*32
    assert c.post(path,json=request).status_code==503
    assert target.read_bytes()==b'untouched collision fixture'
    assert len(c.get('/api/cases/'+case['id']).json()['versions'])==2
    assert not list(target.parent.glob('*.tmp'))


def test_saved_layers_can_branch_and_ai_refinement_does_not_claim_pixels(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));v1=case['versions'][0];request=body(case)
    r=c.post('/api/cases/'+case['id']+'/local-edits',json=request).json();local_id=r['version_id']
    project=c.get(f"/api/cases/{case['id']}/versions/{local_id}/sketch").json()['project'];project['operations'].append({'tool':'text','points':[[60,70,1]],'text':'artist note','width':4,'color':'#111111','opacity':1})
    second={**request,'parent_id':local_id,'request_key':uuid.uuid4().hex,'project':project};r=c.post('/api/cases/'+case['id']+'/local-edits',json=second);assert r.status_code==201,r.text
    case=c.get('/api/cases/'+case['id']).json();assert case['versions'][-1]['parent_id']==local_id
    ai=payload(c,case,instruction='Make the nose longer. Preserve other requested characteristics.')
    assert 'artist note' not in ai['reviewed_prompt'] and 'Text-only regeneration' in ai['reviewed_prompt']
    case=refine(c,case,ai);assert case['versions'][-1]['parent_id']==r.json()['version_id'] and case['versions'][-1]['mode']=='prompt_regeneration'
    assert len(case['statements'])==1 and len(case['refinements'])==1
    assert c.get(v1['image_url']).status_code==200


def test_local_save_fresh_process_restart_integrity_and_missing_parent(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));response=c.post('/api/cases/'+case['id']+'/local-edits',json=body(case)).json();version_id=response['version_id']
    code=f'''from fastapi.testclient import TestClient
import app,hashlib
c=TestClient(app.app)
r=c.get('/api/cases/{case['id']}').json()
assert r['selected_version_id']=='{version_id}'
p=c.get('/api/cases/{case['id']}/versions/{version_id}/sketch')
assert p.status_code==200 and p.json()['project']['operations'][0]['tool']=='line'
assert hashlib.sha256(c.get('/images/{version_id}').content).hexdigest()=='{response['sha256']}'
print('fresh process editable sketch persistence PASS')
'''
    env=os.environ.copy();env['WITNESSTRACE_DATA_DIR']=str(store.DATA)
    run=subprocess.run([sys.executable,'-c',code],env=env,cwd=Path(app.__file__).parent,capture_output=True,text=True,timeout=30);assert run.returncode==0,run.stderr
    store.image_path(version_id).write_bytes(b'corrupted bytes')
    assert c.get(f"/api/cases/{case['id']}/versions/{version_id}/sketch").status_code==409
    case=c.get('/api/cases/'+case['id']).json();assert c.post('/api/cases/'+case['id']+'/local-edits',json=body(case,source=case['versions'][0]['id'])).status_code==409



def test_local_filesystem_failure_preserves_history_and_retry(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));request=body(case);path='/api/cases/'+case['id']+'/local-edits'
    original_open=Path.open
    def fail_write(self,*args,**kwargs):
        if self.suffix=='.tmp':raise OSError('explicit fixture disk failure')
        return original_open(self,*args,**kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(Path,'open',fail_write)
        failed=c.post(path,json=request);assert failed.status_code==503
        assert 'fixture disk failure' not in failed.text
    assert len(c.get('/api/cases/'+case['id']).json()['versions'])==1
    assert c.post(path,json=request).status_code==201
    assert len(c.get('/api/cases/'+case['id']).json()['versions'])==2
