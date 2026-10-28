'use strict';
window.CaseDeliverables=(()=>{
 const ANGLES=[['front','Front'],['left','Left-facing profile'],['right','Right-facing profile'],['three_quarter','Three-quarter']];
 let requests=[],reports=[],sheetId=null,angle=null,zoom=1,sheetImage=null,displayImage=null,reviewed=null,reviewFingerprint='',pendingRequest=null,multiTimer=null,caseToken=0,refreshing=false,exportBusy=false,reportRequest=null,reportFingerprint='',layoutBusy=false,exportVersion=null;
 const selected=()=>activeCase?.versions.find(v=>v.id===activeCase.selected_version_id)||activeCase?.versions.at(-1);
 const currentSheet=()=>requests.find(r=>r.job_id===sheetId&&r.status==='complete'&&r.image_url);
 const fingerprint=()=>JSON.stringify({caseId:activeCase?.id,parent:selected()?.id,revision:activeCase?.revision,draft:draftFromForm(),style:$('multi-style').value});
 const draft=()=>({...draftFromForm(),style:$('multi-style').value});
 const status=(text,error=false)=>{$('multi-status').textContent=text;$('multi-status').classList.toggle('error',error);};
 function availability(){
  const valid=permitted()&&!loading&&!!selected();$('multi-review').disabled=!valid||busy;$('multi-style').disabled=!valid||busy;
  $('multi-generate').disabled=!valid||busy||!reviewed||reviewed.over_limit||reviewFingerprint!==fingerprint();$('multi-generate').textContent=busy?'Generating…':$('multi-status').dataset.failed==='true'?'Retry Multi-View':'Generate Multi-View';
  for(const id of ['export-png','export-json','export-report'])$(id).disabled=!valid||exportBusy;
  $('layout-save').disabled=!$('layout-checked').checked||layoutBusy;
  const item=currentSheet(),panels=item?.layout?.panels||[];$('multi-previous').disabled=!panels.length;$('multi-next').disabled=!panels.length;$('multi-layout').disabled=!item||layoutBusy;
 }
 function invalidate(){reviewed=null;pendingRequest=null;reviewFingerprint='';$('multi-budget').textContent='Inputs changed; review the exact prompt before generating.';availability();}
 function selectionChanged(){
  const v=selected();$('multi-source-image').hidden=!v;
  if(v){$('multi-source-image').src=v.image_url;$('multi-source-label').textContent='Source V'+(activeCase.versions.indexOf(v)+1)+' · '+v.id.slice(0,8)+' · '+(v.workspace==='upload'?'Uploaded source; pixels not used by AI':v.workspace==='multiview'?'Experimental 2D sheet':'Saved composite; pixels not used by AI');$('export-selection').textContent='Persisted source for export: case '+activeCase.id+' · V'+(activeCase.versions.indexOf(v)+1)+' · '+v.id;}
  if(reviewed&&reviewFingerprint!==fingerprint())invalidate();if(exportVersion!==v?.id){reportRequest=null;exportVersion=v?.id;}
  availability();refresh();
 }
 function caseChanged(){
  ++caseToken;clearTimeout(multiTimer);requests=[];reports=[];sheetId=null;angle=null;sheetImage=null;displayImage=null;reviewed=null;pendingRequest=null;reportRequest=null;exportVersion=null;$('multi-sheet-content').hidden=true;$('multi-history').replaceChildren();$('export-history').replaceChildren();$('multi-prompt').textContent='';$('multi-budget').textContent='Review before generation.';$('multi-status').textContent='';$('multi-status').dataset.failed='false';$('export-status').textContent='';$('multi-style').value=activeCase?.draft.style||'forensic';$('layout-dialog').close();$('report-dialog').close();$('report-preview').removeAttribute('src');availability();
 }
 async function refresh(){
  if(!activeCase||!permitted()||refreshing)return;const caseId=activeCase.id,token=caseToken;refreshing=true;
  try{
   const [views,exports]=await Promise.all([api('/api/cases/'+caseId+'/multiview'),api('/api/cases/'+caseId+'/reports')]);if(activeCase?.id!==caseId||caseToken!==token)return;
   if(!Array.isArray(views.requests)||!Array.isArray(exports))throw Error('Unexpected history response; existing saved views are retained.');
   requests=views.requests;reports=exports;$('multi-history').replaceChildren();
   for(const r of requests){const p=document.createElement('p');p.textContent=r.created_at+' · '+r.status+' · '+r.job_id.slice(0,8)+' · parent '+r.parent_id.slice(0,8);$('multi-history').append(p);}
   if(!requests.length)$('multi-history').textContent='No multi-view requests for this case.';
   const complete=requests.filter(r=>r.status==='complete'&&r.image_url);$('multi-sheet-select').replaceChildren(...complete.map(r=>new Option('Concept sheet · '+r.created_at+' · '+r.job_id.slice(0,8),r.job_id)));
   if(!sheetId||!complete.some(r=>r.job_id===sheetId))sheetId=complete.at(-1)?.job_id||null;
   const main=selected();if(main?.mode==='concept_multiview'&&complete.some(r=>r.job_id===main.id))sheetId=main.id;
   if(sheetId){$('multi-sheet-select').value=sheetId;if(!sheetImage||sheetImage.dataset.version!==sheetId)await openSheet(sheetId);else renderAngles();}
   $('export-history').replaceChildren();
   for(const report of reports){const p=document.createElement('p');p.textContent=report.created_at+' · '+report.version_id.slice(0,8)+' · report '+report.id.slice(0,8);const b=document.createElement('button');b.type='button';b.className='secondary';b.textContent='Open persisted report';b.onclick=()=>openReport(report);p.append(b);$('export-history').append(p);}
   if(!reports.length)$('export-history').textContent='No PDF reports saved for this case.';
  }catch(e){status('Unable to load multi-view/report history: '+e.message,true);}
  finally{refreshing=false;availability();if(activeCase&&(activeCase.id!==caseId||caseToken!==token))refresh();}
 }
 $('multi-style').onchange=invalidate;
 $('multi-review').onclick=async()=>{
  if(!selected()||busy)return;const key=fingerprint(),caseId=activeCase.id;reviewed=null;availability();
  try{
   const payload={parent_id:selected().id,revision:activeCase.revision,draft:draft(),request_key:crypto.randomUUID().replaceAll('-','')};const result=await api('/api/cases/'+caseId+'/multiview-preview','POST',payload);
   if(activeCase?.id!==caseId||fingerprint()!==key)return;reviewed=result;reviewFingerprint=key;pendingRequest=payload;$('multi-prompt').textContent=result.description;$('multi-budget').textContent=result.length+' / '+result.limit+' characters'+(result.over_limit?' · Over limit; nothing was truncated.':' · Text-only; one sheet, one CLI call.');$('multi-budget').classList.toggle('error',result.over_limit);$('multi-status').dataset.failed='false';
  }catch(e){status(e.message,true);}finally{availability();}
 };
 $('multi-generate').onclick=async()=>{
  if(busy||!reviewed||reviewed.over_limit||fingerprint()!==reviewFingerprint)return;const caseId=activeCase.id;busy=true;unlock();status('Submitting one experimental 2D sheet job…');
  try{const job=await api('/api/cases/'+caseId+'/multiview','POST',{...pendingRequest,reviewed_prompt:reviewed.description});await poll(job.job_id,caseId);}
  catch(e){busy=false;status(e.message+' Existing images retained.',true);$('multi-status').dataset.failed='true';unlock();}
 };
 async function poll(id,caseId){
  if(activeCase?.id!==caseId)return;
  try{
   const job=await api('/api/jobs/'+id);
   if(job.status==='working'){status('Generating experimental 2D views · job '+id.slice(0,8)+' · existing images retained.');state('RUNNING','Generating one concept sheet through the existing authenticated Codex CLI.');multiTimer=setTimeout(()=>poll(id,caseId),2000);return;}
   const record=await api('/api/cases/'+caseId);if(activeCase?.id!==caseId)return;
   for(const key of ['revision','versions','jobs','events','selected_version_id','preferred_version_id','last_generated_draft'])activeCase[key]=record[key];busy=false;renderRecords();
   if(job.status==='complete'){
    sheetId=id;sheetImage=null;await refresh();await showImage(selected(),caseId);if(labReady)CharacterLab.setBaseline(record.last_generated_draft);status('Saved AI-generated 2D concept sheet. Inspect the actual layout before enabling any angle crops.');$('multi-status').dataset.failed='false';reviewed=null;pendingRequest=null;$('connection').textContent='ONLINE GENERATION';$('connection').classList.add('online');
   }else{status(job.message+' No successful sheet created; prior images retained.',true);$('multi-status').dataset.failed='true';if(pendingRequest)pendingRequest.request_key=crypto.randomUUID().replaceAll('-','');await refresh();state('FAILED',job.message,true);}
   unlock();
  }catch(e){busy=false;status('Connection lost. State is unknown; reload to reconnect or retry the same request safely.',true);$('multi-status').dataset.failed='true';unlock();}
 }
 async function openSheet(id){
  const item=requests.find(r=>r.job_id===id&&r.image_url);if(!item)return;const caseId=activeCase.id;sheetId=id;angle=null;zoom=1;
  try{const im=new Image();im.src=item.image_url;await im.decode();if(activeCase?.id!==caseId||sheetId!==id)return;im.dataset.version=id;sheetImage=im;$('multi-sheet-content').hidden=false;$('multi-sheet-meta').textContent='Sheet '+id+' · '+im.naturalWidth+' × '+im.naturalHeight+' · SHA-256 '+item.sha256;await display(null);renderAngles();}
  catch(e){$('multi-sheet-content').hidden=true;status('Saved sheet unavailable or failed integrity validation.',true);}
 }
 $('multi-sheet-select').onchange=()=>openSheet($('multi-sheet-select').value);
 function panelURL(item,p){return '/api/cases/'+activeCase.id+'/views/'+item.job_id+'/layouts/'+item.layout.id+'/'+p.angle+'.png';}
 function renderAngles(){
  const item=currentSheet();if(!item)return;$('multi-angle-buttons').replaceChildren();
  for(const [id,name] of ANGLES){const panel=item.layout?.panels.find(p=>p.angle===id);if(!panel)continue;const b=document.createElement('button');b.type='button';b.className='secondary';b.textContent=name;b.setAttribute('aria-pressed',String(angle===id));b.onclick=()=>display(id);$('multi-angle-buttons').append(b);}
  $('multi-layout-status').textContent=item.layout?'Available angles are operator-reviewed crops of the returned sheet. Review '+item.layout.id.slice(0,8)+' · '+item.layout.created_at+'. Not independent renders or a 3D mesh.':'Sheet only. Independent angles are unavailable until the actual poses and panel boundaries are checked.';availability();
 }
 async function display(id){
  const item=currentSheet();if(!item||!sheetImage)return;const selectedSheet=sheetId;angle=id;zoom=1;let url=item.image_url,label='Original AI-generated 2D sheet';
  if(id){const p=item.layout?.panels.find(p=>p.angle===id);if(!p)return;url=panelURL(item,p);label=ANGLES.find(a=>a[0]===id)[1]+' · reviewed crop of returned 2D sheet';}
  const im=new Image();im.src=url;
  try{await im.decode();if(sheetId!==selectedSheet||angle!==id)return;displayImage=im;$('multi-image').src=im.src;$('multi-view-label').textContent=label+' · identity consistency is not guaranteed.';$('multi-download').href=url;$('multi-download').download='witnesstrace-'+activeCase.id+'-'+sheetId+(id?'-'+id+'.png':'-original-sheet.'+(item.image_format==='JPEG'?'jpg':item.image_format.toLowerCase()));$('multi-download').textContent=id?'Download angle crop':'Download original sheet';fit();renderAngles();}
  catch(e){status('This view could not be loaded. The original sheet remains available.',true);}
 }
 function fit(){if(!displayImage)return;const available=$('multi-viewport').clientWidth-18;const h=$('multi-viewport').clientHeight-18;const factor=Math.min(available/displayImage.naturalWidth,h/displayImage.naturalHeight)*zoom;$('multi-image').style.width=Math.max(1,displayImage.naturalWidth*factor)+'px';$('multi-image').style.height=Math.max(1,displayImage.naturalHeight*factor)+'px';$('multi-zoom-value').textContent=Math.round(zoom*100)+'%';}
 $('multi-sheet').onclick=()=>display(null);$('multi-reset').onclick=()=>{zoom=1;fit();$('multi-viewport').scrollTo(0,0);};$('multi-zoom-in').onclick=()=>{zoom=Math.min(5,zoom*1.25);fit();};$('multi-zoom-out').onclick=()=>{zoom=Math.max(.5,zoom*.8);fit();};
 new ResizeObserver(fit).observe($('multi-viewport'));
 function navigate(delta){const panels=currentSheet()?.layout?.panels;if(!panels?.length)return;const index=panels.findIndex(p=>p.angle===angle);display(panels[(index+delta+panels.length)%panels.length].angle);}
 $('multi-previous').onclick=()=>navigate(-1);$('multi-next').onclick=()=>navigate(1);
 $('multi-full').onclick=()=>{if(displayImage)Refinement.viewFull({image_url:displayImage.src,display_label:angle?'Reviewed 2D angle crop':'Original 2D concept sheet'});};
 const viewport=$('multi-viewport');$('multi-image').draggable=false;let pan=null;viewport.onpointerdown=e=>{if(e.button>0)return;e.preventDefault();pan={id:e.pointerId,x:e.clientX,y:e.clientY,sx:viewport.scrollLeft,sy:viewport.scrollTop};viewport.setPointerCapture(e.pointerId);};viewport.onpointermove=e=>{if(pan&&pan.id===e.pointerId){viewport.scrollLeft=pan.sx+pan.x-e.clientX;viewport.scrollTop=pan.sy+pan.y-e.clientY;}};viewport.onpointerup=()=>pan=null;viewport.onpointercancel=()=>pan=null;
 for(const [id,name] of ANGLES){const box=document.createElement('section');box.className='layout-panel';const h=document.createElement('h3');h.textContent=name;const fields=document.createElement('div');fields.className='layout-coordinates';for(const field of ['x','y','width','height']){const label=document.createElement('label');label.textContent=field;const input=document.createElement('input');input.type='number';input.min='0';input.step='1';input.id='layout-'+id+'-'+field;input.oninput=()=>{$('layout-checked').checked=false;drawLayout();availability();};label.append(input);fields.append(label);}box.append(h,fields);$('layout-fields').append(box);}
 function rectangles(){return ANGLES.map(([angle])=>({angle,rect:['x','y','width','height'].map(field=>Number($('layout-'+angle+'-'+field).value))}));}
 function fillRects(panels){for(const p of panels)for(const [i,field] of ['x','y','width','height'].entries())$('layout-'+p.angle+'-'+field).value=String(p.rect[i]);drawLayout();}
 function drawLayout(){if(!sheetImage)return;const canvas=$('layout-canvas');canvas.width=sheetImage.naturalWidth;canvas.height=sheetImage.naturalHeight;const c=canvas.getContext('2d');c.drawImage(sheetImage,0,0);c.lineWidth=Math.max(2,canvas.width/500);c.font=Math.max(14,canvas.width/55)+'px sans-serif';for(const [index,p] of rectangles().entries()){c.strokeStyle=['#2166ee','#19a07c','#d35165','#a17bee'][index];c.fillStyle=c.strokeStyle;c.strokeRect(...p.rect);c.fillText(p.angle,p.rect[0]+7,p.rect[1]+25);}}
 $('multi-layout').onclick=()=>{if(!currentSheet()||!sheetImage)return;$('layout-checked').checked=false;$('layout-note').value='';$('layout-status').textContent='Check the actual sheet before publishing angle crops.';fillRects(currentSheet().layout?.panels||ANGLES.map(([angle])=>({angle,rect:[0,0,0,0]})));$('layout-dialog').showModal();availability();};
 $('layout-guide').onclick=()=>{if(!sheetImage)return;const w=sheetImage.naturalWidth,h=sheetImage.naturalHeight,x=Math.floor(w/2),y=Math.floor(h/2);fillRects([{angle:'front',rect:[0,0,x,y]},{angle:'left',rect:[x,0,w-x,y]},{angle:'right',rect:[0,y,x,h-y]},{angle:'three_quarter',rect:[x,y,w-x,h-y]}]);$('layout-checked').checked=false;$('layout-status').textContent='Unverified guide only. Adjust rectangles and verify actual poses before checking the confirmation.';availability();};
 $('layout-checked').onchange=availability;$('layout-close').onclick=()=>$('layout-dialog').close();
 $('layout-save').onclick=async()=>{
  if(layoutBusy||!$('layout-checked').checked)return;layoutBusy=true;availability();const caseId=activeCase.id,id=sheetId;
  try{const layout=await api('/api/cases/'+caseId+'/views/'+id+'/layouts','POST',{checked:true,panels:rectangles(),note:$('layout-note').value});if(activeCase?.id!==caseId||sheetId!==id)return;currentSheet().layout=layout;$('layout-status').textContent='Checked panel layout saved. Crops are available.';renderAngles();$('layout-dialog').close();}
  catch(e){$('layout-status').textContent=e.message;}
  finally{layoutBusy=false;availability();}
 };
 function download(url,filename){const a=document.createElement('a');a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();}
 $('export-png').onclick=()=>{if(selected())download('/api/cases/'+activeCase.id+'/versions/'+selected().id+'/export.png','witnesstrace-'+activeCase.id+'-'+selected().id+'.png');};
 $('export-json').onclick=()=>{if(selected())download('/api/cases/'+activeCase.id+'/versions/'+selected().id+'/export.json','witnesstrace-'+activeCase.id+'-'+selected().id+'.json');};
 $('export-report').onclick=async()=>{
  if(exportBusy||!selected())return;exportBusy=true;availability();const caseId=activeCase.id,versionId=selected().id;$('export-status').textContent='Building PDF from persisted records…';
  try{const key=JSON.stringify([caseId,versionId,activeCase.revision]);if(!reportRequest||reportFingerprint!==key){reportRequest={version_id:versionId,request_key:crypto.randomUUID().replaceAll('-','')};reportFingerprint=key;}const report=await api('/api/cases/'+caseId+'/reports','POST',reportRequest);if(activeCase?.id!==caseId)return;$('export-status').textContent='Persisted PDF/PNG/JSON report saved · '+report.id;await refresh();openReport(report);}
  catch(e){$('export-status').textContent='Report failed: '+e.message+' Records are unchanged; retry Create case PDF report.';}
  finally{exportBusy=false;availability();}
 };
 function openReport(report){$('report-meta').textContent='Case '+report.case_id+' · version '+report.version_id+' · '+report.created_at+' · immutable report '+report.id;for(const kind of ['pdf','json','png']){$('report-'+kind).href=report.files[kind].url;$('report-'+kind).download=report.files[kind].filename;}$('report-preview').src=report.preview_url;$('report-dialog').showModal();}
 $('report-close').onclick=()=>$('report-dialog').close();
 return {availability,selectionChanged,caseChanged,refresh};
})();
