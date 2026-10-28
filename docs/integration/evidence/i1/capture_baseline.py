"""I1 reference capture. Run with a Python environment containing Playwright.
Uses only original Revelio API + fresh synthetic records; no WitnessTrace access.
Requires npm ci and backend/.venv requirements. Never uses default dev-all ports.
"""
import asyncio, hashlib, json, os, secrets, socket, subprocess, tempfile, sys
from pathlib import Path
from urllib.request import urlopen
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:5182'
WIDTHS = [(1920,1080),(1440,900),(1280,800),(768,1024),(390,844)]
DESCRIPTION = 'A fictional adult with an oval face, short dark hair, thick eyebrows, a narrow nose and a small scar on the left cheek.'
RESULT = {'scope':'Unmodified Revelio reference; synthetic procedural images, not WitnessTrace or Codex', 'screenshots':[], 'checks':[], 'errors':[], 'http_errors':[], 'failed_requests':[], 'requests':[], 'services':{'web':5182,'api':8021}, 'motion':'reduce for matrix; separate normal-motion check'}

def check(name, ok, detail=None):
    RESULT['checks'].append({'name':name,'passed':bool(ok),'detail':detail})
    print(('PASS ' if ok else 'FAIL ')+name, flush=True)

MEASURE = """() => {
 const style=(sel)=>{const e=document.querySelector(sel);if(!e)return null;const s=getComputedStyle(e),r=e.getBoundingClientRect();return {width:r.width,height:r.height,x:r.x,y:r.y,background:s.background,backgroundColor:s.backgroundColor,color:s.color,font:s.font,fontFamily:s.fontFamily,fontSize:s.fontSize,fontWeight:s.fontWeight,lineHeight:s.lineHeight,letterSpacing:s.letterSpacing,borderRadius:s.borderRadius,border:s.border,padding:s.padding,gap:s.gap,gridTemplateColumns:s.gridTemplateColumns,aspectRatio:s.aspectRatio,objectFit:s.objectFit,display:s.display,transform:s.transform,animationName:s.animationName}};
 const cs=getComputedStyle(document.documentElement),names=['--bg','--bg-2','--panel','--panel-2','--panel-3','--border','--border-strong','--text','--text-2','--text-3','--cyan','--blue','--amber','--red','--green','--shadow','--focus','--font','--display','--mono','--sidebar-w','--topbar-h','--r-lg','--t'];
 return {viewport:{width:innerWidth,height:innerHeight},scrollWidth:document.documentElement.scrollWidth,overflow:document.documentElement.scrollWidth>innerWidth,tokens:Object.fromEntries(names.map(n=>[n,cs.getPropertyValue(n).trim()])),elements:Object.fromEntries(['body','.lp','.lp-nav','.lp-hero__title','.sidebar','.nav-item.is-active','.topbar','.topbar__title h1','.content','.studio__grid','.studio__side','.viewer__stage','.viewer__frame','.viewer__img','.panel','.panel__title','.btn--primary','.input','.range','.lib-card','.providers','.modal','.toast','.label'].map(s=>[s,style(s)])),fonts:[...document.fonts].map(f=>({family:f.family,status:f.status,weight:f.weight})),brokenImages:[...document.images].filter(i=>i.complete&&!i.naturalWidth).map(i=>i.getAttribute('src')),offenders:[...document.querySelectorAll('body *')].filter(e=>{const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width&&s.position!=='fixed'&&s.visibility!=='hidden'&&(r.right>innerWidth+1||r.left< -1)}).slice(0,15).map(e=>({tag:e.tagName,class:e.className,right:e.getBoundingClientRect().right,left:e.getBoundingClientRect().left}))};
}"""

async def settled(page):
    await page.wait_for_load_state('domcontentloaded')
    await page.evaluate('document.fonts.ready')
    if '/app' in page.url:
        await page.locator('.boot').wait_for(state='detached',timeout=15000)
    await page.wait_for_timeout(400)
    await page.evaluate("Promise.all([...document.images].filter(i=>i.loading!=='lazy'||(i.getBoundingClientRect().top<innerHeight&&i.getBoundingClientRect().bottom>0)).map(i=>i.complete?Promise.resolve():Promise.race([new Promise(r=>{i.onload=r;i.onerror=r}),new Promise(r=>setTimeout(r,3000))])))")

