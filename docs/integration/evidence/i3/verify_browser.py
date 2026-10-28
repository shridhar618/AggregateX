"""I3 localhost integration. Temporary synthetic data; fake CLI unless --live-once.
No credentials, raw CLI logs or generated facial images are written to Git evidence.
"""
import hashlib,json,os,secrets,shutil,socket,subprocess,sys,tempfile,time
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
LIVE='--live-once' in sys.argv
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
                page.on('pageerror',lambda e:exceptions.append(type(e).__name__))
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
                    for width in [1440,1280,768,390]:
                        page.set_viewport_size({'width':width,'height':1000});page.wait_for_timeout(250)
                        overflow=page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
                        check(f'{theme} {width}px no horizontal page overflow',not overflow)
                        page.screenshot(path=str(OUT/f'studio-{theme}-{width}.png'),full_page=True)
                page.set_viewport_size({'width':1440,'height':1000})
                page.get_by_role('button',name='Zoom in',exact=True).click();check('viewer zoom control works','125%' in page.locator('.viewer__zoom').inner_text())
                page.get_by_role('button',name='Fit to screen',exact=True).click()
                # Missing image must produce a visible error without deleting the revision.
                page.route('**/wt-api/images/**',lambda route:route.fulfill(status=404,body='missing'))
                page.reload();expect(page.get_by_text('Saved image could not be loaded.',exact=False)).to_be_visible(timeout=15000)
                check('missing image is visible failure')
                page.unroute('**/wt-api/images/**');page.reload();expect(img).to_be_visible(timeout=15000)
                # Explicit second fixture request fails; original saved image is retained.
                control.touch();page.get_by_role('button',name='Generate composite',exact=True).click()
                expect(page.get_by_role('button',name='Generation running…')).to_be_visible()
                expect(page.get_by_role('button',name='Generate composite',exact=True)).to_be_visible(timeout=20000)
                updated=context.request.get(f'http://127.0.0.1:5182/wt-api/api/cases/{case_id}').json()
                check('failed fixture job creates no successful revision',len(updated['versions'])==1 and updated['jobs'][-1]['status']=='failed')
                check('prior validated image retained after failure',img.count()==1)
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
                result.update(outcome='passed',screenshots=8,submissions=len(submissions),checks=checks)
                browser.close()
        finally:
            for p in reversed(processes):
                if p.poll() is None:p.terminate();p.wait(timeout=15)
            log.close()
            result['checks']=checks;result['owned_services_stopped']=True
            (OUT/('live-result.json' if LIVE else 'browser-result.json')).write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
