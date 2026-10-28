"""Case-scoped source imports and deterministic browser enhancement revisions. No AI calls."""
import base64
import binascii
import hashlib
import io
import json
import uuid
from typing import Literal
from fastapi import HTTPException
from PIL import Image,ImageOps,UnidentifiedImageError
from pydantic import Field
import case_store as store
from sketch_store import owned,MAX_BYTES,MAX_PIXELS

class Adjustments(store.Strict):
    brightness: float = Field(default=0,ge=-100,le=100,allow_inf_nan=False)
    contrast: float = Field(default=0,ge=-95,le=95,allow_inf_nan=False)
    exposure: float = Field(default=0,ge=-3,le=3,allow_inf_nan=False)
    gamma: float = Field(default=1,ge=.2,le=3,allow_inf_nan=False)
    highlights: float = Field(default=0,ge=-100,le=100,allow_inf_nan=False)
    shadows: float = Field(default=0,ge=-100,le=100,allow_inf_nan=False)
    saturation: float = Field(default=100,ge=0,le=200,allow_inf_nan=False)
    temperature: float = Field(default=0,ge=-100,le=100,allow_inf_nan=False)
    sharpen: float = Field(default=0,ge=0,le=200,allow_inf_nan=False)
    smoothing: float = Field(default=0,ge=0,le=100,allow_inf_nan=False)
    blur: int = Field(default=0,ge=0,le=5)
    grayscale: bool = False
    invert: bool = False
    resize: int = Field(default=100,ge=25,le=150)

class ImportImage(store.Strict):
    request_key: str = Field(pattern='^[0-9a-f]{32}$')
    image: str = Field(min_length=32,max_length=16*1024*1024+64)
    filename: str = Field(min_length=1,max_length=180)
    consent: Literal[True]

class SaveEnhancement(store.Strict):
    parent_id: str = Field(pattern='^[0-9a-f]{32}$')
    source_id: str = Field(pattern='^[0-9a-f]{32}$')
    request_key: str = Field(pattern='^[0-9a-f]{32}$')
    png: str = Field(min_length=32,max_length=16*1024*1024+64)
    adjustments: Adjustments
    engine: Literal['rgba-worker-v1'] = 'rgba-worker-v1'


def decoded(value,only_png=False):
    try:
        header,encoded=value.split(',',1)
        mime={'data:image/png;base64':'PNG','data:image/jpeg;base64':'JPEG','data:image/webp;base64':'WEBP'}[header]
        if only_png and mime!='PNG':raise ValueError()
        data=base64.b64decode(encoded,validate=True)
        if not 64<=len(data)<=MAX_BYTES:raise ValueError()
        with Image.open(io.BytesIO(data)) as image:
            if image.format!=mime or image.width<32 or image.height<32 or max(image.size)>8192 or image.width*image.height>MAX_PIXELS or getattr(image,'n_frames',1)!=1:
                raise ValueError()
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            image.load();oriented=ImageOps.exif_transpose(image).convert('RGBA');oriented.info.clear()
        return data,mime,oriented
    except (ValueError,KeyError,TypeError,SyntaxError,binascii.Error,OSError,UnidentifiedImageError,Image.DecompressionBombError):
        raise HTTPException(422,'Use a readable, single-frame PNG, JPEG or WebP, 32–8192 pixels per side, at most 16 megapixels and 12 MiB; MIME must match actual format.') from None


def canonical_image(case_id,version_id):
    with store.connection() as con:owned(con,case_id,version_id)
    path=store.image_path(version_id)
    try:
        with Image.open(path) as image:
            if image.width*image.height>MAX_PIXELS:raise ValueError()
            image.load();result=ImageOps.exif_transpose(image).convert('RGBA');result.info.clear()
        return result
    except (ValueError,OSError,Image.DecompressionBombError):
        raise HTTPException(422,'Source image cannot be opened for local enhancement.') from None


def png_bytes(image):
    image.info.clear();out=io.BytesIO();image.save(out,format='PNG');return out.getvalue()


