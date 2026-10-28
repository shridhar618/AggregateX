'use strict';
const $ = id => document.getElementById(id);
let busy=false, activeCase=null, dirty=false, pollTimer=null, loading=false, appending=false, labReady=false;
const tabs = [...document.querySelectorAll('[role=tab]')];
function selectTab(name, focus = false) {
  if(name!=='enhance'&&window.Enhance)Enhance.deactivate();
  $('generator').hidden=false; $('refinement-panel').hidden=true;
  tabs.forEach(tab => {
    const selected = tab.dataset.tab === name;
    tab.setAttribute('aria-selected', String(selected));
    tab.tabIndex = selected ? 0 : -1;
    $(tab.getAttribute('aria-controls')).hidden = !selected;
    if (selected && focus) tab.focus();
  });
  $('generate-footer').hidden = name !== 'text';
  if(name==='sketch'&&window.Sketchpad)Sketchpad.openSelected();
  if(name==='enhance'&&window.Enhance)Enhance.openSelected();
}
tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => selectTab(tab.dataset.tab));
  tab.addEventListener('keydown', event => {
    let next;
    if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
    if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = tabs.length - 1;
    if (next !== undefined) { event.preventDefault(); selectTab(tabs[next].dataset.tab, true); }
  });
});
document.querySelectorAll('[data-go]').forEach(button => button.addEventListener('click', () => selectTab(button.dataset.go, true)));
// Text attributes only; advanced facial geometry remains Phase 03.
for (const id of ['complexion','hair','eyes','facial-hair','age']) {
  const host = id === 'age' ? document.querySelector('.age-inputs') : $(id).parentElement;
  const metadata = document.createElement('div'); metadata.className='trait-metadata';
  for (const [field, options] of [['confidence',[['unknown','Unknown'],['tentative','Tentative'],['certain','Certain']]],['source',[['operator','Operator input'],['witness','Witness quote']]]]) {
    const label=document.createElement('label'); label.textContent=field==='source'?'Source':'Recollection';
    const select=document.createElement('select'); select.id=id+'-'+field;select.setAttribute('aria-label',id+' '+field);
    for (const [value,text] of options) { const option=document.createElement('option');option.value=value;option.textContent=text;select.append(option); }
    label.append(select); metadata.append(label);
  }
  const quote=document.createElement('input');quote.id=id+'-quote';quote.type='text';quote.maxLength=1800;quote.placeholder='Exact quote from recorded statement';quote.setAttribute('aria-label',id+' source quote');quote.hidden=true;
  metadata.append(quote);
  if(id==='age')host.after(metadata);
  else {const wrapper=document.createElement('div');wrapper.className='trait-control';host.replaceWith(wrapper);wrapper.append(host,metadata);}
  $(id+'-source').addEventListener('change',()=>{quote.hidden=$(id+'-source').value!=='witness';});
}
function caseMessage(message,error=false) { $('case-status').textContent=message;$('case-status').classList.toggle('error',error);$('retry-connection').hidden=!error; }
function state(status,message,error=false) {
  $('output-state').textContent=status;$('job-status').textContent='JOB '+status;
  $('activity').textContent=message;$('activity').classList.toggle('error',error);
}
async function jsonResponse(response) {
  let data;
  try{data=await response.json();}catch(e){throw Error('The server returned an unreadable response ('+response.status+'). Retry the action when the connection is restored.');}
  if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'Invalid request ('+response.status+'). Check required values and witness quotes.');
  return data;
}
const api=(path,method='GET',body)=>fetch(path,{method,headers:{'Content-Type':'application/json'},cache:'no-store',...(body===undefined?{}:{body:JSON.stringify(body)})}).then(jsonResponse);
function permitted(){return !!activeCase && (!!activeCase.synthetic || !!activeCase.frozen_at);}
function unlock(){
  $('parameters').hidden=loading||!permitted();$('submit').disabled=busy||loading||!permitted();
  if(labReady)CharacterLab.availability(permitted()&&!loading,busy||loading);
  $('save-case').disabled=!activeCase||loading;
  $('capture').hidden=!activeCase||!!activeCase.frozen_at;
  $('capture').disabled=busy||loading;
  $('description').disabled=!activeCase||loading;
  $('append-note').disabled=busy||loading;
  $('case-select').disabled=busy||loading;$('new-case').disabled=busy||loading;
  if(window.Refinement)Refinement.availability();
  if(window.Sketchpad)Sketchpad.availability();
  if(window.Enhance)Enhance.availability();
  if(window.CaseDeliverables)CaseDeliverables.availability();
  $('form-state').textContent=!activeCase?'Create or select a case to continue.':(permitted()?(activeCase.synthetic?'SYNTHETIC DEMO · one image per explicit request':'Original account frozen · optional sourced addenda'):'Freeze the independent account before viewing or generating images.');
}
function resetImage(){
  $('result').hidden=true;$('result').removeAttribute('src');$('download').hidden=true;$('download').removeAttribute('href');
  $('placeholder').hidden=false;$('image-meta').textContent='';state('IDLE','No image generated for this case.');
}
async function showImage(version,caseId){
  if(!version)return;
  const selectedId=version.id;
  const decoded=new Image();decoded.src=version.image_url;
  try{await decoded.decode();$('retry-image').hidden=true;}catch(error){$('retry-image').hidden=false;throw Error('Selected image could not be decoded or retrieved. Retry selected image, or choose another saved version.');}
  if(activeCase?.id!==caseId||!permitted()||(activeCase.selected_version_id && activeCase.selected_version_id!==selectedId))return;
  document.querySelector('.watermark').textContent=version.workspace==='upload'?'UPLOADED SOURCE · UNVERIFIED':version.workspace==='enhance'?'LOCALLY ADJUSTED IMAGE · SOURCE PRESERVED':version.workspace==='sketch'?'MODIFIED ILLUSTRATION · LOCAL ARTIST EDIT':'AI-GENERATED ILLUSTRATION · NOT A REAL PHOTO';
  document.querySelector('.caution').textContent=version.workspace==='upload'?'Uploaded source. Provenance and accuracy are not verified by this workbench.':version.workspace==='enhance'?'Locally adjusted image. Adjustments do not recover reliable missing facial information or verify identity.':'Illustrative AI composite. Not a verified likeness or proof of identity or guilt.';
  $('result').alt=version.workspace==='upload'?'Uploaded source image; unverified provenance':version.workspace==='enhance'?'Locally adjusted image; original source preserved':version.workspace==='sketch'?'Artist-edited illustration; not witness testimony':'AI-generated illustrative composite; not a verified likeness';
  $('result').src=decoded.src;$('result').hidden=false;$('placeholder').hidden=true;
  $('download').href=version.image_url;$('download').hidden=false;
  if(window.Refinement)Refinement.sync();
  if(window.Sketchpad)Sketchpad.selectionChanged();
  if(window.Enhance)Enhance.selectionChanged();
  if(window.CaseDeliverables)CaseDeliverables.selectionChanged();
  $('image-meta').textContent='V'+(activeCase.versions.findIndex(v=>v.id===version.id)+1)+' · '+decoded.naturalWidth+' × '+decoded.naturalHeight+' · '+version.id.slice(0,8)+' · SHA-256 recorded · '+new Date(version.created_at).toLocaleString()+' · '+(version.workspace==='multiview'?'Experimental 2D concept sheet':version.workspace==='upload'?'Uploaded source':version.workspace==='enhance'?'Local pixel adjustment':version.workspace==='sketch'?'Local artist edit · modified illustration':version.workspace==='refinement'?'Operator refinement':version.workspace==='lab'?'Character Lab hypothesis':'Text generation');
  if(busy){state('RUNNING','Saved version selected for viewing. The submitted generation is still running.');return;}
  if(version.workspace==='upload'||version.workspace==='enhance'){state('SAVED',version.workspace==='upload'?'Uploaded source · original bytes retained. Not an AI-generated result.':'Locally adjusted image · original preserved. No AI generation or recovered missing information.');return;}
  if(version.workspace==='sketch'){state('SAVED','Modified illustration · local artist edits. No AI generation; not witness testimony.');return;}
  state('SUCCEEDED',version.workspace==='lab'?'New generated hypothesis. Unchanged features are best-effort; appearance may drift.':'Saved case image loaded. Illustrative composite; review before use.');
}
function getSharedAttribute(id){
  const value=id==='age'?($('age-unknown').checked?null:$('age-number').value):($(id).value||null);
  return {value,confidence:value===null?'unknown':$(id+'-confidence').value,source:$(id+'-source').value,quote:$(id+'-quote').value};
}
function setSharedAttribute(id,a){
  if(id==='age'){$('age-unknown').checked=a.value===null;$('age-number').value=$('age').value=a.value||'35';$('age').disabled=$('age-number').disabled=a.value===null;}
  else $(id).value=a.value||'';
  $(id+'-confidence').value=a.confidence;$(id+'-source').value=a.source;$(id+'-quote').value=a.quote;$(id+'-quote').hidden=a.source!=='witness';
}
function draftFromForm(noteOverride){
  const attributes=Object.fromEntries(['complexion','hair','eyes','facial-hair','age'].map(id=>[id,getSharedAttribute(id)]));
  return {attributes,lab:labReady?CharacterLab.read():activeCase?.draft.lab||{},style:document.querySelector('[name=style]:checked').value,view:document.querySelector('[name=view]:checked').value,note:noteOverride===undefined?(activeCase?.frozen_at?$('description').value:''):noteOverride,note_source:$('note-source').value};
}
function setDirty(){
  if(activeCase&&!loading){dirty=true;caseMessage(activeCase.title+' · Unsaved draft changes');}
  if(labReady){CharacterLab.syncPresentation('style',document.querySelector('[name=style]:checked').value);CharacterLab.syncPresentation('view',document.querySelector('[name=view]:checked').value);CharacterLab.invalidate();CharacterLab.refresh();}
}
// Lab manages its draft before refreshing labels; do not reset a checkbox between input and change.
for(const eventName of ['input','change'])$('generator').addEventListener(eventName,event=>{if(!event.target.closest('#panel-lab')&&!event.target.closest('#panel-sketch')&&!event.target.closest('#panel-enhance')){if(labReady)CharacterLab.clearUndo();setDirty();}});
for(const id of ['complexion','hair','eyes','facial-hair'])$(id).addEventListener('change',()=>{
  setSharedAttribute(id,{value:$(id).value||null,confidence:$(id).value?'tentative':'unknown',source:'operator',quote:''});
});
$('age-unknown').addEventListener('change',()=>{
  $('age').disabled=$('age-number').disabled=$('age-unknown').checked;
  setSharedAttribute('age',{value:$('age-unknown').checked?null:$('age-number').value,confidence:$('age-unknown').checked?'unknown':'tentative',source:'operator',quote:''});
});
$('age').addEventListener('input',()=>{$('age-number').value=$('age').value;setSharedAttribute('age',{value:$('age').value,confidence:'tentative',source:'operator',quote:''});});
$('age-number').addEventListener('input',()=>{if($('age-number').validity.valid){$('age').value=$('age-number').value;setSharedAttribute('age',{value:$('age-number').value,confidence:'tentative',source:'operator',quote:''});}});
async function refreshSelector(){
  const cases=await api('/api/cases');$('case-select').replaceChildren();
  const empty=document.createElement('option');empty.value='';empty.textContent='Select a case';$('case-select').append(empty);
  for(const record of cases){const option=document.createElement('option');option.value=record.id;option.textContent=(record.synthetic?'DEMO · ':'')+record.title;$('case-select').append(option);}
  $('case-select').value=activeCase?.id||'';
}
function renderRecords(){
  if(window.Refinement)Refinement.records();
  $('case-history').replaceChildren();
  for(const event of activeCase.events){const p=document.createElement('p');p.textContent=event.created_at+' · '+event.kind.replaceAll('_',' ')+' · '+event.detail;$('case-history').append(p);}
  const notes=activeCase.statements.filter(s=>s.kind==='clarification');$('clarifications').hidden=!notes.length;$('clarification-list').replaceChildren();
  for(const note of notes){const p=document.createElement('p');p.textContent=note.source+' · '+note.created_at+'\n'+note.text;$('clarification-list').append(p);}
}
async function renderCase(record){
  clearTimeout(pollTimer);activeCase=record;dirty=false;resetImage();
  failedDownload=null;$('download-status').hidden=true;$('retry-download').hidden=true;$('retry-image').hidden=true;
  if(window.Refinement)Refinement.load();
  if(window.Sketchpad)Sketchpad.caseChanged();
  if(window.Enhance)Enhance.caseChanged();
  if(window.CaseDeliverables)CaseDeliverables.caseChanged();
  localStorage.setItem('witnesstrace-case',record.id);$('case-select').value=record.id;
  const original=record.statements.find(s=>s.kind==='original');
  $('demo').checked=!!record.synthetic;
  $('description').value=record.frozen_at?record.draft.note:original.text;
  $('description').required=!record.frozen_at;$('description').minLength=record.frozen_at?0:10;
  $('description').placeholder=record.frozen_at?'Optional clarification; append it to the case before generation…':'Record the account here, in the witness’s own words…';
  $('description-label').textContent=record.frozen_at?'Clarification draft':'First free-recall account';
  $('recall-help').textContent=record.frozen_at?'The original account is frozen below. New clarifications are append-only.':'In your own words, describe what you remember. Include uncertainty and leave anything you do not recall unspecified.';
  $('original-account').hidden=!record.frozen_at;$('original-text').textContent=original.text;
  $('account-meta').textContent='Case '+record.id+' · '+(record.synthetic?'SYNTHETIC DEMO · ':'')+(record.frozen_at?'Frozen '+record.frozen_at:'Original draft · source '+original.source);
  $('clarification-controls').hidden=!record.frozen_at;
  $('note-source').value=record.draft.note_source||'operator';
  for(const id of ['complexion','hair','eyes','facial-hair','age'])setSharedAttribute(id,record.draft.attributes[id]);
  for(const name of ['style','view'])for(const input of document.querySelectorAll('[name='+name+']'))input.checked=input.value===record.draft[name];
  if(labReady)CharacterLab.load(record.draft,record.last_generated_draft,record.id);
  renderRecords();busy=false;
  if(permitted()&&record.versions.length){try{await showImage(record.versions.find(v=>v.id===record.selected_version_id)||record.versions.at(-1),record.id);}catch(error){state('FAILED','Saved image unavailable or failed integrity check.',true);}}
  const latest=record.jobs.at(-1);
  if(latest?.status==='working'){busy=true;$('submit').textContent='Generating…';pollTimer=setTimeout(()=>poll(latest.id,record.id),100);}
  else if(latest?.status==='failed')state('FAILED',latest.message,true);
  caseMessage(record.title+' · '+(record.synthetic?'SYNTHETIC DEMO · ':'')+'Saved locally · revision '+record.revision);unlock();
}
async function loadCase(id){
  const priorImageHidden=$('result').hidden,priorDownloadHidden=$('download').hidden;
  loading=true;$('result').hidden=true;$('download').hidden=true;unlock();
  try{const record=await api('/api/cases/'+encodeURIComponent(id));await renderCase(record);}
  catch(error){$('case-select').value=activeCase?.id||'';$('result').hidden=priorImageHidden;$('download').hidden=priorDownloadHidden;throw error;}
  finally{loading=false;unlock();if(!$('panel-sketch').hidden&&window.Sketchpad)Sketchpad.openSelected();if(!$('panel-enhance').hidden&&window.Enhance)Enhance.openSelected();}
}
async function saveCurrent(noteOverride){
  if(!activeCase)throw Error('Create a case first.');
  if(!$('age-number').disabled&&!$('age-number').validity.valid)throw Error('Estimated age must be 18–100.');
  const body={revision:activeCase.revision,draft:draftFromForm(noteOverride)};
  if(!activeCase.frozen_at)body.original=$('description').value;
  const record=await api('/api/cases/'+activeCase.id,'PUT',body);
  // Keep form focus/draft during a save; authoritative revision advances atomically.
  activeCase=record;dirty=JSON.stringify(draftFromForm(noteOverride))!==JSON.stringify(body.draft);renderRecords();caseMessage(record.title+(dirty?' · Saved snapshot; newer form edits remain unsaved':' · Saved locally')+' · revision '+record.revision);
  return record;
}
$('save-case').addEventListener('click',async()=>{try{await saveCurrent();}catch(error){caseMessage(error.message,true);}});
$('capture').addEventListener('click',async()=>{
  if(!activeCase||busy)return;
  try{
    const text=$('description').value;
    if(text.trim().length<10)throw Error('Enter at least 10 non-whitespace characters to freeze the account.');
    await saveCurrent();
    const record=await api('/api/cases/'+activeCase.id+'/freeze','POST',{text,revision:activeCase.revision});
    await renderCase(record);
  }catch(error){caseMessage(error.message,true);}
});
$('append-note').addEventListener('click',async()=>{
  if(appending)return;appending=true;$('append-note').disabled=true;
  try{
    const text=$('description').value,source=$('note-source').value;
    if(!text.trim())throw Error('Enter a clarification before appending.');
    // Append first; then clear only the saved pending note. A failed save leaves the appended statement visible on reload.
    const record=await api('/api/cases/'+activeCase.id+'/clarifications','POST',{text,source});
    activeCase.revision=record.revision;
    await saveCurrent('');
    await renderCase(await api('/api/cases/'+activeCase.id));
  }catch(error){caseMessage(error.message,true);}
  finally{appending=false;unlock();}
});
$('new-case').addEventListener('click',()=>{$('new-case-error').textContent='';$('new-case-dialog').showModal();$('case-title').focus();});
$('cancel-case').addEventListener('click',()=>$('new-case-dialog').close());
$('new-case-form').addEventListener('submit',async event=>{
  event.preventDefault();if((dirty||window.Sketchpad?.isDirty()||window.Enhance?.isDirty())&&!confirm('Leave unsaved changes? Save the case draft, sketch and enhancement with their separate save actions to keep them.'))return;
  $('create-case').disabled=true;
  try{const record=await api('/api/cases','POST',{title:$('case-title').value,synthetic:$('case-synthetic').checked});await refreshSelector();await renderCase(record);$('new-case-dialog').close();$('new-case-form').reset();}
  catch(error){$('new-case-error').textContent=error.message;}
  finally{$('create-case').disabled=false;}
});
$('case-select').addEventListener('change',async()=>{
  const id=$('case-select').value;
  if(!id){$('case-select').value=activeCase?.id||'';return;}
  if((dirty||window.Sketchpad?.isDirty()||window.Enhance?.isDirty())&&!confirm('Leave unsaved changes? Save the case draft, sketch and enhancement with their separate save actions to keep them.')){$('case-select').value=activeCase?.id||'';return;}
  try{await loadCase(id);}catch(error){caseMessage(error.message,true);}
});
async function poll(id,caseId){
  if(activeCase?.id!==caseId)return;
  try{
    const job=await api('/api/jobs/'+encodeURIComponent(id));
    if(job.status==='complete'){
      $('connection').textContent='ONLINE GENERATION';$('connection').classList.add('online');
      const record=await api('/api/cases/'+caseId);
      // Preserve edits made while generation was running. Load only image/history/job metadata.
      activeCase.versions=record.versions;activeCase.events=record.events;activeCase.jobs=record.jobs;activeCase.last_generated_draft=record.last_generated_draft;activeCase.selected_version_id=record.selected_version_id;activeCase.preferred_version_id=record.preferred_version_id;activeCase.refinements=record.refinements;renderRecords();
      if(labReady)CharacterLab.setBaseline(record.last_generated_draft);
      busy=false;await showImage(record.versions.find(v=>v.id===record.selected_version_id)||record.versions.find(v=>v.id===id),caseId);$('submit').textContent='Generate Composite';unlock();
    }else if(job.status==='failed'){
      const failedRecord=await api('/api/cases/'+caseId);activeCase.events=failedRecord.events;activeCase.refinements=failedRecord.refinements;renderRecords();busy=false;$('submit').textContent='Generate Composite';unlock();
      state(/timed out|deadline/i.test(job.message)?'TIMED-OUT':'FAILED',job.message+' Previous image and draft retained.',true);
    }else{state('RUNNING','Generating through the authenticated Codex CLI. Network required; this may take several minutes.');pollTimer=setTimeout(()=>poll(id,caseId),2000);}
  }catch(error){
    state('UNKNOWN','Connection lost; job state is unknown. Reload this case to reconnect. Previous image retained.',true);
    busy=false;$('submit').textContent='Generate Composite';unlock();
  }
}
async function generateCurrent(workspace){
  if(busy||!permitted())return;
  busy=true;unlock();$('submit').textContent='Generating…';
  try{
    await saveCurrent();
    if(activeCase.draft.note)throw Error('Append the pending clarification before generating.');
    state('SUBMITTING','Submitting one generation request…');
    const job=await api('/api/generate','POST',{description:'Case generation request',style:activeCase.draft.style,case_id:activeCase.id,case_revision:activeCase.revision,workspace});
    await poll(job.job_id,activeCase.id);
  }catch(error){state('FAILED',error.message,true);busy=false;$('submit').textContent='Generate Composite';unlock();}
}
$('generator').addEventListener('submit',async event=>{event.preventDefault();await generateCurrent('text');});
$('update-preview').addEventListener('click',()=>generateCurrent('lab'));
$('review-prompt').addEventListener('click',async()=>{
  if(!permitted())return;
  try{
    const reviewedCase=activeCase.id,draft=draftFromForm();
    const preview=await api('/api/cases/'+reviewedCase+'/prompt-preview','POST',draft);
    if(activeCase?.id!==reviewedCase)return;
    if(JSON.stringify(draft)!==JSON.stringify(draftFromForm())){$('prompt-budget').textContent='Draft changed during review; review again.';return;}
    $('prompt-text').textContent=preview.description;
    $('prompt-budget').textContent=preview.length+' / '+preview.limit+' characters'+(preview.over_limit?' · Too long: no fields or testimony were truncated. Reduce optional requests explicitly.':' · Fits the current generator.');
    $('prompt-budget').classList.toggle('error',preview.over_limit);
  }catch(error){$('prompt-budget').textContent=error.message;}
});
window.addEventListener('beforeunload',event=>{if(dirty||window.Sketchpad?.isDirty()||window.Enhance?.isDirty()){event.preventDefault();event.returnValue='';}});
async function initialize(){
  unlock();
  try{
    const health=await api('/api/health');$('connection').textContent=health.codex_installed?'GENERATION UNKNOWN · CLI FOUND':'GENERATOR UNAVAILABLE';
    const schema=await api('/api/lab-schema');
    if(!labReady)CharacterLab.init(schema,{getShared:getSharedAttribute,setShared:setSharedAttribute,change:setDirty,style:()=>document.querySelector('[name=style]:checked').value,view:()=>document.querySelector('[name=view]:checked').value,setPresentation:(name,value)=>{for(const input of document.querySelectorAll('[name='+name+']'))input.checked=input.value===value;}});
    labReady=true;unlock();
    await refreshSelector();
    const selected=localStorage.getItem('witnesstrace-case');
    if(!activeCase&&selected&&[...$('case-select').options].some(option=>option.value===selected))await loadCase(selected);
    else if(activeCase)caseMessage(activeCase.title+' · Connection restored; current draft retained.');
    else caseMessage('Create a case to record an independent account, or select a saved case.');
  }catch(error){caseMessage('Unable to load cases: '+error.message,true);}
}
$('retry-connection').onclick=initialize;
initialize();

