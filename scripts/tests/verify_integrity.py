"""Isolated browser E2E with explicit wallet approval simulation and deterministic RPC."""
import base64, io, json, os, secrets, socket, subprocess, tempfile, time, uuid
from pathlib import Path
import httpx
from PIL import Image
from playwright.sync_api import sync_playwright, expect

ROOT = Path.cwd()
TX = '0x' + 'a' * 64
ADDRESS = '0x' + '1' * 40
SINK = '0x000000000000000000000000000000000000dead'
BLOCK = '0x' + 'b' * 64
with tempfile.TemporaryDirectory(prefix='integrity-e2e-') as temp:
    env = dict(os.environ, REVELIO_RUNTIME_DIR=temp)
    # The stub runs only in this isolated child process, never in application production code.
    stub = Path(temp) / 'rpc.json'
    stub.write_text('{}')
    env['INTEGRITY_TEST_RPC'] = str(stub)
    runner = Path(temp) / 'witness.py'
    runner.write_text("""import sys,os,json
sys.path.insert(0,os.path.join(os.getcwd(),'witness-backend'))
import app,integrity_store,uvicorn
def rpc(method,params):
    values=json.load(open(os.environ['INTEGRITY_TEST_RPC']))
    if 'failure' in values: raise integrity_store.RPCFailure(values['failure'])
    return values[method]
integrity_store.rpc=rpc
uvicorn.run(app.app,host='127.0.0.1',port=8122)
""")
    for key, child in [('WITNESSTRACE_DATA_DIR','data'),('WITNESSTRACE_OUTPUTS_DIR','outputs'),('WITNESSTRACE_WORK_DIR','work'),('REVELIO_DATA_DIR','accounts')]:
        env[key] = str(Path(temp)/child)
    env.update(WITNESSTRACE_GATEWAY_TARGET='http://127.0.0.1:8122', REVELIO_API_URL='http://127.0.0.1:8121', REVELIO_GATEWAY_URL='http://127.0.0.1:8121')
    py = str(ROOT/'witness-backend/.venv/bin/python')
    commands = [[py,str(runner)],[py,'-m','uvicorn','app.main:app','--app-dir','backend','--port','8121'],['node','node_modules/vite/bin/vite.js','--host','127.0.0.1','--port','5282','--strictPort']]
    processes=[]
    with open(Path(temp)/'log','w') as log:
      try:
        for port in [5282,8121,8122]:
            with socket.socket() as sock: assert sock.connect_ex(('127.0.0.1',port)) != 0, 'Test port occupied'
        processes=[subprocess.Popen(cmd,env=env,stdout=log,stderr=log) for cmd in commands]
        for _ in range(150):
            try:
                if httpx.get('http://127.0.0.1:5282/api/health').status_code==200: break
            except httpx.HTTPError: pass
            time.sleep(.1)
        with sync_playwright() as p:
            browser=p.chromium.launch(); ctx=browser.new_context(); page=ctx.new_page()
            origin='http://127.0.0.1:5282'
            assert ctx.request.get(origin+'/wt-api/api/cases/'+'0'*32+'/versions/'+'0'*32+'/integrity').status == 401
            assert ctx.request.post(origin+'/api/auth/register',data={'name':'Integrity Test','email':'integrity@example.test','password':secrets.token_urlsafe(24)}).status==201
            case=ctx.request.post(origin+'/wt-api/api/cases',data={'title':'Synthetic integrity case','synthetic':True}).json()
            ctx.request.post(origin+f"/wt-api/api/cases/{case['id']}/freeze",data={'revision':case['revision'],'text':'Fictional synthetic witness testimony for an isolated test.'})
            image=io.BytesIO();Image.new('RGB',(128,128),'navy').save(image,format='PNG')
            imported=ctx.request.post(origin+f"/wt-api/api/cases/{case['id']}/imports",data={'image':'data:image/png;base64,'+base64.b64encode(image.getvalue()).decode(),'filename':'synthetic.png','consent':True,'request_key':uuid.uuid4().hex}).json()
            vid=imported['version_id']; path=origin+f"/wt-api/api/cases/{case['id']}/versions/{vid}/integrity"
            value=ctx.request.get(path).json()
            tx=dict(hash=TX,chainId='0x14a34',input=value['data'],value='0x0',to=SINK,blockHash=BLOCK,blockNumber='0x123',**{'from':ADDRESS})
            stub.write_text(json.dumps({'eth_chainId':'0x14a34','eth_getTransactionByHash':tx,'eth_getTransactionReceipt':None}))
            # Real ethers BrowserProvider and signer; simulate the extension's user approval boundary.
            page.add_init_script("""window.walletCalls=[];window.walletReject=false;window.walletChain='0x1';
window.ethereum={isMetaMask:true,on(){},removeListener(){},async request({method,params}){
window.walletCalls.push({method,params});
if(method==='eth_requestAccounts'||method==='eth_accounts')return ['ADDRESS'];
if(method==='eth_chainId')return window.walletChain;
if(method==='wallet_switchEthereumChain'){window.walletChain=params[0].chainId;return null;}
if(method==='eth_blockNumber')return '0x123';
if(method==='eth_estimateGas')return '0x10000';
if(method==='eth_gasPrice'||method==='eth_maxPriorityFeePerGas')return '0x3b9aca00';
if(method==='eth_sendTransaction'){if(params[0].to.toLowerCase()==='ADDRESS' && params[0].data){let e=new Error('External transactions to internal accounts cannot include data.');e.code=-32602;throw e;}if(window.walletReject){let e=new Error('User rejected');e.code=4001;throw e;}window.sent=params[0];return 'TX';}
if(method==='eth_getTransactionByHash')return {hash:'TX',type:'0x2',chainId:'0x14a34',nonce:'0x0',gas:'0x10000',maxFeePerGas:'0x3b9aca00',maxPriorityFeePerGas:'0x1',from:'ADDRESS',to:window.sent.to,value:'0x0',input:window.sent.data,blockHash:null,blockNumber:null,transactionIndex:null,accessList:[],v:'0x0',r:'0x'+'1'.repeat(64),s:'0x'+'2'.repeat(64)};
if(method==='eth_getTransactionReceipt')return null;
throw new Error('Unexpected wallet method '+method);
}};""".replace('ADDRESS',ADDRESS).replace('TX',TX))
            page.route('**/api/speech', lambda route: route.fulfill(json={'available': False}))
            page.add_init_script('''window.SpeechRecognition=class {start(){window.testRecognition=this;}stop(){this.onend?.();}abort(){}}''')
            page.goto(origin+'/app#/new')
            page.locator('#wt-case').select_option(case['id'])
            expect(page.get_by_role('heading',name='Blockchain Integrity')).to_be_visible(timeout=20000)
            expect(page.get_by_text('NOT REGISTERED',exact=True)).to_be_visible()
            # Preserve remote dictation in the same studio as blockchain integrity.
            dictate=page.get_by_role('button',name='Dictate',exact=True).first
            expect(dictate).to_be_enabled()
            dictate.click()
            page.evaluate("""() => {const result=[{transcript:'Synthetic voice clarification.'}];result.isFinal=true;window.testRecognition.onresult({resultIndex:0,results:[result]});}""")
            expect(page.locator('#wt-clarify')).to_have_value('Synthetic voice clarification.')
            page.get_by_role('button',name='Stop',exact=True).click()
            page.get_by_role('button',name='Connect MetaMask',exact=True).click()
            expect(page.get_by_text('Wallet: '+ADDRESS)).to_be_visible()
            assert page.evaluate('window.walletChain')=='0x14a34'
            rejection = page.evaluate("""async () => {try {await window.ethereum.request({method:'eth_sendTransaction',params:[{to:'"""+ADDRESS+"""',data:'0x1234',value:'0x0'}]});return null;}catch(e){return {code:e.code,message:e.message};}}""")
            assert rejection['code']==-32602 and 'internal accounts' in rejection['message']
            page.evaluate('window.walletReject=true')
            page.get_by_role('button',name='Register on Blockchain',exact=True).click()
            expect(page.get_by_text('ERROR',exact=True)).to_be_visible()
            assert ctx.request.get(path).json()['status']=='NOT REGISTERED'
            page.evaluate('window.walletReject=false')
            page.get_by_role('button',name='Register on Blockchain',exact=True).click()
            expect(page.get_by_role('link',name='View transaction on BaseScan:',exact=False)).to_be_visible()
            for _ in range(40):
                if ctx.request.get(path).json()['tx_hash']==TX:break
                time.sleep(.1)
            assert ctx.request.get(path).json()['status']=='PENDING'
            sent=page.evaluate('window.sent');assert int(sent['value'],16)==0 and sent['data']==value['data'] and sent['to'].lower()==SINK and sent['from'].lower()==ADDRESS and int(sent['chainId'],16)==84532
            # Reload proves pending transactions survive without browser memory or a wallet connection.
            page.reload();expect(page.get_by_text('PENDING',exact=True)).to_be_visible(timeout=20000)
            rpc=json.loads(stub.read_text());rpc['eth_getTransactionReceipt']=dict(to=SINK, **{'from':ADDRESS}, transactionHash=TX,status='0x1',blockHash=BLOCK,blockNumber='0x123');rpc['eth_getBlockByNumber']={'hash':BLOCK};stub.write_text(json.dumps(rpc))
            page.get_by_role('button',name='Verify Integrity',exact=True).click();expect(page.get_by_text('VERIFIED',exact=True)).to_be_visible()
            # Operational failures must show a retryable code, preserve the hash, and never resend.
            send_count=page.evaluate("window.walletCalls.filter(c=>c.method==='eth_sendTransaction').length")
            stub.write_text(json.dumps({'failure':'RPC_RATE_LIMITED'}))
            page.get_by_role('button',name='Verify Integrity',exact=True).click()
            expect(page.get_by_text('ERROR',exact=True)).to_be_visible()
            expect(page.get_by_text('Diagnostic: RPC_RATE_LIMITED',exact=False)).to_be_visible()
            expect(page.get_by_role('button',name='Register on Blockchain',exact=True)).to_be_disabled()
            stub.write_text(json.dumps(rpc))
            page.get_by_role('button',name='Verify Integrity',exact=True).click()
            expect(page.get_by_text('VERIFIED',exact=True)).to_be_visible()
            assert page.evaluate("window.walletCalls.filter(c=>c.method==='eth_sendTransaction').length")==send_count
            files=list((Path(temp)/'data').rglob(vid+'.png'));assert len(files)==1
            files[0].write_bytes(files[0].read_bytes()+b'tampered')
            page.get_by_role('button',name='Verify Integrity',exact=True).click();expect(page.get_by_text('TAMPERED',exact=True)).to_be_visible()
            browser.close()
            print('PASS: authenticated gateway, saved-byte digest, dictation alongside blockchain, chain switch, MetaMask rejection, ethers zero-value commitment, pending persistence, reload, independent verification, safe RPC rate-limit diagnostics and recovery without resubmission, tamper detection, BaseScan link')
      finally:
        for process in processes: process.terminate()
        for process in processes: process.wait(timeout=15)
