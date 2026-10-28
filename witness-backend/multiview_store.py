"""Experimental text-only 2D sheets and explicit operator-reviewed panel crops."""
import hashlib
import io
import json
import uuid
from typing import Literal
from fastapi import HTTPException
from PIL import Image,ImageOps
from pydantic import Field
import case_store as store
from sketch_store import owned

ROUTE='Existing authenticated Codex CLI → built-in image_gen (text-only)'
ANGLES=['front','left','right','three_quarter']

class Request(store.Strict):
    parent_id: str = Field(pattern='^[0-9a-f]{32}$')
    revision: int = Field(ge=0)
    draft: store.Draft
    request_key: str = Field(pattern='^[0-9a-f]{32}$')
    reviewed_prompt: str = Field(default='',max_length=2500)

class Panel(store.Strict):
    angle: Literal['front','left','right','three_quarter']
    rect: tuple[int,int,int,int]

class Layout(store.Strict):
    checked: Literal[True]
    panels: list[Panel] = Field(min_length=4,max_length=4)
    note: str = Field(default='',max_length=500)


def input_for(con,case_id,request,enforce_limit=True):
    case=store.row(con,case_id);parent=owned(con,case_id,request.parent_id);store.image_path(parent['id'])
    description,style,snapshot=store.generation_input(con,case_id,request.draft,enforce_limit=False)
    # Replace only the generated generic composition footer, never witness text or attributes.
    description=description.rsplit('\nComposition:',1)[0]
    meta=con.execute('SELECT metadata FROM version_details WHERE id=?',(parent['id'],)).fetchone();metadata=json.loads(meta[0]) if meta else {}
    inherited=metadata.get('refinement_prompt','')
    description+='\nSource revision '+parent['id']+'; '+metadata.get('mode','Codex generation')+'; style '+parent['style']+'.'
    if inherited:description+=' Operator parent request (best effort): '+inherited
    description+='\nGenerate ONE experimental 2D 2×2 head-and-shoulders character sheet. Top-left FRONT; top-right LEFT PROFILE (nose points image-left); bottom-left RIGHT PROFILE (nose image-right); bottom-right THREE-QUARTER. Use these supplied pose labels, equal panels and clear gutters. Consistent lighting and requested facial characteristics across views. Sheet layout overrides single-portrait framing. Text-only interpretation: identity consistency is uncertain; not a 3D mesh or verified likeness. Unknown features remain unspecified.'
    if enforce_limit and len(description)>2500:raise HTTPException(422,f'Multi-view prompt is {len(description)}/2500 characters. Nothing was truncated. Reduce optional current requests explicitly; original testimony is unchanged.')
    data=json.loads(snapshot);data.update(_parent_id=parent['id'],_workspace='multiview',_multiview=True,_generation_route=ROUTE,_source_revision={'id':parent['id'],'sha256':parent['sha256'],'created_at':parent['created_at'],'style':parent['style'],'mode':metadata.get('mode','prompt_regeneration')})
    return description,style,json.dumps(data,ensure_ascii=False)


def preview(case_id,request):
    with store.connection() as con:description,style,_=input_for(con,case_id,request,enforce_limit=False)
    return {'description':description,'style':style,'length':len(description),'limit':2500,'over_limit':len(description)>2500,'route':ROUTE,'image_reference_used':False}


def previous(case_id,request):
    with store.connection() as con:
        record=con.execute('SELECT * FROM multiview_requests WHERE request_key=?',(request.request_key,)).fetchone()
        if record:
            if record['case_id']!=case_id or record['payload']!=request.model_dump_json():raise HTTPException(409,'Request key already used for different multi-view inputs.')
            return record['job_id']


