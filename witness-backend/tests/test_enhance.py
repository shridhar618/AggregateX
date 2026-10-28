"""Phase 06 local image fixtures only; fake CLI where AI regression is exercised."""
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
import pytest
from fastapi.testclient import TestClient
import app
import case_store as store
import enhance_store as enhance
from test_cases import new,freeze
from test_app import _setup
from test_refinement import generate


def image_data(format='PNG',size=(128,96),orientation=None,color=(70,110,150)):
    out=io.BytesIO();im=Image.new('RGB',size,color)
    if orientation:
        exif=Image.Exif();exif[274]=orientation;exif[270]='Private metadata fixture';im.save(out,format=format,exif=exif)
    else:im.save(out,format=format)
    return 'data:image/'+{'PNG':'png','JPEG':'jpeg','WEBP':'webp'}[format]+';base64,'+base64.b64encode(out.getvalue()).decode()


def upload(c,case,format='PNG',**kwargs):
    body={'request_key':uuid.uuid4().hex,'image':image_data(format,**kwargs),'filename':'../../Source.'+format.lower(),'consent':True}
    response=c.post('/api/cases/'+case['id']+'/imports',json=body);assert response.status_code==201,response.text
    return response.json(),body


def adjustment_body(version_id,**kwargs):
    return {'request_key':uuid.uuid4().hex,'parent_id':version_id,'source_id':version_id,'png':image_data(), 'adjustments':enhance.Adjustments(**kwargs).model_dump(),'engine':'rgba-worker-v1'}


def test_upload_all_formats_original_bytes_and_metadata_safety():
    c=TestClient(app.app);case=freeze(c,new(c));original=case['statements']
    for format in ['PNG','JPEG','WEBP']:
        result,body=upload(c,case,format,orientation=6)
        record=c.get('/api/cases/'+case['id']).json();v=record['versions'][-1]
        assert v['id']==result['version_id'] and v['mode']=='uploaded_source' and v['generation_job_id'] is None and v['parent_id'] is None
        assert v['source_filename']=='Source.'+format.lower() and (v['width'],v['height'])==(96,128)
        assert c.get(v['image_url']).content==base64.b64decode(body['image'].split(',')[1])
        assert hashlib.sha256(c.get(v['image_url']).content).hexdigest()==result['sha256']
        normalized=c.get(f"/api/cases/{case['id']}/versions/{v['id']}/pixels")
        with Image.open(io.BytesIO(normalized.content)) as im:
            assert im.size==(96,128) and not im.getexif() and not im.info.get('exif') and im.format=='PNG'
        assert record['statements']==original and record['last_generated_draft'] is None


def test_import_rejects_corrupt_oversize_animated_mime_and_unsafe_case(tmp_path):
    c=TestClient(app.app);case=freeze(c,new(c));valid={'request_key':uuid.uuid4().hex,'image':image_data(),'filename':'fixture.png','consent':True};path='/api/cases/'+case['id']+'/imports'
    bads=['data:image/png;base64,not-base64','data:image/png;base64,'+base64.b64encode(b'broken'*30).decode(),valid['image'].replace('image/png','image/jpeg'),image_data(size=(20,100)),image_data(size=(4001,4000))]
    for image in bads:assert c.post(path,json={**valid,'image':image}).status_code==422
    animated=io.BytesIO();a=Image.new('RGB',(64,64),'red');a.save(animated,format='WEBP',save_all=True,append_images=[Image.new('RGB',(64,64),'blue')],duration=100)
    assert c.post(path,json={**valid,'image':'data:image/webp;base64,'+base64.b64encode(animated.getvalue()).decode()}).status_code==422
    assert c.post(path,json={**valid,'consent':False}).status_code==422
    unfrozen=new(c);assert c.post('/api/cases/'+unfrozen['id']+'/imports',json=valid).status_code==409
    assert c.post('/api/cases/not-an-id/imports',json=valid).status_code==404
    assert c.get('/api/cases/'+case['id']).json()['versions']==[]


