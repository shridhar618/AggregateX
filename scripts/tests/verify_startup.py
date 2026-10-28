import os,secrets,socket,subprocess,tempfile,time,json
from pathlib import Path
import httpx
from playwright.sync_api import sync_playwright,expect
root=Path.cwd();checks=[]
for port in [5182,8021,8022]:
 with socket.socket() as s:assert s.connect_ex(('127.0.0.1',port))!=0,'Occupied test port'
with socket.socket() as occupied:
 occupied.bind(('127.0.0.1',5182));occupied.listen()
 rejected=subprocess.run(['node','scripts/dev-integrated.mjs'],capture_output=True,text=True,timeout=10)
 assert rejected.returncode!=0 and 'occupied' in rejected.stderr
 checks.append('launcher refuses occupied port without starting children')
with tempfile.TemporaryDirectory(prefix='revelio-launcher-') as temp:
 env=os.environ.copy()
 for key in ['WITNESSTRACE_DATA_DIR','WITNESSTRACE_OUTPUTS_DIR','WITNESSTRACE_WORK_DIR','REVELIO_DATA_DIR','VITE_WITNESSTRACE_LOCAL'] :env.pop(key,None)
 env['REVELIO_RUNTIME_DIR']=temp
 with open(Path(temp)/'launcher.log','w') as log:
  process=subprocess.Popen(['node','scripts/dev-integrated.mjs'],env=env,stdout=log,stderr=log)
  try:
   for _ in range(100):
    try:
     if httpx.get('http://127.0.0.1:5182/api/health',timeout=.5).status_code==200:break
    except httpx.HTTPError:pass
    time.sleep(.1)
   else:raise RuntimeError('Launcher did not become ready')
   with sync_playwright() as p:
    browser=p.chromium.launch();context=browser.new_context();page=context.new_page()
    page.goto('http://127.0.0.1:5182/app');page.wait_for_url('**/login**')
    response=context.request.post('http://127.0.0.1:5182/api/auth/register',data={'name':'Synthetic Startup Check','email':'startup@example.test','password':secrets.token_urlsafe(24)})
    assert response.status==201
    page.goto('http://127.0.0.1:5182/app#/new')
    expect(page.get_by_text('Connected · Codex CLI installed')).to_be_visible(timeout=20000)
    checks.append('one launcher serves default integrated React and both authenticated APIs')
    page.locator('#wt-title').fill('Synthetic startup case');page.get_by_role('button',name='Create case',exact=True).click()
    expect(page.locator('#wt-description')).to_be_visible()
    page.locator('#wt-description').fill('Fictional startup testimony. No generation is requested.')
    page.get_by_role('button',name='Save original testimony').click();expect(page.locator('#wt-description')).to_have_attribute('readonly','')
    page.reload();expect(page.locator('#wt-description')).to_have_value('Fictional startup testimony. No generation is requested.',timeout=20000)
    checks.append('launcher isolates persistent case and account paths and restores after refresh')
    assert (Path(temp)/'data/witness.sqlite3').exists() and (Path(temp)/'accounts').is_dir()
    assert ((Path(temp)/'data').stat().st_mode & 0o077)==0
    checks.append('new runtime directories have private permissions')
    browser.close()
  finally:
   process.terminate();process.wait(timeout=15)
for port in [5182,8021,8022]:
 with socket.socket() as s:assert s.connect_ex(('127.0.0.1',port))!=0,'Owned listener left running'
checks.append('launcher stops only its children and leaves no test listeners')
Path('docs/integration/evidence/final/startup-smoke.json').write_text(json.dumps({'checks':checks,'result':'PASS','generation_submissions':0},indent=2)+'\n')
print('PASS startup smoke: '+str(len(checks))+' checks; no generation')