def list_sheets(case_id):
    with store.connection() as con:
        store.row(con,case_id)
        jobs=[dict(r) for r in con.execute('SELECT m.job_id,m.parent_id,m.created_at,j.status,j.message FROM multiview_requests m JOIN jobs j ON j.id=m.job_id WHERE m.case_id=? ORDER BY m.created_at,m.job_id',(case_id,))]
        for item in jobs:
            version=con.execute('SELECT sha256 FROM versions WHERE id=? AND case_id=?',(item['job_id'],case_id)).fetchone()
            if item['status']=='complete' and version:
                item['image_url']='/images/'+item['job_id'];item['sha256']=version[0];meta=con.execute('SELECT metadata FROM version_details WHERE id=?',(item['job_id'],)).fetchone();item['image_format']=json.loads(meta[0]).get('image_format','PNG') if meta else 'PNG';item['layout']=latest_layout(con,case_id,item['job_id'])
        return {'requests':jobs,'route':ROUTE,'image_reference_used':False}


def sheet(con,case_id,version_id):
    version=owned(con,case_id,version_id)
    if not con.execute('SELECT 1 FROM multiview_requests WHERE job_id=? AND case_id=?',(version_id,case_id)).fetchone():raise HTTPException(404,'This version is not a generated concept sheet.')
    store.image_path(version_id)
    return version


def latest_layout(con,case_id,version_id):
    record=con.execute('SELECT * FROM multiview_layouts WHERE case_id=? AND version_id=? ORDER BY created_at DESC,id DESC LIMIT 1',(case_id,version_id)).fetchone()
    if not record:return None
    return {'id':record['id'],'created_at':record['created_at'],'source_sha256':record['source_sha256'],'source':'operator visual layout review','note':record['note'],'panels':json.loads(record['panels'])}


def png_crop(image,rect):
    x,y,w,h=rect;out=io.BytesIO();crop=image.crop((x,y,x+w,y+h)).convert('RGBA');crop.info.clear();crop.save(out,format='PNG');return out.getvalue()


def save_layout(case_id,version_id,request):
    with store.connection() as con:
        con.execute('BEGIN IMMEDIATE');version=sheet(con,case_id,version_id)
        if sorted(p.angle for p in request.panels)!=sorted(ANGLES):raise HTTPException(422,'Review exactly one front, left, right and three-quarter panel.')
        with Image.open(store.image_path(version_id)) as image:
            image.load();image=ImageOps.exif_transpose(image);panels=[]
            for p in request.panels:
                x,y,w,h=p.rect
                if x<0 or y<0 or w<32 or h<32 or x+w>image.width or y+h>image.height:raise HTTPException(422,'Panel rectangles must be inside the sheet and at least 32×32 pixels.')
                for other in panels:
                    ox,oy,ow,oh=other['rect']
                    if x<ox+ow and ox<x+w and y<oy+oh and oy<y+h:raise HTTPException(422,'Independent reviewed panels must not overlap.')
                data=png_crop(image,p.rect);panels.append({'angle':p.angle,'rect':list(p.rect),'width':w,'height':h,'sha256':hashlib.sha256(data).hexdigest()})
        layout_id=uuid.uuid4().hex;timestamp=store.now()
        con.execute('INSERT INTO multiview_layouts VALUES(?,?,?,?,?,?,?)',(layout_id,case_id,version_id,timestamp,version['sha256'],json.dumps(panels),request.note))
        store.event(con,case_id,'multiview_panels_reviewed',layout_id+' · operator review, not witness testimony')
        return latest_layout(con,case_id,version_id)


def crop_bytes(case_id,version_id,layout_id,angle):
    store.identifier(layout_id)
    with store.connection() as con:
        version=sheet(con,case_id,version_id)
        record=con.execute('SELECT * FROM multiview_layouts WHERE id=? AND version_id=? AND case_id=?',(layout_id,version_id,case_id)).fetchone()
        if not record:raise HTTPException(404,'Unknown reviewed layout.')
        if version['sha256']!=record['source_sha256']:raise HTTPException(409,'Sheet integrity no longer matches reviewed layout.')
        panel=next((p for p in json.loads(record['panels']) if p['angle']==angle),None)
        if not panel:raise HTTPException(404,'This angle is not available.')
        with Image.open(store.image_path(version_id)) as im:data=png_crop(ImageOps.exif_transpose(im),panel['rect'])
        if hashlib.sha256(data).hexdigest()!=panel['sha256']:raise HTTPException(409,'Panel checksum mismatch.')
        return data