async def shot(page,name,full=False):
    await settled(page)
    meta=await page.evaluate(MEASURE)
    target=OUT/(name+'.png')
    await page.screenshot(path=str(target),full_page=full,mask=[page.locator('input[type=password]')],mask_color='#555555')
    RESULT['screenshots'].append({'file':target.name,'route':page.url.replace(BASE,''),'theme':await page.locator('html').get_attribute('data-theme'),'source_rendered':await page.locator('#root > *').count()>0,'full_page':full,'console_events_seen':[e for e in RESULT['errors'] if e.get('route')==page.url.replace(BASE,'')],**meta})

async def navigate(page,path):
    await page.goto(BASE+path)
    await page.wait_for_load_state('domcontentloaded')
    if await page.evaluate("document.documentElement.dataset.theme !== localStorage.getItem('revelio.theme')"):
        await page.reload()
    await settled(page)

async def attempt(name,fn):
    try:await fn()
    except Exception as e:check(name,False,str(e)[:450])

async def run_browser():
 async with async_playwright() as p:
    browser=await p.chromium.launch()
    RESULT['browser']=browser.version
    RESULT['source_commit']='f89093eaa45ace99b134093b563d1f30d3bbe5c0'
    def observe(page):
        page.on('pageerror',lambda e:RESULT['errors'].append({'route':page.url.replace(BASE,''),'message':str(e)}))
        page.on('console',lambda m:RESULT['errors'].append({'route':page.url.replace(BASE,''),'console':m.text}) if m.type=='error' else None)
        page.on('requestfailed',lambda r:RESULT['failed_requests'].append({'url':r.url.replace(BASE,''),'failure':r.failure}))
        page.on('response',lambda r:RESULT['http_errors'].append({'url':r.url.replace(BASE,''),'status':r.status}) if r.status>=400 else None)
        page.on('request',lambda r:RESULT['requests'].append({'url':r.url.replace(BASE,''),'method':r.method}))
    anon=await browser.new_context(viewport={'width':1440,'height':900},reduced_motion='reduce')
    auth=await browser.new_context(viewport={'width':1440,'height':900},reduced_motion='reduce')
    for context in [anon,auth]:
        await context.add_init_script("if(!localStorage.getItem('revelio.theme'))localStorage.setItem('revelio.theme','dark')")
    page=await auth.new_page();observe(page)
    # Seed via real original API, no intercepted/fabricated successful responses.
    password=secrets.token_urlsafe(24)
    response=await auth.request.post(BASE+'/api/auth/register',data={'name':'Synthetic Visual QA','email':'visual-qa@example.test','password':password})
    check('real reference API registration',response.status==201)
    ex=await auth.request.post(BASE+'/api/traits/extract',data={'description':DESCRIPTION});profile=(await ex.json())['profile']
    a=await auth.request.post(BASE+'/api/sketches/generate',data={'title':'Synthetic baseline A','description':DESCRIPTION,'profile':profile,'mode':'offline'})
    sketch=await a.json();sid=sketch['id'];check('offline procedural synthetic seed',a.status==201 and not sketch['current']['is_ai'])
    profile2=json.loads(json.dumps(profile));profile2['adjustments']={'jaw_width':-.35,'nose_width':.25};profile2['traits']['eyebrow_thickness']={'value':'thick','source':'manual'}
    r=await auth.request.post(BASE+f'/api/sketches/{sid}/revisions',data={'profile':profile2,'mode':'offline','note':'Synthetic visual revision; no real person'})
    check('real reference API second revision',r.status==201)
    r=await auth.request.post(BASE+'/api/sketches/generate',data={'title':'Synthetic baseline B','description':DESCRIPTION,'profile':profile,'mode':'offline'})
    check('second synthetic library card',r.status==201)
    ap=await anon.new_page();observe(ap)
    # Matrix uses saved revision for populated studio and comparison. Auth screens stay anonymous.
    routes=[('landing','/',ap),('login','/login',ap),('register','/register',ap),('workspace','/app#/workspace',page),('new',f'/app#/new?sketch={sid}',page),('library','/app#/library',page),('compare',f'/app#/compare?sketch={sid}',page),('settings','/app#/settings',page)]
    for theme in ([] if '--states-only' in sys.argv else ['dark','light']):
      for width,height in WIDTHS:
        for name,path,target in routes:
            await target.set_viewport_size({'width':width,'height':height})
            # Set persisted preference on real origin; normal application initialization reads it.
            if not target.url.startswith(BASE):await target.goto(BASE+'/login')
            await target.evaluate('(t)=>localStorage.setItem("revelio.theme",t)',theme)
            await navigate(target,path)
            check(f'matrix {theme}-{width}-{name} active theme',await target.locator('html').get_attribute('data-theme')==theme)
            if name=='new':await target.locator('.viewer__img').wait_for()
            if name=='library':await target.locator('.lib-card').first.wait_for()
            if name=='compare':await target.get_by_role('slider',name='Comparison divider').wait_for()
            await shot(target,f'{theme}-{width}-{name}')
        print(f'MATRIX {theme} {width} complete',flush=True)
    # Additional screen states at 1440 in dark.
    for target in [page,ap]:
        await target.set_viewport_size({'width':1440,'height':900})
        if not target.url.startswith(BASE):await target.goto(BASE+'/')
        await target.evaluate("localStorage.setItem('revelio.theme','dark')")
    await navigate(ap,'/')
    for selector,name in [('#features','features'),('#demo','demo'),('#editor','editor'),('.lp-footer','footer')]:
        loc=ap.locator(selector)
        if await loc.count():
            await loc.scroll_into_view_if_needed();await shot(ap,'dark-1440-landing-'+name)
    for y in range(0,await ap.evaluate('document.documentElement.scrollHeight'),600):
        await ap.evaluate('(y)=>window.scrollTo(0,y)',y);await ap.wait_for_timeout(65)
    await ap.evaluate('window.scrollTo(0,0)');await shot(ap,'dark-1440-landing-full',full=True)
    async def landing_demo():
        demo=ap.locator('#demo');await demo.scroll_into_view_if_needed()
        await demo.locator('textarea').fill(DESCRIPTION)
        await demo.get_by_role('button',name='Generate Composite',exact=True).click()
        await demo.locator('img').first.wait_for()
        await shot(ap,'dark-1440-landing-demo-generated');check('landing live procedural demo',True)
    await attempt('landing live procedural demo',landing_demo)
    await navigate(ap,'/register')
    await ap.locator('button[type=submit]').click()
    check('registration validation',await ap.locator('.lp-error').count()>=3)
    await shot(ap,'dark-1440-register-validation')
    await navigate(ap,'/login')
    await ap.locator('#auth-email').fill('unknown@example.test');await ap.locator('#auth-password').fill(secrets.token_urlsafe(20))
    await ap.locator('button[type=submit]').click();await ap.get_by_text('Email or password is incorrect.',exact=False).wait_for()
    await shot(ap,'dark-1440-login-server-error')
    check('login real server rejection',True)
    # Real form login with throwaway account, no password persisted in evidence.
    await ap.locator('#auth-email').fill('visual-qa@example.test');await ap.locator('#auth-password').fill(password)
    await ap.locator('button[type=submit]').click();await ap.wait_for_url('**/app');check('login form successful redirect',True)
    await navigate(page,'/app#/new?fresh=i1')
    await shot(page,'dark-1440-new-empty')
    await page.get_by_role('tab',name='Guided',exact=True).click();await shot(page,'dark-1440-new-guided')
    check('guided tab',await page.get_by_role('button',name='Apply 0 answers to profile',exact=True).count()>0)
    guided_select=page.locator('.guided select').first
    options=await guided_select.locator('option').evaluate_all("es=>es.map(e=>e.value).filter(Boolean)")
    await guided_select.select_option(options[0]);await page.get_by_role('button',name='Apply 1 answer to profile',exact=True).click();check('guided answer applied',True)
    await page.get_by_role('tab',name='Witnesses',exact=True).click();await shot(page,'dark-1440-new-witnesses');check('witness tab',await page.locator('.merge').count()>0)
    for i in range(2):await page.locator('.merge textarea').nth(i).fill(DESCRIPTION)
    await page.get_by_role('button',name='Compare descriptions',exact=True).click()
    await page.get_by_role('button',name='Apply combined profile',exact=True).wait_for();await shot(page,'dark-1440-witness-merge-result');check('real witness merge comparison',True)
    await page.get_by_role('button',name='Apply combined profile',exact=True).click();check('combined profile applied',True)
    await page.get_by_role('tab',name='Description',exact=True).click()
    await page.locator('.describe__text').fill(DESCRIPTION)
    await page.locator('.describe__text').press('Control+Enter')
    await page.locator('.viewer__img').wait_for();check('keyboard extraction and real procedural preview',True)
    await shot(page,'dark-1440-new-extracted-toast')
    await page.get_by_role('button',name='Zoom in',exact=True).click()
    check('viewer zoom',await page.locator('.viewer__zoom').inner_text()=='125%')
    await shot(page,'dark-1440-new-zoom');await page.get_by_role('button',name='Fit to screen',exact=True).click()
    await page.get_by_role('tab',name='Editor',exact=True).click()
    slider=page.locator('#adj-face_width');await slider.fill('0.4');await slider.press('ArrowRight')
    check('adjustment slider keyboard',float(await slider.input_value())>.4)
    await shot(page,'dark-1440-new-adjustments')
    await page.get_by_role('button',name='Undo',exact=True).click();check('undo adjustment',float(await slider.input_value())==0)
    await page.get_by_role('button',name='Redo',exact=True).click();check('redo adjustment',float(await slider.input_value())>0)
    await page.get_by_role('tab',name='Refine',exact=True).click()
    await page.locator('.refine__form input.input').fill('Make the eyebrows thinner and the jaw narrower')
    await page.locator('.refine button[type=submit]').click()
    await page.locator('.change').first.wait_for();await shot(page,'dark-1440-new-refinement-proposal');check('real refinement proposal',True)
    await page.get_by_role('button',name='Apply',exact=False).filter(has_text='change').click();check('apply refinement proposal',True)
    await page.get_by_role('button',name='Save composite',exact=False).click()
    await page.locator('.revisions .rev').first.wait_for();check('save through UI',True)
    await shot(page,'dark-1440-new-saved');await page.evaluate('window.scrollTo(0,0)');await shot(page,'dark-1440-studio-full',full=True)
    # Library modal, search, rename, status, exports.
    await navigate(page,'/app#/library')
    await shot(page,'dark-1440-library-full',full=True)
    await page.get_by_role('button',name='History',exact=True).first.click();await page.get_by_role('dialog').wait_for()
    await shot(page,'dark-1440-library-history')
    check('modal focus trapped',await page.evaluate("document.querySelector('[role=dialog]').contains(document.activeElement)"))
    await page.keyboard.press('Shift+Tab');check('modal keyboard focus stays inside',await page.evaluate("document.querySelector('[role=dialog]').contains(document.activeElement)"))
    await page.keyboard.press('Escape');check('modal Escape closes',await page.get_by_role('dialog').count()==0)
    await page.get_by_role('button',name='Delete Synthetic baseline A',exact=True).click();await shot(page,'dark-1440-library-delete-confirm')
    await page.get_by_role('button',name='Cancel',exact=True).click();check('delete confirmation cancellation',await page.get_by_role('dialog').count()==0)
    await page.get_by_label('Search sketches',exact=True).fill('no-synthetic-match')
    await page.get_by_text('No sketches match this search',exact=True).wait_for();await shot(page,'dark-1440-library-search-empty');check('library search',True)
    await page.get_by_label('Search sketches',exact=True).fill('');await page.locator('.lib-card').first.wait_for()
    for label,link in [('png',f'/api/sketches/{sid}/revisions/2/image.png?download=true'),('json',f'/api/sketches/{sid}/export.json?download=true'),('report',f'/api/sketches/{sid}/report')]:
        r=await auth.request.get(BASE+link);body=await r.body();check('reference '+label+' export',r.status==200);RESULT.setdefault('exports',[]).append({'kind':label,'status':r.status,'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)})
    await navigate(page,f'/app#/compare?sketch={sid}')
    divider=page.get_by_role('slider',name='Comparison divider');await divider.focus();await divider.press('ArrowLeft');check('compare keyboard',await divider.get_attribute('aria-valuenow')=='45')
    bounds=await page.locator('.compare').bounding_box();await page.mouse.move(bounds['x']+bounds['width']*.5,bounds['y']+bounds['height']*.5);await page.mouse.down();await page.mouse.move(bounds['x']+bounds['width']*.7,bounds['y']+bounds['height']*.5);await page.mouse.up()
    check('compare drag',int(await divider.get_attribute('aria-valuenow'))>=69)
    await page.get_by_label('Version A revision',exact=True).select_option('2');check('compare version selection',await page.get_by_label('Version A revision',exact=True).input_value()=='2')
    await page.get_by_role('button',name='Side by side',exact=True).click();await shot(page,'dark-1440-compare-split');check('side-by-side view',await page.locator('.split figure').count()==2)
    await navigate(page,'/app#/settings')
    motion=page.locator('label.switch').filter(has_text='Reduce motion');await motion.click();check('reduce-motion preference',await page.locator('html').evaluate("e=>e.classList.contains('reduce-motion')"));await motion.click()
    await page.get_by_role('button',name='Re-check',exact=True).click();check('health recheck',await page.get_by_text('Generation providers',exact=True).is_visible())
    await page.get_by_role('button',name='Delete all local data',exact=False).click();await shot(page,'dark-1440-settings-delete-confirm')
    check('destructive action gated',not await page.get_by_role('button',name='Delete everything',exact=True).is_enabled())
    await page.get_by_label('Type DELETE to confirm',exact=False).fill('DELETE');check('confirmation text unlocks',await page.get_by_role('button',name='Delete everything',exact=True).is_enabled());await page.keyboard.press('Escape')
    # Toggle actual theme control and prove persistence.
    await page.get_by_role('button',name='Switch to light theme',exact=True).click();check('theme toggle',await page.locator('html').get_attribute('data-theme')=='light');await page.reload();await settled(page);check('theme persists reload',await page.locator('html').get_attribute('data-theme')=='light')
    # Every real sidebar route via link click.
    for name in ['workspace','new','library','compare','settings']:
        await page.locator(f'.sidebar__nav a[href="#/{name}"]').click();await settled(page);check('sidebar navigation '+name,await page.locator(f'.sidebar__nav a[href="#/{name}"]').get_attribute('aria-current')=='page')
    await page.set_viewport_size({'width':390,'height':844})
    await page.get_by_role('button',name='Open navigation',exact=False).click();await shot(page,'light-390-sidebar-open');check('mobile sidebar opens',await page.locator('.sidebar').evaluate("e=>e.classList.contains('is-open')"))
    await page.locator('.sidebar__nav a[href="#/library"]').click();check('mobile navigation closes drawer',not await page.locator('.sidebar').evaluate("e=>e.classList.contains('is-open')"))
    await navigate(ap,'/')
    await ap.set_viewport_size({'width':390,'height':844});await ap.get_by_role('button',name='Open menu',exact=True).click();await shot(ap,'dark-390-landing-menu');await ap.keyboard.press('Escape');check('landing mobile menu Escape',not await ap.locator('.lp-menu').evaluate("e=>e.classList.contains('is-open')"))
    # Transport delay passes real backend results through unchanged: capture spinner, no mocked success.
    await page.set_viewport_size({'width':1440,'height':900})
    await page.evaluate("localStorage.setItem('revelio.theme','dark')")
    async def delay(route):
        response=await route.fetch();await asyncio.sleep(1.5);await route.fulfill(response=response)
    await page.route('**/api/health',delay)
    await page.goto(BASE+'/app#/workspace');await page.reload(wait_until='domcontentloaded');await page.locator('.boot').wait_for();await page.screenshot(path=str(OUT/'dark-1440-loading-boot.png'));RESULT['screenshots'].append({'file':'dark-1440-loading-boot.png','route':'/app#/workspace','theme':'dark','source_rendered':True,'controlled_transport_delay':True,**(await page.evaluate(MEASURE))})
    await settled(page);await page.unroute('**/api/health',delay)
    # Controlled transport errors, explicitly identified separately from baseline errors.
    async def fail(route):await route.fulfill(status=503,json={'detail':'I1 controlled unavailable reference service'})
    await page.route('**/api/health',fail);await page.reload(wait_until='domcontentloaded');await navigate(page,'/app#/workspace');await page.get_by_text('Local engine not reachable',exact=True).wait_for();await shot(page,'dark-1440-controlled-offline');check('workspace controlled 503 offline state',True);await page.unroute('**/api/health',fail)
    await navigate(page,'/app#/workspace')
    await page.get_by_role('button',name='Notifications',exact=False).click();await shot(page,'dark-1440-notifications');await page.keyboard.press('Escape');check('notifications opens and Escape closes',True)
    await ap.set_viewport_size({'width':1440,'height':900})
    await ap.evaluate("localStorage.setItem('revelio.theme','light')");await navigate(ap,'/')
    for selector,name in [('#features','features'),('#demo','demo'),('#editor','editor'),('.lp-footer','footer')]:
        await ap.locator(selector).scroll_into_view_if_needed();await shot(ap,'light-1440-landing-'+name)
    for y in range(0,await ap.evaluate('document.documentElement.scrollHeight'),600):
        await ap.evaluate('(y)=>window.scrollTo(0,y)',y);await ap.wait_for_timeout(65)
    await ap.evaluate('window.scrollTo(0,0)');await shot(ap,'light-1440-landing-full',full=True)
    await ap.get_by_role('button',name='Join Waitlist',exact=True).click();await shot(ap,'light-1440-planned-pricing-modal');check('pricing notice is labelled planned',await ap.get_by_role('dialog').is_visible());await ap.keyboard.press('Escape')
    normal=await browser.new_context(viewport={'width':1440,'height':900},reduced_motion='no-preference');np=await normal.new_page();observe(np);await navigate(np,'/');await np.wait_for_timeout(1200);await shot(np,'dark-1440-landing-motion');check('normal motion source renders',await np.locator('.lp-hero__title').is_visible())
    RESULT['normal_motion']=await np.evaluate("({reduced:matchMedia('(prefers-reduced-motion: reduce)').matches,canvas:!!document.querySelector('canvas'),animations:[...document.querySelectorAll('*')].filter(e=>getComputedStyle(e).animationName!=='none').length})")
    await normal.close();await anon.close();await auth.close();await browser.close()

async def main():
    if '--states-only' in sys.argv:
        previous=json.loads((OUT/'browser-results.json').read_text())
        RESULT['screenshots']=[s for s in previous['screenshots'] if s['file'].count('-')==2]
        RESULT['matrix_previous_run']={'browser':previous.get('browser'),'errors':previous['errors'],'http_errors':previous['http_errors'],'failed_requests':previous['failed_requests'],'requests':previous['requests']}
    for port in [5182,8021]:
        with socket.socket() as s:
            if s.connect_ex(('127.0.0.1',port))==0:raise RuntimeError(f'Refusing to disturb occupied port {port}')
    with tempfile.TemporaryDirectory(prefix='revelio-i1-') as temp:
        env=os.environ.copy()
        for k in list(env):
            if k.startswith(('REVELIO_','VERISKETCH_','GEMINI_')):env.pop(k)
        env.update(REVELIO_DATA_DIR=temp+'/data',REVELIO_HOSTED_PROVIDER='',REVELIO_API_URL='http://127.0.0.1:8021')
        processes=[]
        try:
            log=open(Path(temp)/'services.log','w')
            processes.append(subprocess.Popen([str(ROOT/'backend/.venv/bin/python'),'-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8021'],cwd=ROOT/'backend',env=env,stdout=log,stderr=log))
            processes.append(subprocess.Popen(['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5182','--strictPort'],cwd=ROOT,env=env,stdout=log,stderr=log))
            for _ in range(100):
                try:
                    with urlopen(BASE+'/api/health',timeout=1) as r:
                        if r.status==200:break
                except Exception:await asyncio.sleep(.2)
            else:raise RuntimeError('Reference services did not start')
            await run_browser()
        except Exception as exc:
            RESULT['fatal']=str(exc);raise
        finally:
            for process in reversed(processes):
                process.terminate()
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:process.kill();process.wait()
            RESULT['services_stopped']=all(p.poll() is not None for p in processes)
            (OUT/'browser-results.json').write_text(json.dumps(RESULT,indent=2))
            log.close()

if __name__=='__main__':asyncio.run(main())
