"""Final localhost regression. Temporary synthetic data; labelled CLI fixture only.
No credentials, raw CLI logs or generated facial images are written to Git evidence.
"""
import base64,hashlib,io,json,os,secrets,shutil,socket,sqlite3,subprocess,sys,tempfile,time
from PIL import Image
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
LIVE='--live-once' in sys.argv
assert not LIVE, 'Final verification uses labelled fixtures only; use the recorded I3 real-generation evidence.'
checks=[]
def check(name,value=True):
    assert value,name
    checks.append(name); print('PASS '+name,flush=True)
def wait(port):
    for _ in range(150):
        try:
            if httpx.get(f'http://127.0.0.1:{port}/',timeout=.5).status_code in (200,404):return
        except httpx.HTTPError:pass
        time.sleep(.1)
    raise RuntimeError('Local process did not start')
def main():
    for port in [8021,8022,5182]:
        with socket.socket() as s:assert s.connect_ex(('127.0.0.1',port))!=0,'Occupied isolated port'
    processes=[]
    result={'mode':'one real Codex attempt' if LIVE else 'synthetic fake CLI; not AI generation'}
    with tempfile.TemporaryDirectory(prefix='revelio-i3-') as temporary:
        runtime=Path(temporary);runtime.chmod(0o700)
        env=os.environ.copy()
        env.update(WITNESSTRACE_DATA_DIR=str(runtime/'data'),WITNESSTRACE_OUTPUTS_DIR=str(runtime/'outputs'),WITNESSTRACE_WORK_DIR=str(runtime/'work'),REVELIO_DATA_DIR=str(runtime/'accounts'),REVELIO_HOSTED_PROVIDER='',WITNESSTRACE_GATEWAY_TARGET='http://127.0.0.1:8022',REVELIO_API_URL='http://127.0.0.1:8021',REVELIO_GATEWAY_URL='http://127.0.0.1:8021',VITE_WITNESSTRACE_LOCAL='1')
        control=runtime/'fail'
        if not LIVE:
            fake=runtime/'fake-cli'
            fake.write_text(f'''#!{sys.executable}
import sys,os,time
from pathlib import Path
from PIL import Image,ImageDraw
sys.stdin.read();time.sleep(4)
if Path({str(control)!r}).exists():sys.exit(1)
p=Path(os.environ['CODEX_HOME'])/'generated_images'/'fixture.png';p.parent.mkdir(parents=True,exist_ok=True)
im=Image.new('RGB',(720,480),'#d9d3c4');d=ImageDraw.Draw(im)
for x in range(0,720,8):d.line((x,0,720-x,480),fill='#8e725c',width=2)
d.text((20,20),'SYNTHETIC TEST PATTERN - NOT AI',fill='black');im.save(p)
''');fake.chmod(0o700)
            env.update(CODEX_BIN=str(fake),CODEX_HOME=str(runtime/'fake-home'))
        else:
            env.pop('CODEX_BIN',None)
            env.pop('CODEX_HOME',None)
            status=subprocess.run(['codex','login','status'],capture_output=True)
            check('real CLI authentication reported available',status.returncode==0)
        log=open(runtime/'services.log','w')
        def start_witness():
            p=subprocess.Popen([str(ROOT/'witness-backend/start.sh')],cwd=ROOT,env=env,stdout=log,stderr=log);processes.append(p);wait(8022);return p
        try:
            wt=start_witness()
            gateway=subprocess.Popen([str(ROOT/'witness-backend/.venv/bin/python'),'-m','uvicorn','app.main:app','--app-dir',str(ROOT/'backend'),'--host','127.0.0.1','--port','8021'],cwd=ROOT,env=env,stdout=log,stderr=log);processes.append(gateway);wait(8021)
            vite=subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5182','--strictPort'],cwd=ROOT,env=env,stdout=log,stderr=log);processes.append(vite);wait(5182)
            check('unauthenticated gateway rejects cases and images',httpx.get('http://127.0.0.1:5182/wt-api/api/cases').status_code==401 and httpx.get('http://127.0.0.1:5182/wt-api/images/'+'a'*32).status_code==401)
            with sync_playwright() as pw:
                browser=pw.chromium.launch()
                context=browser.new_context(viewport={'width':1440,'height':1000},accept_downloads=True)
                page=context.new_page();exceptions=[];submissions=[]
                page.on('pageerror',lambda e:(exceptions.append(str(e)), print('PAGE ERROR '+str(e),flush=True)))
                page.on('request',lambda r:submissions.append(r.url) if r.method=='POST' and r.url.endswith('/wt-api/api/generate') else None)
                page.goto('http://127.0.0.1:5182/app');page.wait_for_url('**/login**')
                check('workspace preserves login redirect')
                response=context.request.post('http://127.0.0.1:5182/api/auth/register',data={'name':'Synthetic Integration Tester','email':'integration@example.test','password':secrets.token_urlsafe(24)})
                check('real account session created',response.status==201)
                page.goto('http://127.0.0.1:5182/app#/new')
                expect(page.get_by_text('Connected · Codex CLI installed')).to_be_visible(timeout=20000)
                page.locator('#wt-title').fill('I3 synthetic case')
                page.get_by_role('button',name='Create case',exact=True).click()
                expect(page.locator('#wt-description')).to_be_visible()
                testimony='Fictional adult aged about thirty, oval face, short dark hair, brown eyes and a broad nose. This is an invented test description.'
                page.locator('#wt-description').fill(testimony)
                page.get_by_role('button',name='Save original testimony').click()
                expect(page.locator('#wt-description')).to_have_attribute('readonly','')
                check('real case created and original frozen')
                page.get_by_role('button',name='Generate composite',exact=True).evaluate('(el)=>{el.click();el.click()}')
                if not LIVE:
                    expect(page.get_by_role('button',name='Generation running…')).to_be_visible(timeout=10000)
                    page.reload();expect(page.get_by_role('button',name='Generation running…')).to_be_visible(timeout=10000)
                    check('refresh reconnects to existing working job')
                    page.goto('http://127.0.0.1:5182/app#/workspace');page.goto('http://127.0.0.1:5182/app#/new')
                img=page.locator('.viewer__img')
                try:
                    page.wait_for_function("() => document.querySelector('.viewer__img') || document.querySelector('.studio__center [role=status]')?.textContent.includes('failed')", timeout=650000 if LIVE else 25000)
                    expect(img).to_be_visible(timeout=2000 if LIVE else 25000)
                    page.wait_for_function("() => document.querySelector('.viewer__img')?.naturalWidth > 0")
                except Exception:
                    if LIVE:
                        text=page.locator('main').inner_text()
                        result['outcome']='failed or unavailable'
                        # Only known worker classification, never raw subprocess output.
                        private=Path('/home/god/Documents/github/integration-audit-private/i3-live');private.mkdir(parents=True,exist_ok=True,mode=0o700)
                        for response in (runtime/'work').rglob('codex-response.txt'):
                            shutil.copy2(response, private/'codex-response.txt')
                        result['failure_ui']=next((s for s in ['Codex generation failed','timed out','No new image','failed','connection lost'] if s.lower() in text.lower()),'No validated output displayed within deadline')
                        result['submissions']=len(submissions)
                        check('at most one real submission',len(submissions)==1)
                        return
                    raise
                check('exactly one generation POST despite refresh/navigation',len(submissions)==1)
                check('saved image displayed',img.evaluate('(el)=>el.naturalWidth')>=256)
                case_id=page.locator('.studio__ident .wt-id').inner_text()
                saved=context.request.get(f'http://127.0.0.1:5182/wt-api/api/cases/{case_id}').json()
                version=saved['versions'][-1]
                raw=context.request.get('http://127.0.0.1:5182'+img.get_attribute('src')).body()
                check('saved source checksum matches HTTP image',hashlib.sha256(raw).hexdigest()==version['sha256'])
                with page.expect_download() as event:page.get_by_role('button',name='PNG',exact=True).click()
                download=event.value
                exported=Path(download.path()).read_bytes()
                disk=(runtime/'data'/'images'/f"{version['id']}.png")
                # Compare normalized download to canonical export endpoint and raw source separately.
                canonical=context.request.get(f"http://127.0.0.1:5182/wt-api/api/cases/{case_id}/versions/{version['id']}/export.png").body()
                check('download checksum matches saved image export',hashlib.sha256(exported).digest()==hashlib.sha256(canonical).digest())
                if LIVE:
                    result.update(outcome='validated saved image displayed and downloaded',submissions=len(submissions),source_sha256=version['sha256'],export_sha256=hashlib.sha256(exported).hexdigest())
                    return
                page.reload();expect(img).to_be_visible(timeout=20000)
                check('refresh restores original and saved result',page.locator('#wt-description').input_value()==testimony)
                wt.terminate();wt.wait(timeout=10);wt=start_witness()
                page.get_by_role('button',name='Reconnect / reload cases').click();expect(img).to_be_visible()
                check('server restart retains saved case and image')
                for theme in ['dark','light']:
                    page.evaluate('(theme)=>{document.documentElement.dataset.theme=theme;localStorage.setItem("revelio.theme",theme)}',theme)
                    for width in [1920,1440,1280,768,390]:
                        page.set_viewport_size({'width':width,'height':1000});page.wait_for_timeout(250)
                        overflow=page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
                        check(f'{theme} {width}px no horizontal page overflow',not overflow)
                        page.screenshot(path=str(OUT/f'studio-{theme}-{width}.png'),full_page=True)
                page.set_viewport_size({'width':1440,'height':1000})
                page.get_by_role('button',name='Zoom in',exact=True).click();check('viewer zoom control works','125%' in page.locator('.viewer__zoom').inner_text())
                page.get_by_role('button',name='Fit to screen',exact=True).click()
                # All further generated images are explicitly labelled synthetic fixtures.
                page.locator('summary').filter(has_text='Structure & Shape').click()
                page.locator('#trait-face_width').fill('65')
                page.get_by_role('button',name='Save draft',exact=True).click()
                page.wait_for_timeout(500)
                page.reload();expect(page.locator('#wt-description')).to_be_visible(timeout=20000)
                page.locator('summary').filter(has_text='Structure & Shape').click()
                expect(page.locator('#trait-face_width')).to_have_value('65')
                schema=context.request.get('http://127.0.0.1:5182/wt-api/api/lab-schema').json()
                check('45 attributes in seven groups',len(schema['groups'])==7 and sum(len(g['fields']) for g in schema['groups'])==45)
                check('Character Lab draft persists across refresh')
                page.get_by_role('button',name='Review prompt',exact=True).click()
                expect(page.get_by_role('button',name='Update Preview',exact=True)).to_be_enabled()
                page.get_by_role('button',name='Update Preview',exact=True).click()
                page.wait_for_timeout(6000)
                page.reload();expect(img).to_be_visible(timeout=20000)
                record=context.request.get(f'http://127.0.0.1:5182/wt-api/api/cases/{case_id}').json()
                check('explicit Lab generation saved',record['versions'][-1]['workspace']=='lab')
                page.get_by_label('Refinement instructions',exact=True).fill('Slightly narrow the nose.')
                page.get_by_role('button',name='Review refinement prompt',exact=True).click()
                expect(page.get_by_role('button',name='Generate refinement',exact=True)).to_be_enabled()
                page.get_by_role('button',name='Generate refinement',exact=True).click()
                page.wait_for_timeout(6000)
                page.reload();expect(img).to_be_visible(timeout=20000)
                record=context.request.get(f'http://127.0.0.1:5182/wt-api/api/cases/{case_id}').json()
                check('refinement creates immutable child',record['versions'][-1]['workspace']=='refinement' and bool(record['versions'][-1]['parent_id']))
                page.goto('http://127.0.0.1:5182/app#/compare')
                expect(page.get_by_role('slider',name='Comparison divider')).to_be_visible(timeout=20000)
                page.get_by_role('slider',name='Comparison divider').press('ArrowRight')
                check('comparison keyboard operation',page.get_by_role('slider',name='Comparison divider').get_attribute('aria-valuenow')=='55')
                page.get_by_role('button',name='Set preferred',exact=True).last.click()
                page.wait_for_timeout(400)
                page.goto('http://127.0.0.1:5182/app#/new')
                expect(img).to_be_visible(timeout=20000)
                page.get_by_role('button',name='Digital Sketchpad',exact=True).click()
                frame=page.frame_locator('iframe[title="WitnessTrace image editing"]')
                expect(frame.locator('#sketch-canvas')).to_be_visible(timeout=20000)
                page.wait_for_timeout(1000)
                canvas=frame.locator('#sketch-canvas');canvas.scroll_into_view_if_needed();box=canvas.bounding_box()
                print('Sketch state '+frame.locator('#sketch-status').inner_text(),flush=True)
                page.mouse.move(box['x']+box['width']*.4,box['y']+box['height']*.4)
                page.mouse.down();page.mouse.move(box['x']+box['width']*.6,box['y']+box['height']*.6,steps=10);page.mouse.up()
                page.screenshot(path=str(OUT/'sketch-edit.png'),full_page=True)
                print('Sketch after '+frame.locator('#sketch-status').inner_text(),flush=True)
                expect(frame.locator('#sketch-save')).to_be_enabled(timeout=10000)
                frame.locator('body').evaluate("() => { window.qaCanvasMarker = 'retained' }")
                page.goto('http://127.0.0.1:5182/app#/library')
                expect(page.get_by_role('heading',name='Case library',exact=True)).to_be_visible(timeout=10000)
                page.goto('http://127.0.0.1:5182/app#/new')
                expect(frame.locator('#sketch-save')).to_be_enabled(timeout=10000)
                check('canvas and handlers survive hash navigation',frame.locator('body').evaluate("() => window.qaCanvasMarker")=='retained')
                frame.locator('#sketch-save').click()
                expect(frame.locator('#sketch-save-status')).to_contain_text('Saved',timeout=15000)
                check('original Sketchpad engine saves annotation')
                page.get_by_role('button',name='Enhance',exact=True).click()
                expect(frame.locator('#enhance-save')).to_be_visible(timeout=15000)
                page.wait_for_timeout(1000)
                brightness=frame.locator('input[type=range]').filter(visible=True) if False else frame.locator('#enhance-brightness')
                # Schema-built engine controls use enhance-param-<key> IDs.
                ranges=frame.locator('#enhance-controls input[type=range]')
                print('Enhance controls '+str(ranges.count()),flush=True)
                ranges.first.fill('20')
                expect(frame.locator('#enhance-save')).to_be_enabled(timeout=15000)
                preview=frame.locator('#enhance-canvas').evaluate('(canvas)=>canvas.toDataURL()')
                frame.locator('#enhance-save').click()
                expect(frame.locator('#enhance-status')).to_contain_text('Saved Enhanced Version',timeout=15000)
                check('enhancement saves committed preview')
                enhanced=context.request.get(f'http://127.0.0.1:5182/wt-api/api/cases/{case_id}').json()['versions'][-1]
                saved_pixels=context.request.get('http://127.0.0.1:5182/wt-api'+enhanced['image_url']).body()
                shown=Image.open(io.BytesIO(base64.b64decode(preview.split(',')[1]))).convert('RGBA')
                stored=Image.open(io.BytesIO(saved_pixels)).convert('RGBA')
                check('enhancement preview equals saved pixels',shown.size==stored.size and shown.tobytes()==stored.tobytes())
                page.screenshot(path=str(OUT/'enhance-light.png'),full_page=True)
                page.get_by_role('button',name='Reload saved revisions',exact=True).click()
                page.wait_for_timeout(500)
                page.get_by_role('button',name='Create PDF report',exact=True).click()
                expect(page.get_by_role('link',name='Download PDF',exact=True)).to_be_visible(timeout=15000)
                for ext in ['PDF','JSON','PNG']:
                    link=page.get_by_role('link',name='Download '+ext,exact=True).last
                    response=context.request.get('http://127.0.0.1:5182'+link.get_attribute('href'))
                    check('persisted report '+ext+' download',response.status==200 and len(response.body())>100)
                record=context.request.get(f'http://127.0.0.1:5182/wt-api/api/cases/{case_id}').json()
                check('editing lineage and testimony retained',record['versions'][-1]['workspace']=='enhance' and record['statements'][0]['text']==testimony)
                # Exercise preserved angle-sheet controls with a labelled fixture, never an AI claim.
                page.locator('summary').filter(has_text='Multi-view workspace').click()
                multi=page.frame_locator('iframe[title="WitnessTrace multi-view and reports"]')
                expect(multi.locator('#multi-review')).to_be_enabled(timeout=15000)
                multi.locator('#multi-review').click()
                expect(multi.locator('#multi-generate')).to_be_enabled(timeout=10000)
                multi.locator('#multi-generate').click()
                expect(multi.locator('#multi-layout')).to_be_enabled(timeout=20000)
                multi.locator('#multi-layout').click()
                multi.locator('#layout-guide').click()
                multi.locator('#layout-note').fill('Synthetic test geometry only, not reviewed facial poses.')
                multi.locator('#layout-checked').check()
                multi.locator('#layout-save').scroll_into_view_if_needed()
                page.screenshot(path=str(OUT/'layout-review.png'),full_page=True)
                multi.locator('#layout-save').click()
                expect(multi.locator('#layout-dialog')).not_to_be_visible(timeout=10000)
                expect(multi.locator('#multi-angle-buttons button')).to_have_count(4)
                multi.locator('#multi-angle-buttons button').first.click()
                multi.locator('#multi-next').click()
                check('multi-view fixture generates and reviewed crop navigation works')
                crop=multi.locator('#multi-download').get_attribute('href')
                check('reviewed angle download authenticated',context.request.get('http://127.0.0.1:5182'+crop).status==200)
                page.screenshot(path=str(OUT/'multiview.png'),full_page=True)
                # Completed local edits and sheets must survive process restart too.
                wt.terminate();wt.wait(timeout=10);wt=start_witness()
                persisted=context.request.get(f'http://127.0.0.1:5182/wt-api/api/cases/{case_id}').json()
                check('all revisions survive restart',len(persisted['versions'])==6 and persisted['statements'][0]['text']==testimony)
                page.reload();expect(img).to_be_visible(timeout=20000)
                result['fixture_generation_jobs']=len(persisted['jobs'])
                result['saved_revision_count']=len(persisted['versions'])
                for revision in persisted['versions']:
                    image=context.request.get('http://127.0.0.1:5182/wt-api'+revision['image_url']).body()
                    assert hashlib.sha256(image).hexdigest()==revision['sha256']
                reports=context.request.get(f'http://127.0.0.1:5182/wt-api/api/cases/{case_id}/reports').json()
                for export in reports[0]['files'].values():
                    content=context.request.get('http://127.0.0.1:5182/wt-api'+export['url']).body()
                    assert hashlib.sha256(content).hexdigest()==export['sha256']
                check('all six revision and report file checksums verify')
                with sqlite3.connect(runtime/'data/witness.sqlite3') as db:
                    check('SQLite integrity and foreign keys',db.execute('PRAGMA integrity_check').fetchone()[0]=='ok' and not db.execute('PRAGMA foreign_key_check').fetchall())
                for route,title in [('workspace','Recent case images'),('library','Case library'),('compare','Compare saved revisions'),('settings','Application settings')]:
                    page.goto('http://127.0.0.1:5182/app#/'+route)
                    page.wait_for_timeout(500)
                    check('navigation '+route, page.locator('main').is_visible())
                    page.screenshot(path=str(OUT/(route+'.png')),full_page=True)
                for theme in ['dark','light']:
                    page.evaluate('(theme)=>{document.documentElement.dataset.theme=theme;localStorage.setItem("revelio.theme",theme)}',theme)
                    for width in [1920,1440,1280,768,390]:
                        page.set_viewport_size({'width':width,'height':1000});page.wait_for_timeout(100)
                        check(f'settings {theme} {width}px no overflow',not page.evaluate('document.documentElement.scrollWidth > innerWidth'))
                        page.screenshot(path=str(OUT/f'settings-{theme}-{width}.png'),full_page=True)
                page.set_viewport_size({'width':1440,'height':1000})
                page.goto('http://127.0.0.1:5182/app#/new');expect(img).to_be_visible(timeout=15000)
                updated=persisted
                missing=context.request.get('http://127.0.0.1:5182/wt-api/api/cases/'+'f'*32)
                check('unknown case returns 404',missing.status==404)
                invalid=context.request.post(f'http://127.0.0.1:5182/wt-api/api/cases/{case_id}/freeze',data={'revision':updated['revision'],'text':'short'})
                check('invalid description is rejected',invalid.status==422)
                page.locator('#wt-clarify').fill('Entirely fictional clarification for integration verification.')
                page.get_by_role('button',name='Add clarification',exact=True).click()
                expect(page.get_by_role('button',name='Generate composite',exact=True)).to_be_enabled()
                clarified=context.request.get(f'http://127.0.0.1:5182/wt-api/api/cases/{case_id}').json()
                check('clarification appends without changing original',len(clarified['statements'])==2 and clarified['statements'][0]['text']==testimony)
                page.locator('#wt-title').fill('Second synthetic case')
                page.get_by_role('button',name='Create case',exact=True).click()
                expect(page.locator('#wt-description')).to_have_value('')
                check('case switch clears unsaved input')
                page.locator('#wt-case').select_option(case_id)
                expect(page.locator('#wt-description')).to_have_value(testimony)
                check('case list and selection restore correct record')
                wt.terminate();wt.wait(timeout=10)
                page.get_by_role('button',name='Reconnect / reload cases').click();expect(page.get_by_text('Backend not connected')).to_be_visible(timeout=15000)
                check('backend unavailable is recoverable UI state')
                check('zero JavaScript page exceptions',not exceptions)
                result.update(outcome='passed',screenshots=len(list(OUT.glob('*.png'))),submissions=len(submissions),checks=checks)
                browser.close()
        finally:
            for p in reversed(processes):
                if p.poll() is None:p.terminate();p.wait(timeout=15)
            log.close()
            result['checks']=checks;result['owned_services_stopped']=True
            (OUT/('live-result.json' if LIVE else 'browser-result.json')).write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