def source(case_id,version_id):
    with store.connection() as con:
        parent=owned(con,case_id,version_id)
        record=con.execute("SELECT payload FROM image_operations WHERE version_id=? AND kind='enhance'",(version_id,)).fetchone()
        payload=json.loads(record[0]) if record else None
        source_id=payload['source_id'] if payload else version_id
        owned(con,case_id,source_id);store.image_path(source_id);store.image_path(parent['id'])
        return {'source_id':source_id,'parent_id':version_id,'source_url':f'/api/cases/{case_id}/versions/{source_id}/pixels','adjustments':payload['adjustments'] if payload else Adjustments().model_dump(),'engine':'rgba-worker-v1'}


def commit(case_id,kind,request_key,data,suffix,metadata,payload,parent_id=None):
    digest=hashlib.sha256(data).hexdigest()
    signature=hashlib.sha256(json.dumps({'payload':payload,'sha256':digest},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    target=None;temporary=None;created=False;committed=False
    try:
        with store.connection() as con:
            con.execute('BEGIN IMMEDIATE');case=store.row(con,case_id)
            if not case['synthetic'] and not case['frozen_at']:raise HTTPException(409,'Freeze the original witness account before importing or editing images.')
            prior=con.execute('SELECT * FROM image_operations WHERE request_key=?',(request_key,)).fetchone()
            if prior:
                if prior['case_id']!=case_id or prior['signature']!=signature:raise HTTPException(409,'Request key already used for different image inputs.')
                store.image_path(prior['version_id']);return {'version_id':prior['version_id'],'sha256':digest,'replayed':True}
            if parent_id:
                parent=owned(con,case_id,parent_id);store.image_path(parent_id);snapshot=json.loads(parent['draft']);style=parent['style']
                owned(con,case_id,payload['source_id']);store.image_path(payload['source_id'])
                previous=con.execute("SELECT payload FROM image_operations WHERE version_id=? AND kind='enhance'",(parent_id,)).fetchone()
                root=json.loads(previous[0])['source_id'] if previous else parent_id
                if root!=payload['source_id']:raise HTTPException(422,'Enhancement source must match the opened parent’s non-destructive source.')
            else:snapshot=json.loads(case['draft']);style=snapshot['style']
            version_id=uuid.uuid4().hex;timestamp=store.now();target=store.safe_path(case_id,version_id,suffix);target.parent.mkdir(parents=True,exist_ok=True);temporary=target.with_suffix(suffix+'.tmp')
            with temporary.open('xb') as out:out.write(data)
            with target.open('xb') as out:
                created=True;out.write(temporary.read_bytes())
            temporary.unlink();temporary=None
            snapshot['_workspace']='enhance' if kind=='enhance' else 'upload';snapshot['_parent_id']=parent_id;snapshot_json=json.dumps(snapshot,ensure_ascii=False)
            con.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?)',(version_id,case_id,'complete','Local '+kind+'; no AI generation',style,timestamp,'Local image saved; no AI call.','/images/'+version_id,snapshot_json))
            con.execute('INSERT INTO versions VALUES(?,?,?,?,?,?,?,?)',(version_id,case_id,parent_id,timestamp,str(target.relative_to(store.DATA.resolve())),digest,style,snapshot_json))
            original=con.execute("SELECT text FROM statements WHERE case_id=? AND kind='original'",(case_id,)).fetchone()[0]
            metadata.update(generation_job_id=None,local_save_id=version_id,outcome='saved',image_path=str(target.relative_to(store.DATA.resolve())),original_prompt=original,generation_prompt=None,refinement_prompt='',attribute_snapshot={k:v for k,v in snapshot.items() if not k.startswith('_')})
            con.execute('INSERT INTO version_details VALUES(?,?)',(version_id,json.dumps(metadata,ensure_ascii=False)))
            con.execute('INSERT INTO image_operations VALUES(?,?,?,?,?,?,?)',(version_id,case_id,kind,request_key,signature,json.dumps(payload,ensure_ascii=False),timestamp))
            selected=con.execute('SELECT selected_id FROM selections WHERE case_id=?',(case_id,)).fetchone()
            if kind=='upload' or not selected or not selected[0] or selected[0]==parent_id:
                con.execute('INSERT INTO selections(case_id,selected_id) VALUES(?,?) ON CONFLICT(case_id) DO UPDATE SET selected_id=excluded.selected_id',(case_id,version_id))
            store.event(con,case_id,'source_image_imported' if kind=='upload' else 'local_enhancement_saved',version_id)
        committed=True
    finally:
        if temporary and temporary.exists():temporary.unlink()
        if created and not committed and target and target.exists():target.unlink()
    return {'version_id':version_id,'sha256':digest,'replayed':False}


def import_image(case_id,request):
    data,format,image=decoded(request.image)
    # Filename is a display label only; it is never used as a filesystem path.
    filename=request.filename.replace('\\','/').split('/')[-1]
    filename=''.join(c for c in filename if c.isprintable())[:180] or 'Imported source'
    metadata={'mode':'uploaded_source','creation_kind':'uploaded_source','source':'upload','modified_illustration':False,'source_filename':filename,'source_format':format,'width':image.width,'height':image.height,'metadata_preserved_in_original':True,'working_copy_exif_oriented':True}
    return commit(case_id,'upload',request.request_key,data,{'PNG':'.png','JPEG':'.jpg','WEBP':'.webp'}[format],metadata,{'filename':filename,'consent':True})


def save_enhancement(case_id,request):
    _,_,image=decoded(request.png,only_png=True)
    canonical=canonical_image(case_id,request.source_id)
    factor=request.adjustments.resize/100
    expected=(max(32,int(canonical.width*factor+.5)),max(32,int(canonical.height*factor+.5)))
    if image.size!=expected or image.width*image.height>MAX_PIXELS or max(image.size)>8192:raise HTTPException(422,'Enhanced output dimensions do not match the resize setting or exceed the image budget.')
    payload={'parent_id':request.parent_id,'source_id':request.source_id,'adjustments':request.adjustments.model_dump(),'engine':request.engine}
    metadata={'mode':'local_enhancement','creation_kind':'local_enhancement','source':'local_adjustment','modified_illustration':True,'width':image.width,'height':image.height,**payload,'rendering_tolerance':'Saved decoded RGBA equals committed Canvas PNG pixels; encoded PNG bytes may differ after metadata stripping.'}
    return commit(case_id,'enhance',request.request_key,png_bytes(image),'.png',metadata,payload,request.parent_id)

CONTROLS=[
 ('tonal','brightness','Brightness',-100,100,1),('tonal','contrast','Contrast',-95,95,1),('tonal','exposure','Exposure (EV)',-3,3,.1),('tonal','gamma','Gamma',.2,3,.05),('tonal','highlights','Highlights',-100,100,1),('tonal','shadows','Shadows',-100,100,1),
 ('detail','sharpen','Sharpening',0,200,1),('detail','smoothing','Noise smoothing',0,100,1),('detail','blur','Blur radius (px)',0,5,1),
 ('color','saturation','Saturation (%)',0,200,1),('color','temperature','Temperature',-100,100,1)]
PRESETS={
 'portrait':{'label':'Portrait cleanup','values':{'contrast':8,'shadows':8,'smoothing':20,'sharpen':25}},
 'pencil':{'label':'Pencil sketch contrast','values':{'contrast':25,'brightness':4,'grayscale':True,'sharpen':35}},
 'forensic':{'label':'Grayscale forensic illustration','values':{'grayscale':True,'contrast':12}},
 'lowlight':{'label':'Low-light visibility','values':{'exposure':.8,'gamma':1.2,'shadows':25,'smoothing':15}},
 'detail':{'label':'High-detail inspection','values':{'contrast':10,'sharpen':100,'smoothing':5}}
}

def schema():
    return {'defaults':Adjustments().model_dump(),'controls':[{'group':g,'key':k,'label':label,'min':lo,'max':hi,'step':step} for g,k,label,lo,hi,step in CONTROLS], 'presets':{k:{**v,'values':Adjustments(**v['values']).model_dump()} for k,v in PRESETS.items()},'engine':'rgba-worker-v1'}