$('retry-image').onclick=async()=>{
  if(!activeCase)return;
  const version=activeCase.versions.find(v=>v.id===activeCase.selected_version_id)||activeCase.versions.at(-1);
  try{await showImage(version,activeCase.id);}catch(error){state('FAILED',error.message,true);}
};
$('open-exports').onclick=()=>{
  $('exports-section').open=true;$('exports-section').scrollIntoView({block:'nearest'});
  $('export-report').focus({preventScroll:true});
};
// Fetch explicit downloads so HTTP failures remain recoverable in the dashboard.
let failedDownload=null;
async function downloadFile(url,filename){
  $('download-status').hidden=false;$('download-status').classList.remove('error');
  $('download-status').textContent='Preparing download…';$('retry-download').hidden=true;const caseId=activeCase?.id;
  try{
    const response=await fetch(url,{cache:'no-store'});
    if(!response.ok){await jsonResponse(response);}
    const blob=await response.blob();if(!blob.size)throw Error('The downloaded file is empty.');
    const disposition=response.headers.get('Content-Disposition');
    const serverName=disposition?.match(/filename="([^"/\\]+)"/);
    const objectURL=URL.createObjectURL(blob),link=document.createElement('a');
    link.href=objectURL;link.download=serverName?.[1]||filename||'witnesstrace-download';
    document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(objectURL),60000);
    if(activeCase?.id!==caseId)return;failedDownload=null;$('download-status').textContent='Download prepared · '+blob.size.toLocaleString()+' bytes.';
  }catch(error){if(activeCase?.id!==caseId)return;failedDownload={url,filename};$('download-status').textContent='Download failed: '+error.message+' Use Retry download when the server is available.';$('download-status').classList.add('error');$('retry-download').hidden=false;}
}
document.addEventListener('click',event=>{
  const link=event.target.closest('a[download]');if(!link||!link.href||!link.href.startsWith(location.origin+'/'))return;
  event.preventDefault();downloadFile(link.href,link.download);
});
$('retry-download').onclick=()=>{if(failedDownload)downloadFile(failedDownload.url,failedDownload.filename);};
