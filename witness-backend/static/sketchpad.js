'use strict';
window.Sketchpad=(()=>{
 const tools=[['pencil','✎','Pencil'],['brush','◕','Brush'],['eraser','▱','Eraser'],['line','╱','Line'],['rectangle','□','Rectangle'],['ellipse','○','Ellipse'],['arrow','↗','Arrow'],['text','T','Text'],['crop','⌗','Crop'],['pan','✥','Pan']];
 const canvas=$('sketch-canvas'),view=$('sketch-viewport');
 const makeCanvas=(w,h)=>{const c=document.createElement('canvas');c.width=w;c.height=h;return c;};
 let doc=null,base=null,overlay=null,sourceImage=null,ops=[],cursor=0,openedOps=[],savedSignature='',tool='pencil',scale=1,panX=0,panY=0,fitScale=1,gesture=null,crop=null,loadingSketch=false,saving=false,loadToken=0,pendingSave=null,viewFitted=true,approvedSelection=null;
 const selected=()=>activeCase?.versions.find(v=>v.id===activeCase.selected_version_id)||activeCase?.versions.at(-1);
 const signature=()=>JSON.stringify(ops.slice(0,cursor));
 const isDirty=()=>!!doc&&signature()!==savedSignature;
 const status=(text,error=false)=>{$('sketch-status').textContent=text;$('sketch-status').classList.toggle('error',error);};
 function availability(){
  const ready=!!doc&&!!base&&doc.caseId===activeCase?.id&&permitted()&&!loading&&!loadingSketch;
  $('sketch-save').disabled=!ready||saving||!!gesture||!isDirty();$('sketch-save').textContent=saving?'Saving edited version…':'Save Edited Version';
  $('sketch-refine').disabled=!ready||saving||busy;
  $('sketch-undo').disabled=!ready||saving||cursor===0;$('sketch-redo').disabled=!ready||saving||cursor===ops.length;
  $('sketch-crop-apply').disabled=!ready||!crop||saving;$('sketch-crop-cancel').disabled=!crop||saving;
  $('sketch-content').setAttribute('aria-busy',String(saving));
  $('sketch-content').hidden=!ready;$('sketch-empty').hidden=ready;
  if(!ready)$('sketch-empty').textContent=loadingSketch?'Loading the selected image and editable layers…':'Select a saved case image to begin. A frozen original account is required in witness cases.';
 }
 for(const [id,icon,name] of tools){const b=document.createElement('button');b.type='button';b.dataset.tool=id;b.title=name;b.setAttribute('aria-label',name+' tool');b.setAttribute('aria-pressed',String(id===tool));const iconNames={pencil:'pencil',brush:'brush',eraser:'eraser',line:'slash-lg',rectangle:'square',ellipse:'circle',arrow:'arrow-up-right',text:'fonts',crop:'crop',pan:'arrows-move'};const image=document.createElement('img');image.src='/static/icons/'+iconNames[id]+'.svg';image.alt='';image.width=16;image.height=16;b.append(image,document.createTextNode(name));b.onclick=()=>{if(saving)return;cancelGesture();tool=id;crop=null;for(const other of $('sketch-tools').children)other.setAttribute('aria-pressed',String(other===b));canvas.style.cursor=id==='pan'?'grab':'crosshair';status(name+(id==='crop'?' · drag a rectangle, then Apply crop.':id==='text'?' · type an artist note below, then click the image.':' tool selected.'));paint();availability();};$('sketch-tools').append(b);}
 for(const color of ['#111111','#777777','#ffffff','#d84e59','#173dcc','#2f9e73','#e4a849']){const b=document.createElement('button');b.type='button';b.style.background=color;b.setAttribute('aria-label','Use color '+color);b.title=color;b.onclick=()=>$('sketch-color').value=color;$('sketch-swatches').append(b);}
 $('sketch-width').oninput=()=>$('sketch-width-value').textContent=$('sketch-width').value+' px';$('sketch-opacity').oninput=()=>$('sketch-opacity-value').textContent=$('sketch-opacity').value+'%';
 function resize(){
  if(!view.clientWidth||!view.clientHeight)return;
  const ratio=window.devicePixelRatio||1;canvas.width=Math.round(view.clientWidth*ratio);canvas.height=Math.round(view.clientHeight*ratio);
  if(base&&viewFitted)fit();else paint();
 }
 new ResizeObserver(resize).observe(view);
 function fit(){if(!base)return;fitScale=Math.min((view.clientWidth-20)/base.width,(view.clientHeight-26)/base.height);scale=fitScale;panX=(view.clientWidth-base.width*scale)/2;panY=(view.clientHeight-base.height*scale)/2;viewFitted=true;paint();}
 function zoom(factor,x=view.clientWidth/2,y=view.clientHeight/2){if(!base||saving)return;const next=Math.max(fitScale*.25,Math.min(8,scale*factor));panX=x-(x-panX)*next/scale;panY=y-(y-panY)*next/scale;scale=next;viewFitted=false;paint();}
 function position(event){const rect=canvas.getBoundingClientRect();return {x:(event.clientX-rect.left-panX)/scale,y:(event.clientY-rect.top-panY)/scale};}
 const clampPoint=p=>[Math.max(0,Math.min(base.width,p.x)),Math.max(0,Math.min(base.height,p.y))];
 function pressure(event){return event.pointerType==='pen'?Math.max(.05,Math.min(1,event.pressure||.5)):1;}
 function drawing(ctx,op){
  if(op.tool==='clear'){ctx.clearRect(0,0,ctx.canvas.width,ctx.canvas.height);return;}
  const p=op.points;if(!p?.length)return;
  ctx.save();ctx.strokeStyle=op.color;ctx.fillStyle=op.color;ctx.lineWidth=op.width;ctx.lineCap='round';ctx.lineJoin='round';ctx.globalAlpha=op.opacity;
  if(op.tool==='eraser')ctx.globalCompositeOperation='destination-out';
  const start=p[0],end=p.at(-1);
  if(['pencil','brush','eraser'].includes(op.tool)){
   if(p.length===1||p.every(point=>point[0]===start[0]&&point[1]===start[1])){ctx.beginPath();ctx.arc(start[0],start[1],op.width/2,0,Math.PI*2);ctx.fill();}
   for(let i=1;i<p.length;i++){ctx.lineWidth=op.tool==='brush'?op.width*(.25+.75*p[i][2]):op.width;ctx.beginPath();ctx.moveTo(p[i-1][0],p[i-1][1]);ctx.lineTo(p[i][0],p[i][1]);ctx.stroke();}
  }else if(op.tool==='text'){ctx.font=(12+op.width*4)+'px ui-sans-serif, system-ui, sans-serif';ctx.textBaseline='top';ctx.fillText(op.text,start[0],start[1]);}
  else{
   ctx.beginPath();const x=Math.min(start[0],end[0]),y=Math.min(start[1],end[1]),w=Math.abs(end[0]-start[0]),h=Math.abs(end[1]-start[1]);
   if(op.tool==='rectangle')ctx.rect(x,y,w,h);
   else if(op.tool==='ellipse')ctx.ellipse(x+w/2,y+h/2,w/2,h/2,0,0,Math.PI*2);
   else{ctx.moveTo(start[0],start[1]);ctx.lineTo(end[0],end[1]);if(op.tool==='arrow'){const angle=Math.atan2(end[1]-start[1],end[0]-start[0]),n=Math.max(12,op.width*4);ctx.moveTo(end[0]-n*Math.cos(angle-Math.PI/6),end[1]-n*Math.sin(angle-Math.PI/6));ctx.lineTo(end[0],end[1]);ctx.lineTo(end[0]-n*Math.cos(angle+Math.PI/6),end[1]-n*Math.sin(angle+Math.PI/6));}}
   ctx.stroke();
  }
  ctx.restore();
 }
 function transform(layer,op){
  const old=layer,w=old.width,h=old.height;let output;
  if(op.tool==='crop'){const [x,y,cw,ch]=op.rect;output=makeCanvas(cw,ch);output.getContext('2d').drawImage(old,x,y,cw,ch,0,0,cw,ch);}
  else if(op.tool==='rotate'){output=makeCanvas(h,w);const c=output.getContext('2d');c.translate(h,0);c.rotate(Math.PI/2);c.drawImage(old,0,0);}
  else{output=makeCanvas(w,h);const c=output.getContext('2d');c.translate(w,0);c.scale(-1,1);c.drawImage(old,0,0);}
  return output;
 }
 function replay(){
  if(!sourceImage)return;
  base=makeCanvas(sourceImage.naturalWidth,sourceImage.naturalHeight);base.getContext('2d').drawImage(sourceImage,0,0);overlay=makeCanvas(base.width,base.height);
  for(const op of ops.slice(0,cursor)){
   if(['crop','rotate','flip'].includes(op.tool)){base=transform(base,op);overlay=transform(overlay,op);}
   else drawing(overlay.getContext('2d'),op);
  }
 }
 function paint(){
  const c=canvas.getContext('2d'),ratio=window.devicePixelRatio||1;c.setTransform(1,0,0,1,0,0);c.clearRect(0,0,canvas.width,canvas.height);
  if(!base)return;
  c.setTransform(ratio*scale,0,0,ratio*scale,ratio*panX,ratio*panY);c.drawImage(base,0,0);
  if(gesture?.operation){const preview=makeCanvas(overlay.width,overlay.height);preview.getContext('2d').drawImage(overlay,0,0);drawing(preview.getContext('2d'),gesture.operation);c.drawImage(preview,0,0);}else c.drawImage(overlay,0,0);
  if(crop){c.fillStyle='#4085f02b';c.fillRect(...crop);c.strokeStyle='#70aeff';c.lineWidth=2/scale;c.setLineDash([6/scale,4/scale]);c.strokeRect(...crop);c.setLineDash([]);}
  $('sketch-zoom-value').textContent=Math.round(scale*100)+'%';
 }
 function commit(operation){
  if(saving)return;
  if(cursor>=2000||ops.slice(0,cursor).reduce((count,op)=>count+(op.points?.length||0),0)+(operation.points?.length||0)>100000){paint();status('Project limit reached. Undo an operation before adding more edits.',true);return;}
  const resized=['crop','rotate'].includes(operation.tool);ops=ops.slice(0,cursor);ops.push(operation);cursor=ops.length;pendingSave=null;crop=null;replay();if(resized)fit();else paint();
  status(cursor+' artist operations · '+base.width+' × '+base.height+' · '+(isDirty()?'Unsaved changes':'Opened version'));$('sketch-save-status').textContent=isDirty()?'Unsaved local edits · Save Edited Version creates a new revision.':'Opened version; original image preserved.';availability();
 }
 function cancelGesture(){if(gesture){try{canvas.releasePointerCapture(gesture.id);}catch{}gesture=null;}paint();}
 canvas.onpointerdown=event=>{
  if(!doc||!base||loadingSketch||saving||event.button>0)return;
  if(gesture){cancelGesture();return;}
  const at=position(event);if(tool!=='pan'&&(at.x<0||at.y<0||at.x>base.width||at.y>base.height))return;
  event.preventDefault();canvas.setPointerCapture(event.pointerId);const point=clampPoint(at);
  if(tool==='text'){
   if(!$('sketch-text').value.trim()){status('Enter annotation text before placing it.',true);return;}
   commit({tool:'text',points:[[...point,pressure(event)]],color:$('sketch-color').value,width:Number($('sketch-width').value),opacity:Number($('sketch-opacity').value)/100,text:$('sketch-text').value});return;
  }
  gesture={id:event.pointerId,start:point,lastX:event.clientX,lastY:event.clientY,tool};
  if(!['pan','crop'].includes(tool))gesture.operation={tool,points:[[...point,pressure(event)]],color:$('sketch-color').value,width:Number($('sketch-width').value),opacity:Number($('sketch-opacity').value)/100};
  if(tool==='crop')crop=null;availability();paint();
 };
 canvas.onpointermove=event=>{
  if(!gesture||gesture.id!==event.pointerId)return;event.preventDefault();
  if(gesture.tool==='pan'){panX+=event.clientX-gesture.lastX;panY+=event.clientY-gesture.lastY;gesture.lastX=event.clientX;gesture.lastY=event.clientY;viewFitted=false;paint();return;}
  const point=clampPoint(position(event));
  if(gesture.tool==='crop'){const x=Math.floor(Math.min(gesture.start[0],point[0])),y=Math.floor(Math.min(gesture.start[1],point[1]));crop=[x,y,Math.floor(Math.max(gesture.start[0],point[0]))-x,Math.floor(Math.max(gesture.start[1],point[1]))-y];}
  else if(['pencil','brush','eraser'].includes(gesture.tool)){if(gesture.operation.points.length<20000)gesture.operation.points.push([...point,pressure(event)]);else status('Stroke limit reached. Release and begin a new stroke.',true);}
  else gesture.operation.points=[gesture.operation.points[0],[...point,pressure(event)]];
  paint();
 };
 canvas.onpointerup=event=>{
  if(!gesture||gesture.id!==event.pointerId)return;canvas.onpointermove(event);const finished=gesture;gesture=null;try{canvas.releasePointerCapture(event.pointerId);}catch{}
  if(finished.operation){if(finished.operation.points.length===1&&['line','rectangle','ellipse','arrow'].includes(finished.tool))finished.operation.points.push(finished.operation.points[0]);commit(finished.operation);}
  else{if(finished.tool==='crop')status(crop?('Crop '+crop[2]+' × '+crop[3]+' pixels. Apply to commit or Cancel.'): 'Drag a crop rectangle.');paint();availability();}
 };
 canvas.onpointercancel=()=>{cancelGesture();crop=null;paint();availability();};canvas.onlostpointercapture=()=>{if(gesture){gesture=null;paint();availability();}};
 canvas.addEventListener('wheel',event=>{if(event.ctrlKey&&base){event.preventDefault();const rect=canvas.getBoundingClientRect();zoom(event.deltaY<0?1.1:1/1.1,event.clientX-rect.left,event.clientY-rect.top);}}, {passive:false});
 $('sketch-zoom-in').onclick=()=>zoom(1.25);$('sketch-zoom-out').onclick=()=>zoom(.8);$('sketch-fit').onclick=()=>{cancelGesture();fit();};
 function history(delta){if(saving||!base)return;cancelGesture();cursor=Math.max(0,Math.min(ops.length,cursor+delta));crop=null;pendingSave=null;replay();fit();status('Undo/redo · '+cursor+' / '+ops.length+' artist operations.');$('sketch-save-status').textContent=isDirty()?'Unsaved local edits':'Opened saved state';availability();}
 $('sketch-undo').onclick=()=>history(-1);$('sketch-redo').onclick=()=>history(1);
 canvas.onkeydown=event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='z'){event.preventDefault();history(event.shiftKey?1:-1);}if(event.key==='Escape'){cancelGesture();crop=null;paint();availability();}};
 $('sketch-crop-apply').onclick=()=>{if(!crop||crop[2]<32||crop[3]<32){status('Crop must be at least 32 × 32 image pixels.',true);return;}commit({tool:'crop',rect:crop});};
 $('sketch-crop-cancel').onclick=()=>{crop=null;paint();availability();status('Crop cancelled.');};
 $('sketch-rotate').onclick=()=>{if(base)commit({tool:'rotate'});};$('sketch-flip').onclick=()=>{if(base)commit({tool:'flip'});};
 $('sketch-clear').onclick=()=>{if(base&&confirm('Clear the annotation layer? The base image stays unchanged. You can undo this action.'))commit({tool:'clear'});};
 $('sketch-reset').onclick=()=>{if(!doc||saving)return;if(isDirty()&&!confirm('Reset to the version opened in Sketch? Unsaved edits will be discarded.'))return;cancelGesture();ops=structuredClone(openedOps);cursor=ops.length;crop=null;pendingSave=null;replay();fit();status('Reset to the opened version.');availability();};
 $('sketch-lab').onclick=()=>selectTab('lab',true);
 async function loadSelected(force=false){
  const version=selected();if(!version||!permitted()||loading)return;
  if(doc?.caseId===activeCase.id&&doc.parentId===version.id&&!force){resize();return;}
  if(isDirty()&&!force){status('Unsaved draft is pinned to its opened image. Save it or use Load selected to discard and switch.');return;}
  const token=++loadToken,caseId=activeCase.id;loadingSketch=true;availability();
  try{
   const data=await api('/api/cases/'+caseId+'/versions/'+version.id+'/sketch'),image=new Image();image.src=data.source_url;await image.decode();
   if(token!==loadToken||activeCase?.id!==caseId||selected()?.id!==version.id)return;
   if(image.naturalWidth*image.naturalHeight>16000000)throw Error('Canvas supports up to 16 megapixels.');
   doc={caseId,parentId:version.id,sourceId:data.project.source_version_id};sourceImage=image;ops=data.project.operations;cursor=ops.length;openedOps=structuredClone(ops);savedSignature=signature();crop=null;gesture=null;pendingSave=null;replay();
   $('sketch-parent').textContent='Editing V'+(activeCase.versions.indexOf(version)+1)+' · '+version.id.slice(0,8)+' · '+(data.modified_illustration?'Artist edit · editable layers restored':version.workspace==='upload'?'Uploaded source · protected original bytes':version.workspace==='enhance'?'Locally adjusted image · protected base':'Original generated image · protected base');
   $('sketch-save-status').textContent='Opened '+base.width+' × '+base.height+' · Original image bytes remain unchanged.';status('Choose a drawing tool. Pan moves the view; eraser affects annotations only.');
   loadingSketch=false;availability();requestAnimationFrame(()=>{resize();fit();});
  }catch(error){if(token===loadToken){doc=null;base=null;overlay=null;status(error.message,true);$('sketch-save-status').textContent='Unable to load sketch: '+error.message;}}
  finally{if(token===loadToken){loadingSketch=false;availability();}}
 }
 $('sketch-load-selected').onclick=()=>{if(isDirty()&&!confirm('Discard unsaved sketch edits and load the selected image?'))return;loadSelected(true);};
 function selectionChanged(){if(approvedSelection&&approvedSelection===selected()?.id){caseChanged();approvedSelection=null;}if(doc?.caseId!==activeCase?.id){caseChanged();}if(!$('panel-sketch').hidden&&$('generator').hidden===false)loadSelected();availability();}
 function caseChanged(){++loadToken;doc=null;sourceImage=null;base=null;overlay=null;ops=[];cursor=0;openedOps=[];crop=null;gesture=null;savedSignature='';pendingSave=null;loadingSketch=false;paint();$('sketch-instruction').value='';$('sketch-parent').textContent='Select a saved image to begin.';availability();}
 function allowSelection(id){if(!doc||doc.parentId===id||!isDirty())return true;const approved=confirm('Switch images and discard this unsaved sketch draft? Save Edited Version first to keep it.');if(approved)approvedSelection=id;return approved;}
 $('sketch-save').onclick=async()=>{
  if(saving||!doc||!isDirty()||gesture)return;
  const caseId=doc.caseId;cancelGesture();saving=true;availability();$('sketch-save-status').textContent='Saving local PNG and editable layers…';
  try{
   if(!pendingSave){const flat=makeCanvas(base.width,base.height);flat.getContext('2d').drawImage(base,0,0);flat.getContext('2d').drawImage(overlay,0,0);pendingSave={parent_id:doc.parentId,request_key:crypto.randomUUID().replaceAll('-',''),png:flat.toDataURL('image/png'),project:{schema_version:1,source_version_id:doc.sourceId,operations:structuredClone(ops.slice(0,cursor))}};}
   const result=await api('/api/cases/'+caseId+'/local-edits','POST',pendingSave);
   if(activeCase?.id!==caseId)return;
   const record=await api('/api/cases/'+caseId);if(activeCase?.id!==caseId)return;
   activeCase.versions=record.versions;activeCase.selected_version_id=record.selected_version_id;activeCase.preferred_version_id=record.preferred_version_id;activeCase.events=record.events;activeCase.jobs=record.jobs;
   doc.parentId=result.version_id;openedOps=structuredClone(ops.slice(0,cursor));savedSignature=signature();pendingSave=null;
   renderRecords();await showImage(selected(),caseId);
   $('sketch-parent').textContent='Editing V'+(record.versions.findIndex(v=>v.id===result.version_id)+1)+' · '+result.version_id.slice(0,8)+' · Modified illustration · artist edit';
   $('sketch-save-status').textContent='Saved edited version · '+result.version_id.slice(0,8)+' · SHA-256 '+result.sha256.slice(0,12)+'…';status('Local edited illustration saved. All earlier versions and the original remain available.');
  }catch(error){$('sketch-save-status').textContent='Save failed: '+error.message+' Draft retained; retry Save Edited Version.';status('Save failed. Your canvas and undo history are retained.',true);}
  finally{saving=false;availability();}
 };
 $('sketch-refine').onclick=()=>{
  if(!doc||busy||saving)return;
  if(isDirty()){status('Save Edited Version before requesting AI refinement, so local annotations remain in history.',true);return;}
  if(selected()?.id!==doc.parentId){status('Select this sketch’s saved version in Reconstruction Output before refining it.',true);return;}
  const text=$('sketch-instruction').value;if(!text.trim()){status('Enter explicit textual refinement instructions.',true);return;}
  $('refinement-input').value=text;$('refinement-input').dispatchEvent(new Event('input',{bubbles:true}));$('open-refinement').click();$('refinement-status').textContent='Text-only regeneration. Sketch pixels and artist annotations are not sent to Codex. Review the final prompt, then Regenerate.';
 };
 return {openSelected:loadSelected,selectionChanged,caseChanged,availability,isDirty,allowSelection};
})();
