'use strict';
window.Enhance=(()=>{
 let schema=null,doc=null,activated=false,loadingImage=false,saving=false,importing=false,processing=false,worker=null,sourceURL=null,resultURL=null,resultBlob=null,params=null,savedParams=null,undo=[],redo=[],timer=null,token=0,renderId=0,finishedId=0,inFlight=false,pendingRender=false,pendingSave=null,pendingImport=null,approvedSelection=null,zoom=1;
 const selected=()=>activeCase?.versions.find(v=>v.id===activeCase.selected_version_id)||activeCase?.versions.at(-1);
 const isActive=()=>activated&&!$('panel-enhance').hidden&&!$('generator').hidden;
 const isDirty=()=>!!doc&&JSON.stringify(params)!==JSON.stringify(savedParams);
 const hasPreview=()=>!!doc&&!!resultBlob&&finishedId===renderId&&!processing;
 const status=(text,error=false)=>{$('enhance-status').textContent=text;$('enhance-status').classList.toggle('error',error);};
 const label=v=>v?'V'+(activeCase.versions.indexOf(v)+1)+' · '+(v.workspace==='upload'?'Uploaded source':v.workspace==='sketch'?'Artist-edited illustration':v.workspace==='enhance'?'Locally adjusted image':'AI-generated illustration'):'No image';
 function availability(){
  const allowed=permitted()&&!loading,ready=allowed&&!!doc&&!loadingImage;
  $('enhance-content').hidden=!ready;$('enhance-source-select').disabled=!allowed||saving||importing;$('enhance-load').disabled=!allowed||!selected()||saving||importing;
  $('enhance-file').disabled=!allowed||!$('enhance-consent').checked||saving||importing;
  $('enhance-import').disabled=!allowed||!$('enhance-file').files?.length||!$('enhance-consent').checked||saving||importing;
  $('enhance-save').disabled=!ready||!hasPreview()||saving||importing||!isDirty();$('enhance-save').textContent=saving?'Saving enhanced version…':'Save Enhanced Version';
  for(const id of ['enhance-compare','enhance-full'])$(id).disabled=!ready||!hasPreview();
  $('enhance-undo').disabled=!ready||saving||undo.length===0;$('enhance-redo').disabled=!ready||saving||redo.length===0;
  $('enhance-ai').disabled=!ready||saving||busy;
  for(const input of $('enhance-controls').querySelectorAll('input'))input.disabled=saving;
  for(const id of ['enhance-grayscale','enhance-invert','enhance-resize','enhance-apply-preset','enhance-reset'])$(id).disabled=!ready||saving;
 }
 function controls(){if(!schema||!params)return;
  for(const item of schema.controls){$('enhance-'+item.key).value=params[item.key];$('enhance-'+item.key+'-value').textContent=Number(params[item.key]).toFixed(item.step<1?2:0);}
  for(const key of ['grayscale','invert'])$('enhance-'+key).checked=params[key];$('enhance-resize').value=params.resize;$('enhance-resize-value').textContent=params.resize+'%';availability();
 }
 function setParams(next,record=true){if(!doc||saving)return;if(record){undo.push(structuredClone(params));if(undo.length>100)undo.shift();redo=[];}params=structuredClone(next);pendingSave=null;controls();schedule();}
 function schedule(){clearTimeout(timer);renderId++;processing=true;status('Processing local pixels…');availability();timer=setTimeout(sendRender,160);}
 function sendRender(){if(!worker||!doc)return;if(inFlight){pendingRender=true;return;}inFlight=true;pendingRender=false;worker.postMessage({type:'render',id:renderId,adjustments:params});}
 function makeWorker(pixels,w,h){
  if(worker)worker.terminate();inFlight=false;pendingRender=false;
  worker=new Worker('/static/enhance-worker.js');worker.postMessage({type:'source',buffer:pixels.data.buffer,width:w,height:h},[pixels.data.buffer]);
  const owner=doc;
  worker.onmessage=async({data:r})=>{
   if(doc!==owner)return;inFlight=false;
   if(r.id!==renderId){if(pendingRender)sendRender();return;}
   if(r.type==='error'){processing=false;status(r.message+' Prior committed preview retained; adjust settings or Reset.',true);availability();return;}
   try{
    const bitmap=await createImageBitmap(r.blob);if(doc!==owner||r.id!==renderId){bitmap.close();if(pendingRender)sendRender();return;}
    const canvas=$('enhance-canvas');canvas.width=r.width;canvas.height=r.height;canvas.getContext('2d').drawImage(bitmap,0,0);bitmap.close();
    if(resultURL)URL.revokeObjectURL(resultURL);resultBlob=r.blob;resultURL=URL.createObjectURL(r.blob);finishedId=r.id;processing=false;
    status('Committed preview · '+r.width+' × '+r.height+' · '+(isDirty()?'unsaved local adjustments':'opened saved settings')+' · source unchanged.');
    showPreview();availability();
   }catch(e){processing=false;status('Preview decode failed: '+e.message,true);availability();}
  };
  worker.onerror=()=>{inFlight=false;processing=false;status('Local processing worker failed. Reload the selected source to retry; parameters remain visible.',true);availability();};
 }
 function showPreview(){
  if(!isActive()||!resultURL)return;document.querySelector('.caution').textContent='Local adjustments cannot recover reliable missing facial information or verify identity.';$('result').alt='Local enhancement preview; source retained; not recovered missing information';$('result').src=resultURL;$('result').hidden=false;$('placeholder').hidden=true;
  $('result').style.transform='scale('+zoom+')';$('output-state').textContent=processing?'PROCESSING':'LOCAL PREVIEW';$('activity').textContent='Local enhancement preview from '+label(activeCase.versions.find(v=>v.id===doc.parentId))+'. '+(isDirty()?'Unsaved; download link remains the selected saved image.':'Saved parameters reopened.');
  $('image-meta').textContent=$('enhance-canvas').width+' × '+$('enhance-canvas').height+' · '+doc.sourceId.slice(0,8)+' source · '+(isDirty()?'not saved':'saved state');document.querySelector('.watermark').textContent='LOCAL PIXEL ADJUSTMENT · ORIGINAL SOURCE RETAINED';
 }
 function records(){if(!activeCase)return;
  const pick=$('enhance-source-select'),old=pick.value;pick.replaceChildren(...activeCase.versions.map(v=>new Option(label(v),v.id)));pick.value=selected()?.id||old;
  $('enhance-history').replaceChildren();
  for(const v of activeCase.versions.filter(v=>v.workspace==='enhance'||v.workspace==='upload')){
   const p=document.createElement('p');p.textContent=label(v)+' · '+new Date(v.created_at).toLocaleString()+'\n'+(v.workspace==='upload'?(v.source_filename+' · original bytes retained'):'Parent '+v.parent_id?.slice(0,8)+' · '+JSON.stringify(v.adjustments));
   const button=document.createElement('button');button.type='button';button.className='secondary';button.textContent='Open '+label(v);button.onclick=()=>{$('active-version').value=v.id;$('active-version').dispatchEvent(new Event('change'));};p.append(button);$('enhance-history').append(p);
  }
  if(!$('enhance-history').childNodes.length)$('enhance-history').textContent='No imports or local enhancements saved in this case.';
 }
 async function openSelected(force=false){
  activated=true;await ready;records();const v=selected();if(!v||!permitted()||loading)return;
  if(doc?.caseId===activeCase.id&&doc.parentId===v.id&&!force){showPreview();availability();return;}
  if(loadingImage)return;
  if(isDirty()&&!force){status('Unsaved adjustments remain pinned to their source. Save or use Load selected image to discard.');return;}
  const own=++token,caseId=activeCase.id;loadingImage=true;status('Loading source pixels…');availability();
  try{
   const data=await api('/api/cases/'+caseId+'/versions/'+v.id+'/enhance');
   const response=await fetch(data.source_url,{cache:'no-store'});if(!response.ok){const err=await response.json();throw Error(err.detail||'Source image unavailable');}
   const blob=await response.blob(),bitmap=await createImageBitmap(blob);
   if(own!==token||activeCase?.id!==caseId||selected()?.id!==v.id){bitmap.close();return;}
   const c=document.createElement('canvas');c.width=bitmap.width;c.height=bitmap.height;c.getContext('2d').drawImage(bitmap,0,0);bitmap.close();
   const image=c.getContext('2d').getImageData(0,0,c.width,c.height);
   const visible=$('enhance-canvas');visible.width=c.width;visible.height=c.height;visible.getContext('2d').drawImage(c,0,0);
   if(sourceURL)URL.revokeObjectURL(sourceURL);sourceURL=URL.createObjectURL(blob);doc={caseId,parentId:v.id,sourceId:data.source_id};params=data.adjustments;savedParams=structuredClone(params);undo=[];redo=[];pendingSave=null;zoom=1;$('enhance-zoom-value').textContent='100%';
   resultBlob=null;if(resultURL)URL.revokeObjectURL(resultURL);resultURL=null;loadingImage=false;
   $('enhance-parent').textContent='Editing '+label(v)+' · non-destructive source '+data.source_id.slice(0,8);controls();makeWorker(image,c.width,c.height);schedule();
  }catch(e){status('Source load failed: '+e.message+' Use Load selected image to retry.',true);doc=null;}
  finally{if(own===token){loadingImage=false;availability();}}
 }
 function deactivate(){activated=false;$('result').style.transform='';if(activeCase&&selected())showImage(selected(),activeCase.id).catch(()=>{});}
 function caseChanged(){++token;clearTimeout(timer);if(worker)worker.terminate();worker=null;doc=null;params=null;savedParams=null;undo=[];redo=[];pendingSave=null;pendingImport=null;loadingImage=false;processing=false;inFlight=false;resultBlob=null;if(resultURL)URL.revokeObjectURL(resultURL);if(sourceURL)URL.revokeObjectURL(sourceURL);resultURL=sourceURL=null;$('enhance-canvas').width=0;$('enhance-canvas').height=0;$('enhance-file').value='';$('enhance-consent').checked=false;$('enhance-ai-text').value='';$('enhance-ai-style').value=activeCase?.draft.style||'forensic';$('enhance-preset').value='';$('enhance-preset-values').textContent='Presets apply documented local settings and can be undone.';status('Select a saved image or import a permitted source for this case.');$('enhance-import-status').textContent='';$('enhance-parent').textContent='Select a case image or import a source.';records();availability();}
 function selectionChanged(){records();if(approvedSelection&&approvedSelection===selected()?.id){doc=null;approvedSelection=null;}if(isActive())openSelected();availability();}
 function allowSelection(id){if(!doc||doc.parentId===id||!isDirty())return true;const yes=confirm('Discard unsaved enhancement adjustments and switch images?');if(yes)approvedSelection=id;return yes;}
 async function chooseSource(){const id=$('enhance-source-select').value;if(id&&id!==selected()?.id){$('active-version').value=id;$('active-version').dispatchEvent(new Event('change'));}else{if(isDirty()&&!confirm('Discard current adjustments and reload the selected saved image?'))return;await openSelected(true);}}
 $('enhance-load').onclick=chooseSource;
 $('enhance-consent').onchange=availability;$('enhance-file').onchange=()=>{pendingImport=null;$('enhance-import-status').textContent='File selected; Import source image validates and saves it to this case.';availability();};
 const asDataURL=blob=>new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('Unable to read image bytes'));reader.readAsDataURL(blob);});
 async function refreshRecord(caseId){const r=await api('/api/cases/'+caseId);if(activeCase?.id!==caseId)return null;for(const key of ['versions','events','jobs','selected_version_id','preferred_version_id','refinements'])activeCase[key]=r[key];renderRecords();records();return r;}
 $('enhance-import').onclick=async()=>{
  const file=$('enhance-file').files?.[0];if(importing||!file||!permitted()||!$('enhance-consent').checked)return;
  if(file.size>12*1024*1024){$('enhance-import-status').textContent='File exceeds 12 MiB.';return;}
  if(!['image/png','image/jpeg','image/webp'].includes(file.type)){$('enhance-import-status').textContent='Select a PNG, JPEG or WebP.';return;}
  if(isDirty()&&!confirm('Import a new source and discard the unsaved enhancement draft?'))return;
  importing=true;availability();const caseId=activeCase.id;
  try{
   if(!pendingImport)pendingImport={request_key:crypto.randomUUID().replaceAll('-',''),image:await asDataURL(file),filename:file.name,consent:true};
   const result=await api('/api/cases/'+caseId+'/imports','POST',pendingImport);if(activeCase?.id!==caseId)return;
   pendingImport=null;doc=null;await refreshRecord(caseId);await showImage(selected(),caseId);$('enhance-import-status').textContent='Imported source saved · '+result.version_id.slice(0,8)+' · original bytes retained.';await openSelected();
  }catch(e){$('enhance-import-status').textContent='Import failed: '+e.message+' Retry Import source image.';}
  finally{importing=false;availability();}
 };
 $('enhance-save').onclick=async()=>{
  if(saving||!hasPreview()||!isDirty())return;const caseId=doc.caseId;saving=true;availability();status('Saving committed preview and parameters…');
  try{
   if(!pendingSave)pendingSave={parent_id:doc.parentId,source_id:doc.sourceId,request_key:crypto.randomUUID().replaceAll('-',''),png:await asDataURL(resultBlob),adjustments:structuredClone(params),engine:schema.engine};
   const result=await api('/api/cases/'+caseId+'/enhancements','POST',pendingSave);if(activeCase?.id!==caseId)return;
   doc.parentId=result.version_id;savedParams=structuredClone(params);pendingSave=null;await refreshRecord(caseId);await showImage(selected(),caseId);showPreview();$('enhance-parent').textContent='Saved '+label(activeCase.versions.find(v=>v.id===result.version_id))+' · non-destructive source '+doc.sourceId.slice(0,8);status('Saved Enhanced Version · '+result.version_id.slice(0,8)+' · SHA-256 '+result.sha256.slice(0,12)+'…');
  }catch(e){status('Save failed: '+e.message+' Committed preview retained; retry Save Enhanced Version.',true);}
  finally{saving=false;availability();}
 };
 function compare(){if(!hasPreview())return;const neutral=JSON.stringify(params)===JSON.stringify(schema.defaults);const base=activeCase.versions.find(v=>v.id===doc.sourceId);Refinement.preview({id:'source-'+doc.sourceId,image_url:sourceURL,display_label:'INPUT · '+label(base),workspace:base?.workspace,sha256:base?.sha256},{id:'enhancement-draft',image_url:resultURL,display_label:neutral?'RESULT · Neutral settings (same source pixels)':isDirty()?'UNSAVED · Local enhancement':'RESULT · Saved enhancement parameters',workspace:'enhance'});}
 function full(){if(hasPreview())Refinement.viewFull({image_url:resultURL,display_label:'Local enhancement preview · '+$('enhance-canvas').width+' × '+$('enhance-canvas').height,workspace:'enhance'});}
 $('enhance-compare').onclick=compare;$('enhance-full').onclick=full;
 function updateZoom(factor){zoom=Math.max(.25,Math.min(3,zoom*factor));$('enhance-zoom-value').textContent=Math.round(zoom*100)+'%';showPreview();}
 $('enhance-zoom-in').onclick=()=>updateZoom(1.25);$('enhance-zoom-out').onclick=()=>updateZoom(.8);$('enhance-fit').onclick=()=>{zoom=1;$('enhance-zoom-value').textContent='100%';showPreview();};
 $('enhance-reset').onclick=()=>setParams(schema.defaults);
 $('enhance-undo').onclick=()=>{if(!undo.length)return;redo.push(structuredClone(params));const previous=undo.pop();setParams(previous,false);};
 $('enhance-redo').onclick=()=>{if(!redo.length)return;undo.push(structuredClone(params));setParams(redo.pop(),false);};
 $('enhance-apply-preset').onclick=()=>{const preset=schema.presets[$('enhance-preset').value];if(!preset){status('Choose an adjustment preset.');return;}$('enhance-preset-values').textContent=preset.label+': '+JSON.stringify(preset.values);setParams(preset.values);};
 for(const key of ['grayscale','invert','resize'])$('enhance-'+key).oninput=()=>{if(params)setParams({...params,[key]:key==='resize'?Number($('enhance-'+key).value):$('enhance-'+key).checked});};
 $('enhance-filters').onclick=()=>{$('enhance-transform-panel').hidden=true;$('enhance-controls').hidden=false;$('enhance-transform').setAttribute('aria-expanded','false');$('enhance-filters').setAttribute('aria-pressed','true');};
 $('enhance-transform').onclick=()=>{$('enhance-transform-panel').hidden=!$('enhance-transform-panel').hidden;$('enhance-transform').setAttribute('aria-expanded',String(!$('enhance-transform-panel').hidden));};
 function sketch(){if(isDirty()){status('Save Enhanced Version before moving its adjusted pixels into Sketch.',true);return;}selectTab('sketch',true);}
 $('enhance-draw').onclick=sketch;$('enhance-sketch').onclick=sketch;$('enhance-lab').onclick=()=>selectTab('lab',true);
 $('enhance-ai').onclick=()=>{
  if(!doc||busy)return;if(isDirty()){status('Save the local enhancement before requesting a separate AI interpretation.',true);return;}if(doc.parentId!==selected()?.id){status('Select this saved enhancement before AI interpretation.',true);return;}
  const text=$('enhance-ai-text').value;if(!text.trim()){status('Enter explicit textual AI interpretation instructions.',true);return;}
  const style=$('enhance-ai-style').value;for(const input of document.querySelectorAll('[name=style]'))input.checked=input.value===style;if(labReady)CharacterLab.syncPresentation('style',style);setDirty();
  $('refinement-input').value=text;$('refinement-input').dispatchEvent(new Event('input',{bubbles:true}));$('open-refinement').click();$('refinement-status').textContent='Separate text-only AI generation. Uploaded or enhanced pixels are not sent; missing facial details may be invented.';
 };
 const ready=api('/api/enhance-schema').then(data=>{
  schema=data;for(const group of ['tonal','detail','color']){const section=document.createElement('section');const title=document.createElement('h2');title.textContent=group.toUpperCase();section.append(title);
   for(const c of data.controls.filter(c=>c.group===group)){const label=document.createElement('label');label.htmlFor='enhance-'+c.key;label.textContent=c.label;const output=document.createElement('output');output.id='enhance-'+c.key+'-value';output.textContent=data.defaults[c.key];const input=document.createElement('input');input.id='enhance-'+c.key;input.type='range';input.min=c.min;input.max=c.max;input.step=c.step;input.value=data.defaults[c.key];input.oninput=()=>{if(params)setParams({...params,[c.key]:Number(input.value)});};label.append(output);section.append(label,input);}$('enhance-controls').append(section);}
  for(const [id,preset] of Object.entries(data.presets))$('enhance-preset').append(new Option(preset.label,id));availability();return data;
 }).catch(e=>{status('Enhancement controls unavailable: '+e.message,true);});
 return {openSelected,selectionChanged,availability,caseChanged,deactivate,isDirty,isActive,hasPreview,allowSelection,compare,full,records};
})();