def test_enhance_saved_pixels_parameters_immutability_parent_and_baseline(tmp_path,monkeypatch):
    c=_setup(tmp_path,monkeypatch,'success');case=generate(c,freeze(c,new(c)));baseline=case['last_generated_draft'];v1=case['versions'][-1]
    body=adjustment_body(v1['id'],brightness=20,contrast=10);body['png']=image_data(size=(512,512),orientation=1)
    response=c.post('/api/cases/'+case['id']+'/enhancements',json=body);assert response.status_code==201,response.text
    record=c.get('/api/cases/'+case['id']).json();v=record['versions'][-1]
    assert v['parent_id']==v1['id'] and v['mode']=='local_enhancement' and v['workspace']=='enhance'
    assert v['adjustments']['brightness']==20 and v['engine']=='rgba-worker-v1' and v['source_id']==v1['id']
    assert v['generation_job_id'] is None and record['last_generated_draft']==baseline
    saved=c.get(v['image_url']).content
    with Image.open(io.BytesIO(saved)) as im:
        assert not im.getexif();assert im.convert('RGBA').tobytes()==Image.open(io.BytesIO(base64.b64decode(body['png'].split(',')[1]))).convert('RGBA').tobytes()
    assert hashlib.sha256(saved).hexdigest()==v['sha256']
    reopened=c.get(f"/api/cases/{case['id']}/versions/{v['id']}/enhance").json();assert reopened['source_id']==v1['id'] and reopened['adjustments']==body['adjustments']
    with store.connection() as con:
        with pytest.raises(sqlite3.IntegrityError):con.execute('DELETE FROM image_operations')
    assert record['statements']==case['statements'] and not app._guard.locked()


def test_ownership_root_integrity_validation_and_resize():
    c=TestClient(app.app);case=freeze(c,new(c));other=freeze(c,new(c));v,_=upload(c,case);foreign,_=upload(c,other)
    body=adjustment_body(v['version_id'],resize=50);body['png']=image_data(size=(64,48));path='/api/cases/'+case['id']+'/enhancements'
    assert c.post(path,json=body).status_code==201
    record=c.get('/api/cases/'+case['id']).json();saved=record['versions'][-1]
    nested={**body,'parent_id':saved['id'],'request_key':uuid.uuid4().hex};assert c.post(path,json=nested).status_code==201
    assert c.post('/api/cases/'+other['id']+'/enhancements',json=body).status_code==404
    assert c.get(f"/api/cases/{other['id']}/versions/{v['version_id']}/pixels").status_code==404
    assert c.post(path,json={**body,'request_key':uuid.uuid4().hex,'source_id':foreign['version_id']}).status_code==404
    assert c.post(path,json={**body,'request_key':uuid.uuid4().hex,'png':image_data()}).status_code==422
    for invalid in [{'gamma':0},{'exposure':4},{'contrast':100},{'resize':200},{'blur':6}]:
        assert c.post(path,json={**body,'adjustments':invalid}).status_code==422
    # A version from the same case still cannot silently substitute a different root.
    extra,_=upload(c,case)
    assert c.post(path,json={**body,'parent_id':extra['version_id'],'request_key':uuid.uuid4().hex}).status_code==422
    store.image_path(v['version_id']).write_bytes(b'broken original')
    assert c.get(f"/api/cases/{case['id']}/versions/{v['version_id']}/pixels").status_code==409


def test_idempotent_import_and_enhance_concurrency_failure_retry(tmp_path,monkeypatch):
    c=TestClient(app.app);case=freeze(c,new(c));valid={'request_key':uuid.uuid4().hex,'image':image_data(),'filename':'fixture.png','consent':True};path='/api/cases/'+case['id']+'/imports'
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:c.post(path,json=valid),range(2)))
    assert all(r.status_code==201 for r in results) and results[0].json()['version_id']==results[1].json()['version_id']
    assert c.post(path,json={**valid,'filename':'different.png'}).status_code==409
    body=adjustment_body(results[0].json()['version_id'],gamma=1.2);savepath='/api/cases/'+case['id']+'/enhancements'
    original_open=Path.open
    def fail(self,*args,**kwargs):
        if self.suffix=='.tmp':raise OSError('fixture-only disk failure detail')
        return original_open(self,*args,**kwargs)
    with monkeypatch.context() as m:
        m.setattr(Path,'open',fail);r=c.post(savepath,json=body);assert r.status_code==503 and 'fixture-only' not in r.text
    assert len(c.get('/api/cases/'+case['id']).json()['versions'])==1
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:c.post(savepath,json=body),range(2)))
    assert all(r.status_code==201 for r in results) and results[0].json()['version_id']==results[1].json()['version_id']
    assert len(c.get('/api/cases/'+case['id']).json()['versions'])==2
    assert not list(store.DATA.rglob('*.tmp'))


