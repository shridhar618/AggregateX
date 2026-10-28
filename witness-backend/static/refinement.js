'use strict';
window.Refinement=(()=>{
 let reviewed=null,reviewKey='',requestKey=null,pendingPayload=null,selecting=false,compared=0,previewPair=null;
 const current=()=>activeCase?.versions.find(v=>v.id===activeCase.selected_version_id)||activeCase?.versions.at(-1);
 const label=v=>{
  if(v.display_label)return v.display_label;
  return 'V'+(activeCase.versions.indexOf(v)+1)+' · '+(v.workspace==='multiview'?'Concept Multi-View · 2D':v.workspace==='upload'?'Uploaded source':v.style+(['sketch','enhance'].includes(v.workspace)?' · Modified':''))+(activeCase.preferred_version_id===v.id?' · Preferred':'');
 };
 const fingerprint=()=>JSON.stringify({case_id:activeCase?.id,parent:current()?.id,instruction:$('refinement-input').value,draft:draftFromForm(),revision:activeCase?.revision});
 function availability(){
  const ready=permitted()&&!loading&&!!current();
  for(const id of ['open-refinement','full-resolution','prefer-version'])$(id).disabled=!ready||busy||selecting;
  for(const id of ['prefer-before','prefer-after'])$(id).disabled=!ready||selecting||!!previewPair;
  $('active-version').disabled=!ready||selecting; // Viewing another revision remains possible while generating.
  $('open-compare').disabled=!ready||(activeCase.versions.length<2&&!window.Enhance?.hasPreview());
  $('review-refinement').disabled=!ready||busy;
  $('regenerate').disabled=!ready||busy||!reviewed||reviewed.over_limit||reviewKey!==fingerprint();
  $('regenerate').textContent=busy?'Generating revision…':($('refinement-status').dataset.failed==='true'?'Retry regeneration':'Regenerate');
  if(busy){const parentId=pendingPayload?.parent_id||activeCase?.refinements?.findLast(r=>r.status==='working')?.parent_id;const number=activeCase?.versions.findIndex(v=>v.id===parentId)+1;$('refinement-status').textContent='Generating V'+((activeCase?.versions.length||0)+1)+(number?' from V'+number:'')+'. Selected saved image remains available for review.';}
 }
 function invalidate(){reviewed=null;requestKey=null;pendingPayload=null;$('refinement-budget').textContent='Inputs changed. Review the final prompt again.';availability();}
 function sync(){
  const v=current();if(!v)return;
  $('active-version').value=v.id;$('prefer-version').textContent=activeCase.preferred_version_id===v.id?'Preferred version':'Mark preferred';
  $('refine-preview').src=v.image_url;$('refine-parent').textContent='Editing '+label(v)+' · '+v.id.slice(0,8)+' · '+new Date(v.created_at).toLocaleString();
  availability();
 }
 function records(){
  $('version-count').textContent=activeCase.versions.length;
  $('files-help').textContent='Select any immutable revision to view or refine it. Selection preserves every image. Downloads retain original bytes.';
  const selected=current();$('active-version').replaceChildren();$('session-downloads').replaceChildren();$('session-downloads').className='revision-grid';
  activeCase.versions.forEach(v=>{
   const option=new Option(label(v),v.id);$('active-version').append(option);
   const tile=document.createElement('div');tile.className='revision-tile'+(selected?.id===v.id?' selected':'');
   const button=document.createElement('button');button.type='button';button.setAttribute('aria-label','Select '+label(v));
   const img=document.createElement('img');img.src=v.image_url;img.alt=label(v);img.loading='lazy';img.decoding='async';img.width=130;img.height=115;
   const title=document.createElement('span');title.textContent=label(v);const meta=document.createElement('small');meta.textContent=new Date(v.created_at).toLocaleString()+' · '+(v.workspace==='multiview'?'AI concept sheet · experimental':v.workspace==='upload'?'Uploaded source':v.workspace==='enhance'?'Local pixel adjustment':v.workspace==='sketch'?'Local artist edit':v.workspace==='refinement'?'Operator refinement':v.workspace==='lab'?'Character Lab':'Text')+' · Parent '+(v.parent_id?'V'+(activeCase.versions.findIndex(x=>x.id===v.parent_id)+1):'none');
   button.append(img,title,meta);button.onclick=()=>choose(v.id);tile.append(button);
   const a=document.createElement('a');a.href=v.image_url;a.download='witnesstrace-'+v.id+'.png';a.textContent=['sketch','enhance'].includes(v.workspace)?'Download edited PNG':'Download original';tile.append(a);$('session-downloads').append(tile);
  });
  $('refinement-history').replaceChildren();
  for(const item of activeCase.refinements||[]){const p=document.createElement('p');const parent=activeCase.versions.find(v=>v.id===item.parent_id);p.textContent='Operator request · '+(parent?label(parent):item.parent_id.slice(0,8))+' → '+item.status+'\n'+new Date(item.created_at).toLocaleString()+'\n'+item.instruction;$('refinement-history').append(p);}
  if(!activeCase.refinements?.length)$('refinement-history').textContent='No refinement requests yet. Model changes are not witness statements.';
  sync();
 }
 async function choose(id,preferred=false){
  if(selecting||!activeCase)return;
  if(!preferred&&window.Sketchpad&&!Sketchpad.allowSelection(id)){$('active-version').value=current().id;return;}
  if(!preferred&&window.Enhance&&!Enhance.allowSelection(id)){$('active-version').value=current().id;return;}
  selecting=true;availability();const caseId=activeCase.id;
  try{
   const record=await api('/api/cases/'+caseId+'/selection','POST',{version_id:id,preferred});if(activeCase?.id!==caseId)return;
   activeCase.selected_version_id=record.selected_version_id;activeCase.preferred_version_id=record.preferred_version_id;activeCase.events=record.events;
   if(!preferred){invalidate();await showImage(current(),caseId);}
   records();if($('comparison-dialog').open)await renderComparison();
  }catch(e){caseMessage(e.message,true);}finally{selecting=false;availability();}
 }
 $('active-version').onchange=()=>choose($('active-version').value);
 $('prefer-version').onclick=()=>choose(current().id,true);
 $('open-refinement').onclick=()=>{
  if(window.Enhance)Enhance.deactivate();$('generator').hidden=true;$('refinement-panel').hidden=false;sync();$('refinement-input').focus();
 };
 $('return-controls').onclick=()=>{const tab=tabs.find(t=>t.getAttribute('aria-selected')==='true');selectTab(tab?.dataset.tab||'text');};
 $('refinement-input').oninput=()=>{invalidate();$('refinement-status').textContent='';$('refinement-status').dataset.failed='false';};
 $('review-refinement').onclick=async()=>{
  const key=fingerprint(),caseId=activeCase.id;reviewed=null;availability();
  try{
   const payload={parent_id:current().id,instruction:$('refinement-input').value,draft:draftFromForm(),revision:activeCase.revision,request_key:crypto.randomUUID().replaceAll('-','')};
   const result=await api('/api/cases/'+caseId+'/refinement-preview','POST',payload);
   if(activeCase?.id!==caseId||fingerprint()!==key)return;
   reviewed=result;reviewKey=key;requestKey=payload.request_key;pendingPayload=payload;
   $('refinement-prompt').textContent=result.description;$('refinement-budget').textContent=result.length+' / 2500 characters'+(result.over_limit?' · Over limit. Nothing was truncated.':' · Final generation prompt ready for review.');$('refinement-budget').classList.toggle('error',result.over_limit);
  }catch(e){$('refinement-budget').textContent=e.message;}finally{availability();}
 };
 $('regenerate').onclick=async()=>{
  if(busy||!reviewed||reviewed.over_limit||reviewKey!==fingerprint())return;
  const caseId=activeCase.id;busy=true;availability();unlock();$('refinement-status').dataset.failed='false';
  try{
   // Draft is part of the immutable request snapshot; no second save can change the reviewed prompt.
   const payload={...pendingPayload,reviewed_prompt:reviewed.description};
   const job=await api('/api/cases/'+caseId+'/refine','POST',payload);
   $('refinement-status').textContent='Generating new revision from '+$('refine-parent').textContent+'. Job '+job.job_id.slice(0,8);
   await waitRefinement(job.job_id,caseId);
  }catch(e){busy=false;$('refinement-status').dataset.failed='true';$('refinement-status').textContent=e.message+' Existing image retained.';state('FAILED',e.message,true);unlock();}
 };
 async function waitRefinement(id,caseId){
  if(activeCase?.id!==caseId)return;
  try{
   const job=await api('/api/jobs/'+id);
   if(job.status==='working'){state('RUNNING','Generating a new revision via the existing Codex CLI. Parent and history retained.');pollTimer=setTimeout(()=>waitRefinement(id,caseId),2000);return;}
   const record=await api('/api/cases/'+caseId);if(activeCase?.id!==caseId)return;
   Object.assign(activeCase,{revision:record.revision,versions:record.versions,refinements:record.refinements,events:record.events,jobs:record.jobs,selected_version_id:record.selected_version_id,preferred_version_id:record.preferred_version_id,last_generated_draft:record.last_generated_draft});
   busy=false;records();renderRecords();
   if(job.status==='complete'){
    await showImage(current(),caseId);$('refinement-status').textContent='Revision saved. Select Compare to review the requested changes.';$('refinement-status').dataset.failed='false';
    $('connection').textContent='ONLINE GENERATION';$('connection').classList.add('online');
    if(labReady)CharacterLab.setBaseline(record.last_generated_draft);
    invalidate();
   }else{
    $('refinement-status').textContent=job.message+' Previous image retained. Retry submits a new attempt.';$('refinement-status').dataset.failed='true';
    state('FAILED',job.message,true);
    // Failed attempts are retained as requests, never successful versions. Explicit retry uses a new key.
    if(pendingPayload)pendingPayload.request_key=crypto.randomUUID().replaceAll('-','');
   }
   unlock();
  }catch(e){busy=false;$('refinement-status').textContent='Connection lost. Reload to reconnect before retrying.';$('refinement-status').dataset.failed='true';unlock();}
 }
 function full(v){if(!v)return;$('full-image').src=v.image_url;$('full-label').textContent=label(v)+(v.display_label?' · Preview pixels · SHA-256 ':['sketch','enhance'].includes(v.workspace)?' · Saved modified pixels · SHA-256 ':' · Original pixels · SHA-256 ')+(v.sha256||'Unsaved preview');$('image-dialog').showModal();}
 $('full-resolution').onclick=()=>window.Enhance?.isActive()&&Enhance.hasPreview()?Enhance.full():full(current());$('close-image').onclick=()=>$('image-dialog').close();
 const comparisonVersion=id=>(previewPair||activeCase.versions).find(v=>v.id===$(id).value);
 async function renderComparison(){
  for(const id of ['compare-before','compare-after'])for(const option of $(id).options){const version=(previewPair||activeCase.versions).find(v=>v.id===option.value);if(version)option.textContent=label(version);}
  const count=++compared,before=comparisonVersion('compare-before'),after=comparisonVersion('compare-after');if(!before||!after)return;
  $('comparison-status').textContent=before.id===after.id?'Choose distinct versions to compare.':'Loading saved image bytes…';
  try{
   const images=await Promise.all([before,after].map(async v=>{const img=new Image();img.src=v.image_url;await img.decode();return img;}));if(count!==compared)return;
   ['before-image','slider-before'].forEach(id=>$(id).src=images[0].src);['after-image','slider-after'].forEach(id=>$(id).src=images[1].src);
   $('before-label').textContent='BEFORE · '+label(before);$('after-label').textContent='AFTER · '+label(after);$('slider-before-label').textContent=previewPair?'INPUT':'BEFORE · V'+(activeCase.versions.indexOf(before)+1);$('slider-after-label').textContent=previewPair?'LOCAL PREVIEW':'AFTER · V'+(activeCase.versions.indexOf(after)+1);
   $('comparison-status').textContent=before.id===after.id?'Same version selected on both sides.':label(before)+' ↔ '+label(after)+(['sketch','enhance','upload'].includes(before.workspace)||['sketch','enhance','upload'].includes(after.workspace)||previewPair?' · Local changes are separate from witness testimony; missing facial information is not recovered.':' · Review requested changes; model differences are not witness claims.');
  }catch(e){$('comparison-status').textContent='Comparison image unavailable or integrity check failed.';for(const id of ['before-image','after-image','slider-before','slider-after'])$(id).removeAttribute('src');}
 }
 $('open-compare').onclick=()=>{
  if(window.Enhance?.isActive()&&Enhance.hasPreview()){Enhance.compare();return;}
  previewPair=null;for(const id of ['compare-before','compare-after'])$(id).disabled=false;
  for(const id of ['compare-before','compare-after']){$(id).replaceChildren(...activeCase.versions.map(v=>new Option(label(v),v.id)));}
  const after=current(),before=activeCase.versions.find(v=>v.id===after.parent_id)||activeCase.versions.find(v=>v.id!==after.id);
  $('compare-before').value=before.id;$('compare-after').value=after.id;$('comparison-dialog').showModal();renderComparison();
 };
 $('close-compare').onclick=()=>$('comparison-dialog').close();
 $('comparison-dialog').addEventListener('close',()=>{previewPair=null;for(const id of ['compare-before','compare-after'])$(id).disabled=false;availability();});
 for(const id of ['compare-before','compare-after'])$(id).onchange=renderComparison;
 $('full-before').onclick=()=>full(comparisonVersion('compare-before'));$('full-after').onclick=()=>full(comparisonVersion('compare-after'));
 $('prefer-before').onclick=()=>choose($('compare-before').value,true);$('prefer-after').onclick=()=>choose($('compare-after').value,true);
 function mode(slider){$('side-comparison').hidden=slider;$('slider-comparison').hidden=!slider;$('mode-side').setAttribute('aria-pressed',String(!slider));$('mode-slider').setAttribute('aria-pressed',String(slider));}
 $('mode-side').onclick=()=>mode(false);$('mode-slider').onclick=()=>mode(true);
 function split(value){$('comparison-range').value=String(value);$('slider-before-clip').style.clipPath='inset(0 '+(100-value)+'% 0 0)';$('comparison-divider').style.left=value+'%';$('comparison-range').setAttribute('aria-valuetext',Math.round(value)+' percent before image');}
 $('comparison-range').oninput=()=>split(Number($('comparison-range').value));
 const stage=$('comparison-stage');let dragging=false;
 function move(event){const rect=stage.getBoundingClientRect();split(Math.max(0,Math.min(100,(event.clientX-rect.left)/rect.width*100)));}
 stage.onpointerdown=event=>{dragging=true;stage.setPointerCapture(event.pointerId);move(event);};stage.onpointermove=event=>{if(dragging)move(event);};stage.onpointerup=()=>dragging=false;stage.onpointercancel=()=>dragging=false;
 function load(){reviewed=null;reviewKey='';pendingPayload=null;$('refinement-input').value=activeCase.refinements?.at(-1)?.status==='failed'?activeCase.refinements.at(-1).instruction:'';$('refinement-prompt').textContent='';$('refinement-budget').textContent='Review the final prompt before regenerating.';$('refinement-status').textContent='';$('refinement-status').dataset.failed='false';}
 function preview(before,after){previewPair=[before,after];for(const [id,v] of [['compare-before',before],['compare-after',after]]){$(id).replaceChildren(new Option(label(v),v.id));$(id).value=v.id;$(id).disabled=true;}$('comparison-dialog').showModal();availability();renderComparison();}
 $('comparison-zoom').oninput=()=>{const value=Number($('comparison-zoom').value);$('comparison-zoom-value').textContent=value+'%';for(const id of ['before-image','after-image','slider-before','slider-after'])$(id).style.transform='scale('+(value/100)+')';};
 return {records,sync,availability,invalidate,load,preview,viewFull:full};
})();
