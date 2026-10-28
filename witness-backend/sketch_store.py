"""Validated, case-scoped local canvas revisions. No AI/subprocess route."""
import base64
import binascii
import hashlib
import io
import json
import math
import sqlite3
import uuid
from typing import Literal
from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import Field, model_validator
import case_store as store

MAX_BYTES=12*1024*1024
MAX_PIXELS=16_000_000

class Operation(store.Strict):
    tool: Literal['pencil','brush','eraser','line','rectangle','ellipse','arrow','text','crop','rotate','flip','clear']
    points: list[tuple[float,float,float]] = Field(default_factory=list,max_length=20000)
    color: str = Field(default='#111111',pattern='^#[0-9a-fA-F]{6}$')
    width: float = Field(default=4,ge=1,le=120,allow_inf_nan=False)
    opacity: float = Field(default=1,ge=0.05,le=1,allow_inf_nan=False)
    text: str = Field(default='',max_length=240)
    rect: tuple[int,int,int,int] | None = None

    @model_validator(mode='after')
    def validate_shape(self):
        if any(not all(math.isfinite(v) for v in point) or not 0<=point[2]<=1 for point in self.points):
            raise ValueError('Invalid pointer coordinates/pressure')
        if self.tool in {'pencil','brush','eraser','line','rectangle','ellipse','arrow','text'}:
            if len(self.points)<(2 if self.tool in {'line','rectangle','ellipse','arrow'} else 1):
                raise ValueError('Drawing needs points')
        if self.tool=='text' and not self.text.strip():
            raise ValueError('Text annotation cannot be blank')
        if self.tool=='crop' and self.rect is None:
            raise ValueError('Crop needs rectangle')
        return self

class Project(store.Strict):
    schema_version: Literal[1] = 1
    source_version_id: str = Field(pattern='^[0-9a-f]{32}$')
    operations: list[Operation] = Field(default_factory=list,max_length=2000)

    @model_validator(mode='after')
    def budget(self):
        if sum(len(o.points) for o in self.operations)>100000 or len(self.model_dump_json())>2*1024*1024:
            raise ValueError('Sketch project is too complex; save and start from a flattened base')
        return self

class SaveEdit(store.Strict):
    parent_id: str = Field(pattern='^[0-9a-f]{32}$')
    request_key: str = Field(pattern='^[0-9a-f]{32}$')
    png: str = Field(min_length=32,max_length=16*1024*1024+32)
    project: Project


def owned(con,case_id,version_id):
    case=store.row(con,case_id)
    if not case['synthetic'] and not case['frozen_at']:
        raise HTTPException(409,'Freeze the independent account before editing images')
    version=con.execute('SELECT * FROM versions WHERE id=? AND case_id=?',(version_id,case_id)).fetchone()
    if not version:
        raise HTTPException(404,'Image version does not belong to this case')
    return version


def open_project(case_id,version_id):
    with store.connection() as con:
        owned(con,case_id,version_id)
        record=con.execute('SELECT project FROM local_edits WHERE version_id=?',(version_id,)).fetchone()
        project=json.loads(record[0]) if record else Project(source_version_id=version_id).model_dump()
        owned(con,case_id,project['source_version_id'])
        store.image_path(version_id);store.image_path(project['source_version_id'])
    return {'version_id':version_id,'project':project,'source_url':f"/api/cases/{case_id}/versions/{project['source_version_id']}/pixels",'modified_illustration':bool(record)}


def dimensions(project,size):
    w,h=size
    if w*h>MAX_PIXELS:
        raise HTTPException(422,'Sketch images must be at most 16 megapixels')
    for op in project.operations:
        if any(not (0<=x<=w and 0<=y<=h) for x,y,_ in op.points):
            raise HTTPException(422,'Drawing points must lie within the current image')
        if op.tool=='crop':
            x,y,cw,ch=op.rect
            if x<0 or y<0 or cw<32 or ch<32 or x+cw>w or y+ch>h:
                raise HTTPException(422,'Crop must be within the image and at least 32×32 pixels')
            w,h=cw,ch
        elif op.tool=='rotate':
            w,h=h,w
    return w,h


