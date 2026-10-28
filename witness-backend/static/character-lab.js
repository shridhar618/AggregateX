'use strict';
const CharacterLab=(()=>{
  let groups=[],fields={},lab={},baseline=null,callbacks={},active='face',undo=[],enabled=false,currentCase=null,referenceURL=null;
  const el=id=>document.getElementById(id);
  const empty=()=>({value:null,confidence:'unknown',source:'operator',quote:''});
  const clone=value=>JSON.parse(JSON.stringify(value));
  const node=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
  const read=key=>fields[key].shared?callbacks.getShared(key):(lab[key]||empty());
  function write(key,value){if(fields[key].shared)callbacks.setShared(key,value);else lab[key]=value;}
  function snapshot(){return {style:callbacks.style(),view:callbacks.view(),lab:clone(lab),shared:Object.fromEntries(Object.keys(fields).filter(k=>fields[k].shared).map(k=>[k,clone(read(k))]))};}
  function remember(){undo.push(snapshot());if(undo.length>30)undo.shift();}
  function invalidate(){el('prompt-budget').textContent='Draft changed; review the prompt again.';el('prompt-text').textContent='';}
  function changed(){invalidate();callbacks.change();refresh();}
  function translate(field,value){
    if(value===null)return 'Unknown / not provided';
    if(field.kind!=='slider')return value;
    const n=Number(value);return n>=41&&n<=59?'Neutral relative setting':((n<=20||n>=80?'Markedly ':'Slightly ')+(n<50?field.low:field.high));
  }
  function refreshField(key){
    const f=fields[key],a=read(key),input=el('lab-'+key);
    if(document.activeElement!==input)input.value=a.value??(f.kind==='slider'?'50':f.kind==='age'?'35':'');
    const unknown=el('lab-'+key+'-unknown');if(unknown)unknown.checked=a.value===null;
    el('lab-'+key+'-value').textContent=f.kind==='slider'?(a.value===null?'Unknown · 50 neutral':a.value+' / 100'):a.value===null?'Unknown':'';
    el('lab-'+key+'-meaning').textContent=translate(f,a.value);
    const confidence=el('lab-'+key+'-confidence');confidence.value=a.confidence;confidence.disabled=a.value===null;
    confidence.options[0].disabled=a.value!==null;
    const source=el('lab-'+key+'-source');source.value=a.source;source.disabled=a.value===null;
    const quote=el('lab-'+key+'-quote');if(document.activeElement!==quote)quote.value=a.quote;quote.hidden=a.source!=='witness';
    el('lab-'+key+'-provenance').textContent=(a.source==='witness'?'Witness quote':'Operator input')+' · '+a.confidence;
  }
  function refresh(){
    for(const key of Object.keys(fields))refreshField(key);
    let pending=0;
    for(const [key,f] of Object.entries(fields)){
      const previous=(f.shared?baseline?.attributes:baseline?.lab)?.[key]||empty();
      if(JSON.stringify(read(key))!==JSON.stringify(previous))pending++;
    }
    if(baseline&&callbacks.style()!==baseline.style)pending++;
    if(baseline&&callbacks.view()!==baseline.view)pending++;
    el('lab-pending').textContent=enabled?pending+' changes not yet generated':'Freeze first account to unlock Character Lab.';
    el('undo-lab').disabled=!enabled||undo.length===0;
  }
  function groupTab(id,focus=false){
    active=id;
    for(const group of groups){const selected=group.id===id;const tab=el('lab-tab-'+group.id);tab.setAttribute('aria-selected',String(selected));tab.tabIndex=selected?0:-1;el('lab-group-'+group.id).hidden=!selected;if(selected&&focus)tab.focus();}
    document.querySelector('.lab-scroll').scrollTop=0;
  }
  function buildField(f){
    fields[f.key]=f;
    const box=node('section','lab-field');box.dataset.field=f.key;
    const heading=node('div','lab-field-heading');const label=node('label','',f.label);label.htmlFor='lab-'+f.key;
    const value=node('output');value.id='lab-'+f.key+'-value';value.setAttribute('for','lab-'+f.key);heading.append(label,value);box.append(heading);
    let input;
    if(f.kind==='select'){
      input=node('select');for(const option of ['',...f.options]){const item=node('option','',option||'Unknown / not provided');item.value=option;input.append(item);}
    }else{input=node('input');input.type=f.kind==='slider'?'range':f.kind==='age'?'number':'text';
      if(f.kind==='slider'){input.min=0;input.max=100;input.step=1;}else if(f.kind==='age'){input.min=18;input.max=100;input.step=1;}else {input.maxLength=100;input.placeholder='Unknown / not provided';}
    }
    input.id='lab-'+f.key;input.setAttribute('aria-describedby','lab-'+f.key+'-meaning');box.append(input);
    input.addEventListener('input',()=>{
      remember();const value=input.value.trim()?input.value:null;
      write(f.key,{value,confidence:value===null?'unknown':'tentative',source:'operator',quote:''});changed();
    });
    const row=node('div','lab-field-foot');const meaning=node('span');meaning.id='lab-'+f.key+'-meaning';row.append(meaning);
    if(f.kind==='slider'||f.kind==='age'){
      const label=node('label','unknown');const unknown=node('input');unknown.type='checkbox';unknown.id='lab-'+f.key+'-unknown';unknown.setAttribute('aria-label',f.label+' Unknown');label.append(unknown,' Unknown');row.append(label);
      unknown.addEventListener('change',()=>{remember();write(f.key,unknown.checked?empty():{value:input.value||'50',confidence:'tentative',source:'operator',quote:''});changed();});
    }
    if(f.kind==='slider'){
      const reset=node('button','lab-neutral','Neutral');reset.type='button';reset.title='Set an explicit neutral operator direction (50)';reset.addEventListener('click',()=>{remember();write(f.key,{value:'50',confidence:'tentative',source:'operator',quote:''});changed();});row.append(reset);
    }
    box.append(row);
    const details=node('details','lab-provenance');const summary=node('summary');summary.id='lab-'+f.key+'-provenance';details.append(summary);
    for(const [name,options] of [['confidence',['unknown','tentative','certain']],['source',['operator','witness']]]){
      const label=node('label','',name==='source'?'Source':'Subjective recollection');const select=node('select');select.id='lab-'+f.key+'-'+name;
      for(const option of options){const item=node('option','',option);item.value=option;select.append(item);}
      label.append(select);details.append(label);select.addEventListener('change',()=>{remember();write(f.key,{...read(f.key),[name]:select.value});changed();});
    }
    const quote=node('input');quote.id='lab-'+f.key+'-quote';quote.type='text';quote.maxLength=1800;quote.placeholder='Exact quote in recorded witness statement';quote.setAttribute('aria-label',f.label+' witness quote');details.append(quote);
    quote.addEventListener('input',()=>{remember();write(f.key,{...read(f.key),quote:quote.value});changed();});
    box.append(details);return box;
  }
  function removeReference(){if(referenceURL)URL.revokeObjectURL(referenceURL);referenceURL=null;el('reference-preview').hidden=true;el('reference-preview').removeAttribute('src');el('reference-file').value='';el('reference-status').textContent='No local reference selected.';el('remove-reference').hidden=true;}
  function init(schema,options){
    callbacks=options;groups=schema.groups;
    groups.forEach((group,index)=>{
      const tab=node('button');tab.type='button';tab.id='lab-tab-'+group.id;tab.setAttribute('role','tab');tab.setAttribute('aria-controls','lab-group-'+group.id);tab.setAttribute('aria-label',group.label);tab.title=group.label;
      const icon=node('img');icon.src='/static/icons/'+group.icon+'.svg';icon.alt='';icon.width=16;icon.height=16;tab.append(icon,node('span','',group.short));el('lab-tabs').append(tab);
      tab.addEventListener('click',()=>groupTab(group.id));tab.addEventListener('keydown',event=>{let next;if(event.key==='ArrowRight')next=(index+1)%groups.length;if(event.key==='ArrowLeft')next=(index+groups.length-1)%groups.length;if(event.key==='Home')next=0;if(event.key==='End')next=groups.length-1;if(next!==undefined){event.preventDefault();event.stopPropagation();groupTab(groups[next].id,true);}});
      const panel=node('div','lab-group');panel.id='lab-group-'+group.id;panel.setAttribute('role','tabpanel');panel.setAttribute('aria-labelledby',tab.id);panel.append(node('h2','',group.label));
      if(group.id==='build')panel.append(node('p','muted small','Build requests may not be visible in a cropped portrait. Choose Upper Body in Appearance for more context. No body measurements are inferred.'));
      if(group.id==='marks')panel.append(node('p','muted small','Describe only supplied marks. Left and right refer to the subject’s own anatomical side. Leave unknown locations unspecified.'));
      group.fields.forEach(field=>panel.append(buildField(field)));
      if(group.id==='appearance'){
        for(const [name,label,values] of [['style','Output style',[['forensic','Forensic Sketch'],['portrait','Realistic Illustration']]],['view','Composition',[['Portrait','Portrait'],['16:9','16:9'],['Upper Body','Upper Body']]]]){
          const wrapper=node('label','lab-presentation',label),select=node('select');select.id='lab-'+name;
          values.forEach(([value,label])=>{const option=node('option','',label);option.value=value;select.append(option);});
          select.addEventListener('change',()=>{remember();callbacks.setPresentation(name,select.value);changed();});wrapper.append(select);panel.append(wrapper);
        }
      }
      el('lab-groups').append(panel);
    });
    el('reset-lab-group').addEventListener('click',()=>{remember();groups.find(g=>g.id===active).fields.forEach(f=>write(f.key,empty()));changed();});
    el('undo-lab').addEventListener('click',()=>{const previous=undo.pop();if(!previous)return;lab=previous.lab;callbacks.setPresentation('style',previous.style);callbacks.setPresentation('view',previous.view);Object.entries(previous.shared).forEach(([key,value])=>callbacks.setShared(key,value));changed();});
    el('reference-consent').addEventListener('change',()=>{el('reference-file').disabled=!enabled||!el('reference-consent').checked;if(!el('reference-consent').checked)removeReference();});
    el('reference-file').addEventListener('change',async()=>{
      const file=el('reference-file').files[0],caseAtSelection=currentCase;if(!file)return;
      try{
        if(!enabled||!el('reference-consent').checked)throw Error('Confirm synthetic or consented use first.');
        if(!['image/png','image/jpeg','image/webp'].includes(file.type)||file.size>5*1024*1024)throw Error('Use a PNG, JPEG or WebP up to 5 MiB.');
        const bytes=new Uint8Array(await file.slice(0,16).arrayBuffer());
        const png=bytes[0]===137&&bytes[1]===80&&bytes[2]===78&&bytes[3]===71;
        const jpeg=bytes[0]===255&&bytes[1]===216&&bytes[2]===255;
        const webp=String.fromCharCode(...bytes.slice(0,4))==='RIFF'&&String.fromCharCode(...bytes.slice(8,12))==='WEBP';
        if(!(file.type==='image/png'&&png||file.type==='image/jpeg'&&jpeg||file.type==='image/webp'&&webp))throw Error('File content does not match its image type.');
        const url=URL.createObjectURL(file),image=new Image();image.src=url;
        try{await image.decode();if(image.naturalWidth>8192||image.naturalHeight>8192||image.naturalWidth*image.naturalHeight>16000000)throw Error('Reference dimensions are too large.');}
        catch(error){URL.revokeObjectURL(url);throw Error('Reference cannot be decoded or exceeds 16 megapixels.');}
        if(currentCase!==caseAtSelection||!enabled||!el('reference-consent').checked){URL.revokeObjectURL(url);return;}
        if(referenceURL)URL.revokeObjectURL(referenceURL);referenceURL=url;el('reference-preview').src=url;el('reference-preview').hidden=false;el('remove-reference').hidden=false;el('reference-status').textContent='Local reference · '+image.naturalWidth+' × '+image.naturalHeight+' · not sent to Codex.';
      }catch(error){el('reference-status').textContent=error.message;el('reference-file').value='';}
    });
    el('remove-reference').addEventListener('click',removeReference);
    groupTab(active);refresh();
  }
  function load(draft,lastGenerated,caseId){
    lab=clone(draft.lab||{});baseline=clone(lastGenerated);undo=[];
    if(currentCase!==caseId){removeReference();el('reference-consent').checked=false;currentCase=caseId;}
    el('lab-style').value=draft.style;el('lab-view').value=draft.view;invalidate();refresh();
  }
  function availability(allow,busy){enabled=allow;el('lab-locked').hidden=allow;el('lab-content').hidden=!allow;el('update-preview').disabled=!allow||busy;el('update-preview').textContent=busy?'Generating…':'Update Preview';el('reset-lab-group').disabled=!allow;el('reference-file').disabled=!allow||!el('reference-consent').checked;refresh();}
  return {init,load,clearUndo:()=>{undo=[];refresh();},read:()=>clone(lab),refresh,availability,invalidate,setBaseline:draft=>{baseline=clone(draft);refresh();},syncPresentation:(name,value)=>{if(el('lab-'+name))el('lab-'+name).value=value;}};
})();