def test_exif_upload_sketch_integration_and_fresh_process_restart(tmp_path):
    c=TestClient(app.app);case=freeze(c,new(c));v,_=upload(c,case,'JPEG',orientation=6)
    project=c.get(f"/api/cases/{case['id']}/versions/{v['version_id']}/sketch").json()
    assert project['source_url'].endswith('/pixels')
    request={'parent_id':v['version_id'],'request_key':uuid.uuid4().hex,'png':image_data(size=(96,128)),'project':{'schema_version':1,'source_version_id':v['version_id'],'operations':[{'tool':'pencil','points':[[10,10,1]]}]}}
    assert c.post('/api/cases/'+case['id']+'/local-edits',json=request).status_code==201
    body=adjustment_body(v['version_id'],gamma=1.3);body['png']=image_data(size=(96,128));result=c.post('/api/cases/'+case['id']+'/enhancements',json=body);assert result.status_code==201
    saved=result.json();code=f'''from fastapi.testclient import TestClient
import app,hashlib
c=TestClient(app.app)
v=c.get('/api/cases/{case['id']}').json()['versions'][-1]
assert v['id']=='{saved['version_id']}' and v['parent_id']=='{v['version_id']}'
assert hashlib.sha256(c.get(v['image_url']).content).hexdigest()=='{saved['sha256']}'
assert c.get('/api/cases/{case['id']}/versions/{saved['version_id']}/enhance').json()['adjustments']['gamma']==1.3
print('fresh-process imports/enhancement persistence PASS')
'''
    env=os.environ.copy();env['WITNESSTRACE_DATA_DIR']=str(store.DATA)
    r=subprocess.run([sys.executable,'-c',code],env=env,cwd=Path(app.__file__).parent,capture_output=True,text=True,timeout=30);assert r.returncode==0,r.stderr


def test_presets_documented_valid_and_all_controls_unknown_witness_unchanged():
    c=TestClient(app.app);schema=c.get('/api/enhance-schema').json();assert len(schema['presets'])==5 and len(schema['controls'])==11
    assert schema['defaults']==enhance.Adjustments().model_dump()
    for preset in schema['presets'].values():assert enhance.Adjustments(**preset['values']).model_dump()==preset['values'] and preset['values']!=schema['defaults']
    case=freeze(c,new(c));v,_=upload(c,case);record=c.get('/api/cases/'+case['id']).json()
    assert record['draft']==case['draft'] and all(a['value'] is None for a in record['draft']['attributes'].values())



def test_post_write_database_failure_rolls_back_files_rows_and_retries(monkeypatch):
    c=TestClient(app.app);case=freeze(c,new(c));v,_=upload(c,case);body=adjustment_body(v['version_id'],brightness=12)
    original_files={str(p) for p in store.DATA.rglob('*.png')}
    def fail_event(*args,**kwargs):raise sqlite3.OperationalError('explicit test DB failure after file write')
    with monkeypatch.context() as m:
        m.setattr(store,'event',fail_event)
        response=c.post('/api/cases/'+case['id']+'/enhancements',json=body)
        assert response.status_code==503 and 'explicit test DB failure' not in response.text
    record=c.get('/api/cases/'+case['id']).json();assert len(record['versions'])==1 and len(record['jobs'])==1
    assert {str(p) for p in store.DATA.rglob('*.png')}==original_files and not list(store.DATA.rglob('*.tmp'))
    assert c.post('/api/cases/'+case['id']+'/enhancements',json=body).status_code==201