def save_edit(case_id,request):
    if not request.png.startswith('data:image/png;base64,'):
        raise HTTPException(422,'Local edits must be PNG images')
    try:
        data=base64.b64decode(request.png.split(',',1)[1],validate=True)
    except (ValueError,binascii.Error):
        raise HTTPException(422,'Invalid PNG encoding') from None
    if not (64<=len(data)<=MAX_BYTES) or not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise HTTPException(422,'Invalid PNG signature or size; maximum 12 MiB')
    try:
        with Image.open(io.BytesIO(data)) as im:
            size=im.size
            if im.format!='PNG' or im.width<32 or im.height<32 or im.width>8192 or im.height>8192 or im.width*im.height>MAX_PIXELS:
                raise ValueError('Invalid dimensions')
            im.verify()
        with Image.open(io.BytesIO(data)) as im:im.load()
    except (ValueError,OSError,UnidentifiedImageError,Image.DecompressionBombError):
        raise HTTPException(422,'Unreadable PNG or unsupported image dimensions') from None
    digest=hashlib.sha256(data).hexdigest()
    payload_hash=hashlib.sha256(json.dumps({'parent_id':request.parent_id,'project':request.project.model_dump(),'sha256':digest},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    target=None;temporary=None;committed=False;created=False
    try:
        with store.connection() as con:
            con.execute('BEGIN IMMEDIATE')
            parent=owned(con,case_id,request.parent_id)
            existing=con.execute('SELECT * FROM local_edits WHERE request_key=?',(request.request_key,)).fetchone()
            if existing:
                if existing['case_id']!=case_id or existing['payload_hash']!=payload_hash:
                    raise HTTPException(409,'Save request key already used for different edits')
                store.image_path(existing['version_id'])
                return {'version_id':existing['version_id'],'sha256':digest,'replayed':True}
            source=owned(con,case_id,request.project.source_version_id)
            prior=con.execute('SELECT project FROM local_edits WHERE version_id=?',(request.parent_id,)).fetchone()
            root=json.loads(prior[0])['source_version_id'] if prior else request.parent_id
            if request.project.source_version_id!=root:
                raise HTTPException(422,'Project source must match the selected parent’s sketch source')
            store.image_path(parent['id'])
            with Image.open(store.image_path(source['id'])) as image:
                expected=dimensions(request.project,ImageOps.exif_transpose(image).size)
            if size!=expected:
                raise HTTPException(422,'PNG dimensions do not match the editing operations')
            version_id=uuid.uuid4().hex;timestamp=store.now()
            target=store.safe_path(case_id,version_id,'.png');target.parent.mkdir(parents=True,exist_ok=True)
            temporary=target.with_suffix('.png.tmp')
            with temporary.open('xb') as out:out.write(data)
            # Unique revision ID and exclusive file creation; never replace an existing version.
            with target.open('xb') as out:
                created=True
                out.write(temporary.read_bytes())
            temporary.unlink();temporary=None
            snapshot=json.loads(parent['draft']);snapshot['_workspace']='sketch';snapshot['_parent_id']=parent['id']
            snapshot_json=json.dumps(snapshot,ensure_ascii=False)
            con.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?)',(version_id,case_id,'complete','Local artist canvas edit; no AI generation',parent['style'],timestamp,'Local edited illustration saved.', '/images/'+version_id,snapshot_json))
            con.execute('INSERT INTO versions VALUES(?,?,?,?,?,?,?,?)',(version_id,case_id,parent['id'],timestamp,str(target.relative_to(store.DATA.resolve())),digest,parent['style'],snapshot_json))
            original=con.execute("SELECT text FROM statements WHERE case_id=? AND kind='original'",(case_id,)).fetchone()[0]
            metadata={'generation_job_id':None,'local_save_id':version_id,'outcome':'saved','mode':'local_canvas_edit','creation_kind':'local_canvas_edit','source':'artist','modified_illustration':True,'original_prompt':original,'refinement_prompt':'','generation_prompt':None,'width':size[0],'height':size[1],'image_path':str(target.relative_to(store.DATA.resolve())),'attribute_snapshot':{k:v for k,v in snapshot.items() if not k.startswith('_')},'editing_metadata':{'source_version_id':source['id'],'operation_count':len(request.project.operations),'tools':sorted({o.tool for o in request.project.operations}),'project_url':f'/api/cases/{case_id}/versions/{version_id}/sketch'}}
            con.execute('INSERT INTO version_details VALUES(?,?)',(version_id,json.dumps(metadata,ensure_ascii=False)))
            con.execute('INSERT INTO local_edits VALUES(?,?,?,?,?,?)',(version_id,case_id,request.request_key,payload_hash,request.project.model_dump_json(),timestamp))
            selected=con.execute('SELECT selected_id FROM selections WHERE case_id=?',(case_id,)).fetchone()
            if not selected or not selected[0] or selected[0]==parent['id']:
                con.execute('INSERT INTO selections(case_id,selected_id) VALUES(?,?) ON CONFLICT(case_id) DO UPDATE SET selected_id=excluded.selected_id',(case_id,version_id))
            store.event(con,case_id,'local_canvas_edit_saved',version_id+' · artist edit · parent '+parent['id'])
        committed=True
    finally:
        if temporary and temporary.exists():temporary.unlink()
        if target and created and not committed and target.exists():target.unlink()
    return {'version_id':version_id,'sha256':digest,'replayed':False}
