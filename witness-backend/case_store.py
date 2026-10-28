"""Local SQLite case records; no generation provider or subprocess code here."""
import hashlib
import json
import os
import re
import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import HTTPException
from PIL import Image
from lab_schema import FIELDS, LAB_FIELDS, phrase
from pydantic import BaseModel, ConfigDict, Field, model_validator

DATA = Path(os.environ.get('WITNESSTRACE_DATA_DIR', str(Path(__file__).resolve().parent / 'data'))).resolve()
DB = DATA / 'witness.sqlite3'

def now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def connection():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        with con:
            yield con
    finally:
        con.close()

def initialize():
    with connection() as con:
        con.execute('PRAGMA journal_mode=WAL')
        version = con.execute('PRAGMA user_version').fetchone()[0]
        if version > 1:
            raise RuntimeError('Database schema is newer than this application')
        con.executescript('''
        CREATE TABLE IF NOT EXISTS cases (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, synthetic INTEGER NOT NULL,
          created_at TEXT NOT NULL, frozen_at TEXT, draft TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS statements (
          id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), kind TEXT NOT NULL,
          text TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE UNIQUE INDEX IF NOT EXISTS one_original ON statements(case_id) WHERE kind='original';
        CREATE TABLE IF NOT EXISTS case_events (
          id INTEGER PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), kind TEXT NOT NULL,
          created_at TEXT NOT NULL, detail TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS jobs (
          id TEXT PRIMARY KEY, case_id TEXT REFERENCES cases(id), status TEXT NOT NULL,
          description TEXT NOT NULL, style TEXT NOT NULL, created_at TEXT NOT NULL,
          message TEXT NOT NULL, image_url TEXT, draft TEXT);
        CREATE TABLE IF NOT EXISTS versions (
          id TEXT PRIMARY KEY REFERENCES jobs(id), case_id TEXT NOT NULL REFERENCES cases(id),
          parent_id TEXT REFERENCES versions(id), created_at TEXT NOT NULL, path TEXT NOT NULL,
          sha256 TEXT NOT NULL, style TEXT NOT NULL, draft TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS frozen_original_update BEFORE UPDATE ON statements
          WHEN OLD.kind='original' AND (SELECT frozen_at FROM cases WHERE id=OLD.case_id) IS NOT NULL
          BEGIN SELECT RAISE(ABORT,'Original account is frozen'); END;
        CREATE TRIGGER IF NOT EXISTS original_delete BEFORE DELETE ON statements
          WHEN OLD.kind='original' BEGIN SELECT RAISE(ABORT,'Original account cannot be deleted'); END;
        CREATE TRIGGER IF NOT EXISTS clarification_update BEFORE UPDATE ON statements
          WHEN OLD.kind='clarification' BEGIN SELECT RAISE(ABORT,'Clarifications are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS clarification_delete BEFORE DELETE ON statements
          WHEN OLD.kind='clarification' BEGIN SELECT RAISE(ABORT,'Clarifications are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS frozen_case BEFORE UPDATE OF frozen_at ON cases
          WHEN OLD.frozen_at IS NOT NULL BEGIN SELECT RAISE(ABORT,'Account cannot be unfrozen'); END;
        CREATE TABLE IF NOT EXISTS version_details (
          id TEXT PRIMARY KEY REFERENCES versions(id), metadata TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS selections (
          case_id TEXT PRIMARY KEY REFERENCES cases(id), selected_id TEXT REFERENCES versions(id),
          preferred_id TEXT REFERENCES versions(id));
        CREATE TABLE IF NOT EXISTS refinement_requests (
          request_key TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id),
          job_id TEXT UNIQUE NOT NULL REFERENCES jobs(id), parent_id TEXT NOT NULL REFERENCES versions(id),
          instruction TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS immutable_version_details_update BEFORE UPDATE ON version_details
          BEGIN SELECT RAISE(ABORT,'Revision metadata is immutable'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_version_details_delete BEFORE DELETE ON version_details
          BEGIN SELECT RAISE(ABORT,'Revision metadata is immutable'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_refinement_update BEFORE UPDATE ON refinement_requests
          BEGIN SELECT RAISE(ABORT,'Refinement requests are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_refinement_delete BEFORE DELETE ON refinement_requests
          BEGIN SELECT RAISE(ABORT,'Refinement requests are immutable'); END;
        CREATE TABLE IF NOT EXISTS local_edits (
          version_id TEXT PRIMARY KEY REFERENCES versions(id),case_id TEXT NOT NULL REFERENCES cases(id),
          request_key TEXT UNIQUE NOT NULL,payload_hash TEXT NOT NULL,project TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS immutable_local_edits_update BEFORE UPDATE ON local_edits
          BEGIN SELECT RAISE(ABORT,'Local edit projects are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_local_edits_delete BEFORE DELETE ON local_edits
          BEGIN SELECT RAISE(ABORT,'Local edit projects are immutable'); END;
        CREATE TABLE IF NOT EXISTS image_operations (
          version_id TEXT PRIMARY KEY REFERENCES versions(id),case_id TEXT NOT NULL REFERENCES cases(id),
          kind TEXT NOT NULL,request_key TEXT UNIQUE NOT NULL,signature TEXT NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS immutable_image_operations_update BEFORE UPDATE ON image_operations
          BEGIN SELECT RAISE(ABORT,'Image operations are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_image_operations_delete BEFORE DELETE ON image_operations
          BEGIN SELECT RAISE(ABORT,'Image operations are immutable'); END;
        CREATE TABLE IF NOT EXISTS multiview_requests (
          request_key TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id),job_id TEXT UNIQUE NOT NULL REFERENCES jobs(id),
          parent_id TEXT NOT NULL REFERENCES versions(id),created_at TEXT NOT NULL,payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS multiview_layouts (
          id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id),version_id TEXT NOT NULL REFERENCES versions(id),
          created_at TEXT NOT NULL,source_sha256 TEXT NOT NULL,panels TEXT NOT NULL,note TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS report_exports (
          id TEXT PRIMARY KEY,case_id TEXT NOT NULL REFERENCES cases(id),version_id TEXT NOT NULL REFERENCES versions(id),
          created_at TEXT NOT NULL,request_key TEXT UNIQUE NOT NULL,signature TEXT NOT NULL,manifest TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS immutable_multiview_requests_update BEFORE UPDATE ON multiview_requests BEGIN SELECT RAISE(ABORT,'Multi-view requests are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_multiview_requests_delete BEFORE DELETE ON multiview_requests BEGIN SELECT RAISE(ABORT,'Multi-view requests are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_multiview_layouts_update BEFORE UPDATE ON multiview_layouts BEGIN SELECT RAISE(ABORT,'Panel reviews are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_multiview_layouts_delete BEFORE DELETE ON multiview_layouts BEGIN SELECT RAISE(ABORT,'Panel reviews are append-only'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_report_exports_update BEFORE UPDATE ON report_exports BEGIN SELECT RAISE(ABORT,'Report exports are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_report_exports_delete BEFORE DELETE ON report_exports BEGIN SELECT RAISE(ABORT,'Report exports are immutable'); END;
        PRAGMA user_version=1;
        ''')
        # A restarted process cannot truthfully claim a previous subprocess is still owned.
        interrupted=con.execute("SELECT id,case_id FROM jobs WHERE status='working'").fetchall()
        con.execute("UPDATE jobs SET status='failed',message='Server restarted; interrupted job requires explicit retry.' WHERE status='working'")
        for job in interrupted:
            if job['case_id']:
                event(con,job['case_id'],'generation_interrupted',job['id'])

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Attribute(Strict):
    value: str | None = Field(default=None, max_length=100)
    confidence: Literal['unknown','tentative','certain'] = 'unknown'
    source: Literal['operator','witness'] = 'operator'
    quote: str = Field(default='', max_length=1800)

    @model_validator(mode='after')
    def check(self):
        if self.value is None and self.confidence != 'unknown':
            raise ValueError('Unknown value must have unknown confidence')
        if self.value is not None and (not self.value.strip() or self.confidence == 'unknown'):
            raise ValueError('A supplied value needs tentative or certain recollection')
        if self.source == 'witness' and not self.quote.strip():
            raise ValueError('Witness source requires an exact quote')
        return self

class Draft(Strict):
    attributes: dict[str, Attribute] = Field(default_factory=dict)
    lab: dict[str, Attribute] = Field(default_factory=dict)
    style: Literal['forensic','portrait'] = 'forensic'
    view: Literal['Portrait','16:9','Upper Body'] = 'Portrait'
    note: str = Field(default='', max_length=1800)
    note_source: Literal['operator','witness'] = 'operator'

    @model_validator(mode='after')
    def check(self):
        allowed = {'complexion','hair','eyes','facial-hair','age'}
        if set(self.attributes) - allowed:
            raise ValueError('Unsupported Text attribute')
        for key in sorted(allowed):
            self.attributes.setdefault(key, Attribute())
        if set(self.lab) - set(LAB_FIELDS):
            raise ValueError('Unsupported Character Lab attribute')
        for key, field in LAB_FIELDS.items():
            attribute=self.lab.setdefault(key, Attribute())
            value=attribute.value
            if value is None:
                continue
            if field['kind']=='slider' and (not value.isdigit() or not 0<=int(value)<=100):
                raise ValueError('Relative controls must be integers 0–100 or Unknown')
            if field['kind']=='select' and value not in field['options']:
                raise ValueError('Unsupported value for '+field['label'])
        for key, attribute in self.attributes.items():
            if key in FIELDS and FIELDS[key]['kind']=='select' and attribute.value is not None and attribute.value not in FIELDS[key]['options']:
                raise ValueError('Unsupported value for '+FIELDS[key]['label'])
        age = self.attributes['age'].value
        if age is not None and (not age.isdigit() or not 18 <= int(age) <= 100):
            raise ValueError('Estimated age must be 18–100 or Unknown')
        return self

class NewCase(Strict):
    title: str = Field(min_length=1, max_length=120)
    synthetic: bool = False

class SaveCase(Strict):
    revision: int = Field(ge=0)
    original: str | None = Field(default=None, max_length=1800)
    draft: Draft

class Freeze(Strict):
    revision: int = Field(ge=0)
    text: str = Field(min_length=10, max_length=1800)

class Clarification(Strict):
    text: str = Field(min_length=1,max_length=1800)
    source: Literal['operator','witness'] = 'operator'

def identifier(value):
    if not re.fullmatch('[0-9a-f]{32}', value):
        raise HTTPException(404, 'Unknown record')
    return value

def row(con, case_id):
    identifier(case_id)
    record = con.execute('SELECT * FROM cases WHERE id=?',(case_id,)).fetchone()
    if record is None:
        raise HTTPException(404,'Unknown case')
    return record

def event(con, case_id, kind, detail=''):
    con.execute('INSERT INTO case_events(case_id,kind,created_at,detail) VALUES(?,?,?,?)',(case_id,kind,now(),detail))

def list_cases():
    with connection() as con:
        return [dict(r) for r in con.execute('SELECT id,title,synthetic,created_at,frozen_at,revision FROM cases ORDER BY created_at DESC')]

def create(request):
    if not request.title.strip():
        raise HTTPException(422,'Case title is required')
    case_id = uuid.uuid4().hex
    with connection() as con:
        timestamp=now()
        con.execute('INSERT INTO cases(id,title,synthetic,created_at,draft) VALUES(?,?,?,?,?)', (case_id,request.title,int(request.synthetic),timestamp,Draft().model_dump_json()))
        con.execute('INSERT INTO statements VALUES(?,?,?,?,?,?)',(uuid.uuid4().hex,case_id,'original','','synthetic' if request.synthetic else 'witness',timestamp))
        event(con,case_id,'case_created','Synthetic demo' if request.synthetic else 'Witness case')
    return get(case_id)

def get(case_id):
    with connection() as con:
        result = dict(row(con,case_id)); result['draft']=Draft.model_validate_json(result['draft']).model_dump()
        result['statements']=[dict(r) for r in con.execute('SELECT * FROM statements WHERE case_id=? ORDER BY created_at,id',(case_id,))]
        result['events']=[dict(r) for r in con.execute('SELECT * FROM case_events WHERE case_id=? ORDER BY id',(case_id,))]
        result['versions']=[]
        latest_draft=None
        for r in con.execute('SELECT id,parent_id,created_at,sha256,style,draft FROM versions WHERE case_id=? ORDER BY created_at,id',(case_id,)):
            version=dict(r); snapshot=json.loads(version.pop('draft'))
            version.update(image_url='/images/'+r['id'],case_revision=snapshot.pop('_case_revision',None),workspace=snapshot.pop('_workspace','text'))
            metadata=con.execute('SELECT metadata FROM version_details WHERE id=?',(r['id'],)).fetchone()
            if metadata:
                version.update(json.loads(metadata[0]))
            else:
                job=con.execute('SELECT description FROM jobs WHERE id=?',(r['id'],)).fetchone()
                version.update(generation_job_id=r['id'],outcome='complete',mode='prompt_regeneration',original_prompt=job[0] if job else '',refinement_prompt='',attribute_snapshot={k:v for k,v in snapshot.items() if not k.startswith('_')})
            if version['workspace'] not in {'sketch','upload','enhance'}:
                latest_draft=Draft.model_validate({k:v for k,v in snapshot.items() if not k.startswith('_')}).model_dump()
            result['versions'].append(version)
        result['last_generated_draft']=latest_draft
        selection=con.execute('SELECT selected_id,preferred_id FROM selections WHERE case_id=?',(case_id,)).fetchone()
        result['selected_version_id']=selection['selected_id'] if selection and selection['selected_id'] else (result['versions'][-1]['id'] if result['versions'] else None)
        result['preferred_version_id']=selection['preferred_id'] if selection else None
        result['refinements']=[dict(r) for r in con.execute('SELECT r.job_id,r.parent_id,r.instruction,r.created_at,j.status,j.message FROM refinement_requests r JOIN jobs j ON j.id=r.job_id WHERE r.case_id=? ORDER BY r.created_at,r.job_id',(case_id,))]
        result['jobs']=[dict(r) for r in con.execute('SELECT id,status,message,image_url,created_at FROM jobs WHERE case_id=? ORDER BY created_at',(case_id,))]
        # Defense in depth: pre-freeze witness retrieval cannot disclose a generated face.
        if not result['synthetic'] and result['frozen_at'] is None:
            result['versions']=[]
            result['last_generated_draft']=None
            result['selected_version_id']=None
            result['preferred_version_id']=None
            result['refinements']=[]
        return result

def check_quotes(con,case_id,draft):
    texts=[r[0] for r in con.execute("SELECT text FROM statements WHERE case_id=? AND source IN ('witness','synthetic')",(case_id,))]
    for attribute in [*draft.attributes.values(), *draft.lab.values()]:
        if attribute.source == 'witness' and not any(attribute.quote in text for text in texts):
            raise HTTPException(422,'Witness quote must occur exactly in the original account or a witness-sourced clarification')

def save(case_id,request):
    with connection() as con:
        con.execute('BEGIN IMMEDIATE')
        case=row(con,case_id)
        if request.revision != case['revision']:
            raise HTTPException(409,'Case changed elsewhere. Reload before saving.')
        if request.original is not None:
            if case['frozen_at'] is not None:
                raise HTTPException(409,'Original account is frozen and cannot be modified')
            con.execute("UPDATE statements SET text=? WHERE case_id=? AND kind='original'",(request.original,case_id))
        if 'lab' not in request.draft.model_fields_set:
            # Older Text-only clients must not erase saved Character Lab controls.
            request.draft.lab=Draft.model_validate_json(case['draft']).lab
        check_quotes(con,case_id,request.draft)
        con.execute('UPDATE cases SET draft=?,revision=revision+1 WHERE id=?',(request.draft.model_dump_json(),case_id))
        event(con,case_id,'draft_saved','Text and Character Lab draft saved')
    return get(case_id)

def freeze(case_id,request):
    if len(request.text.strip()) < 10:
        raise HTTPException(422,'Enter at least 10 non-whitespace characters')
    with connection() as con:
        con.execute('BEGIN IMMEDIATE')
        case=row(con,case_id)
        if case['frozen_at'] is not None:
            raise HTTPException(409,'Original account is already frozen')
        if request.revision != case['revision']:
            raise HTTPException(409,'Case changed elsewhere. Reload before freezing.')
        # Preserve exact Unicode and whitespace: never strip or normalize testimony.
        timestamp=now()
        con.execute("UPDATE statements SET text=?,created_at=? WHERE case_id=? AND kind='original'",(request.text,timestamp,case_id))
        check_quotes(con,case_id,Draft.model_validate_json(case['draft']))
        con.execute('UPDATE cases SET frozen_at=?,revision=revision+1 WHERE id=?',(timestamp,case_id))
        event(con,case_id,'original_frozen','SHA-256 '+hashlib.sha256(request.text.encode('utf-8')).hexdigest())
    return get(case_id)

def append(case_id,request):
    if not request.text.strip():
        raise HTTPException(422,'Clarification cannot be blank')
    with connection() as con:
        con.execute('BEGIN IMMEDIATE')
        case=row(con,case_id)
        if not case['synthetic'] and case['frozen_at'] is None:
            raise HTTPException(409,'Freeze the original account before adding clarifications')
        con.execute('INSERT INTO statements VALUES(?,?,?,?,?,?)',(uuid.uuid4().hex,case_id,'clarification',request.text,request.source,now()))
        con.execute('UPDATE cases SET revision=revision+1 WHERE id=?',(case_id,))
        event(con,case_id,'clarification_added',request.source)
    return get(case_id)

def generation_input(con,case_id,draft_override=None,enforce_limit=True):
    case=row(con,case_id)
    if not case['synthetic'] and case['frozen_at'] is None:
        raise HTTPException(409,'Freeze the first account before generating')
    draft=draft_override or Draft.model_validate_json(case['draft'])
    check_quotes(con,case_id,draft)
    statements=con.execute('SELECT kind,text,source FROM statements WHERE case_id=? ORDER BY created_at,id',(case_id,)).fetchall()
    original=next(r['text'] for r in statements if r['kind']=='original')
    if len(original.strip()) < 10:
        raise HTTPException(422,'Save an original description of at least 10 characters')
    parts=[('Synthetic fictional demo description' if case['synthetic'] else 'Original free-recall account')+':\n'+original]
    parts += [r['source']+' clarification:\n'+r['text'] for r in statements if r['kind']=='clarification']
    if draft.note:
        raise HTTPException(409,'Append the pending clarification before generating')
    # Group provenance instead of repeating it per field; preserve all supplied values.
    groups={}
    for key,attribute in sorted({**draft.attributes,**draft.lab}.items()):
        if attribute.value is None:
            continue
        label=FIELDS.get(key,{}).get('label',key)
        translated=phrase(key,attribute.value)
        if FIELDS.get(key,{}).get('kind')=='slider':
            translated+=' ('+attribute.value+'/100 relative)'
        groups.setdefault((attribute.source,attribute.confidence),[]).append(label+'='+translated)
    for (source,confidence),requests in sorted(groups.items()):
        parts.append(source+' requests ('+confidence+'; subjective): '+ '; '.join(requests))
    framing={'Portrait':'portrait-oriented head and shoulders','16:9':'wide 16:9 composition, subject centered','Upper Body':'upper body visible, including shoulders and torso'}[draft.view]
    parts.append('Composition: '+framing+'. Prioritize this over default framing. Relative controls are operator directions, not measurements. Unspecified traits are unknown. Preserve recorded unchanged features best-effort; appearance may drift. New illustrative hypothesis, not a verified likeness.')
    description='\n'.join(parts)
    if enforce_limit and len(description)>2500:
        raise HTTPException(422,f'Prompt is {len(description)}/2500 characters. No testimony or attributes were truncated. Review the prompt and explicitly reduce optional requests; the original account remains unchanged.')
    snapshot=draft.model_dump()
    snapshot['_case_revision']=case['revision']
    return description,draft.style,json.dumps(snapshot,ensure_ascii=False)


def prompt_preview(case_id,draft):
    with connection() as con:
        description,style,_=generation_input(con,case_id,draft,enforce_limit=False)
    return {'description':description,'style':style,'length':len(description),'limit':2500,'over_limit':len(description)>2500}


def start_job(job,case_id=None,revision=None,workspace="text",refinement=None,multiview=None):
    with connection() as con:
        con.execute('BEGIN IMMEDIATE')
        snapshot=None
        if con.execute("SELECT 1 FROM jobs WHERE status='working'").fetchone():
            raise HTTPException(409,'A generation result is still being recorded')
        if case_id:
            case=row(con,case_id)
            if revision != case['revision']:
                raise HTTPException(409,'Case changed elsewhere. Reload before generating.')
            job.description,job.style,snapshot=generation_input(con,case_id)
            snapshot_data=json.loads(snapshot);snapshot_data['_workspace']=workspace
            selected=con.execute('SELECT selected_id FROM selections WHERE case_id=?',(case_id,)).fetchone()
            latest=con.execute('SELECT id FROM versions WHERE case_id=? ORDER BY created_at DESC,id DESC LIMIT 1',(case_id,)).fetchone()
            snapshot_data['_parent_id']=selected[0] if selected and selected[0] else (latest[0] if latest else None)
            if refinement:
                job.description,job.style,snapshot=refinement_input(con,case_id,refinement)
                snapshot_data=json.loads(snapshot)
                if job.description != refinement.reviewed_prompt:
                    raise HTTPException(409,'Prompt changed. Review the final prompt again before regenerating.')
            if multiview:
                from multiview_store import input_for
                job.description,job.style,snapshot=input_for(con,case_id,multiview)
                snapshot_data=json.loads(snapshot)
                if job.description!=multiview.reviewed_prompt:raise HTTPException(409,'Multi-view prompt changed. Review it again before generating.')
            snapshot=json.dumps(snapshot_data,ensure_ascii=False)
        con.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?)',(job.job_id,case_id,'working',job.description,job.style,now(),'Generation running',None,snapshot))
        if refinement:
            if Draft.model_validate_json(case['draft']).model_dump()!=refinement.draft.model_dump():
                con.execute('UPDATE cases SET draft=?,revision=revision+1 WHERE id=?',(refinement.draft.model_dump_json(),case_id))
            con.execute('INSERT INTO refinement_requests VALUES(?,?,?,?,?,?,?)',(refinement.request_key,case_id,job.job_id,refinement.parent_id,refinement.instruction,now(),refinement.model_dump_json()))
        if multiview:
            if Draft.model_validate_json(case['draft']).model_dump()!=multiview.draft.model_dump():
                con.execute('UPDATE cases SET draft=?,revision=revision+1 WHERE id=?',(multiview.draft.model_dump_json(),case_id))
            con.execute('INSERT INTO multiview_requests VALUES(?,?,?,?,?,?)',(multiview.request_key,case_id,job.job_id,multiview.parent_id,now(),multiview.model_dump_json()))
        if case_id:
            event(con,case_id,'generation_requested',job.job_id)

def safe_path(case_id,job_id,suffix):
    identifier(case_id);identifier(job_id)
    if suffix not in {'.png','.jpg','.webp'}:
        raise ValueError('Invalid image extension')
    root=DATA.resolve()
    base=root/'cases'
    if not base.resolve().is_relative_to(root):
        raise ValueError('Invalid cases directory')
    path=base/case_id/(job_id+suffix)
    if not path.resolve().is_relative_to(base):
        raise ValueError('Invalid image path')
    return path

def finish_job(job,outputs):
    with connection() as con:
        con.execute('BEGIN IMMEDIATE')
        record=con.execute('SELECT * FROM jobs WHERE id=?',(job.job_id,)).fetchone()
        if record is None or record['status']!='working':
            return
        if job.status=='complete' and record['case_id']:
            source=next(outputs.glob(job.job_id+'.*'))
            with Image.open(source) as image:
                width,height=image.size
                if image.format not in {'PNG','JPEG','WEBP'} or not (128<=width<=8192 and 128<=height<=8192):
                    raise ValueError('Invalid revision image')
                image.verify()
            with Image.open(source) as decoded:
                decoded.load()
            target=safe_path(record['case_id'],job.job_id,source.suffix)
            target.parent.mkdir(parents=True,exist_ok=True)
            # Copy bytes, never transform or overwrite original generator output.
            if target.exists():
                if target.read_bytes()!=source.read_bytes():
                    raise ValueError('Case image collision')
            else:
                temporary=target.with_suffix(target.suffix+'.tmp')
                shutil.copy2(source,temporary)
                temporary.replace(target)
            digest=hashlib.sha256(target.read_bytes()).hexdigest()
            snapshot=json.loads(record['draft'])
            parent_id=snapshot.get('_parent_id')
            con.execute('INSERT INTO versions VALUES(?,?,?,?,?,?,?,?)',(job.job_id,record['case_id'],parent_id,now(),str(target.relative_to(DATA.resolve())),digest,job.style,record['draft']))
            original=con.execute("SELECT text FROM statements WHERE case_id=? AND kind='original'",(record['case_id'],)).fetchone()[0]
            metadata={'generation_job_id':job.job_id,'outcome':'complete','mode':'prompt_regeneration',
                      'original_prompt':original,'generation_prompt':record['description'],
                      'refinement_prompt':snapshot.get('_refinement',''),'width':width,'height':height,
                      'image_path':str(target.relative_to(DATA.resolve())),
                      'attribute_snapshot':{k:v for k,v in snapshot.items() if not k.startswith('_')}}
            if snapshot.get('_multiview'):
                metadata.update(image_format={'.png':'PNG','.jpg':'JPEG','.webp':'WEBP'}[source.suffix],mode='concept_multiview',creation_kind='concept_multiview',generation_route=snapshot['_generation_route'],image_reference_used=False,source_revision=snapshot['_source_revision'],panel_status='unverified; original sheet only until explicit layout review')
            con.execute('INSERT INTO version_details VALUES(?,?)',(job.job_id,json.dumps(metadata,ensure_ascii=False)))
            selection=con.execute('SELECT selected_id FROM selections WHERE case_id=?',(record['case_id'],)).fetchone()
            # Never let a late result override a different explicit selection.
            if not selection or not selection[0] or selection[0]==parent_id:
                con.execute('INSERT INTO selections(case_id,selected_id) VALUES(?,?) ON CONFLICT(case_id) DO UPDATE SET selected_id=excluded.selected_id',(record['case_id'],job.job_id))
        # Store safe classification, not CLI stdout/stderr or authentication output.
        message='Image generated and saved.' if job.status=='complete' else ('Codex CLI not found. Sign in locally after installing Codex.' if 'Codex CLI not found' in job.message else ('Generation timed out.' if 'deadline' in job.message else 'Generation failed; check local Codex availability. No image claimed.'))
        con.execute('UPDATE jobs SET status=?,message=?,image_url=? WHERE id=?',(job.status,message,job.image_url,job.job_id))
        if record['case_id']:
            event(con,record['case_id'],'generation_'+job.status,job.job_id)

def job_status(job_id):
    identifier(job_id)
    with connection() as con:
        r=con.execute('SELECT id AS job_id,status,message,image_url FROM jobs WHERE id=?',(job_id,)).fetchone()
        return dict(r) if r else None

def image_path(job_id):
    identifier(job_id)
    with connection() as con:
        record=con.execute('SELECT * FROM versions WHERE id=?',(job_id,)).fetchone()
        if record is None:
            return None
        case=row(con,record['case_id'])
        if not case['synthetic'] and case['frozen_at'] is None:
            raise HTTPException(409,'Original account must be frozen')
        path=DATA/record['path']
        try:
            safe=safe_path(record['case_id'],job_id,path.suffix)
        except ValueError:
            raise HTTPException(404,'Invalid case image path') from None
        if path.resolve()!=safe.resolve() or not path.is_file():
            raise HTTPException(404,'Case image unavailable')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=record['sha256']:
            raise HTTPException(409,'Image integrity check failed')
        return path


class Refinement(Strict):
    parent_id: str = Field(pattern='^[0-9a-f]{32}$')
    instruction: str = Field(min_length=1,max_length=1800)
    draft: Draft
    revision: int = Field(ge=0)
    request_key: str = Field(pattern='^[0-9a-f]{32}$')
    reviewed_prompt: str = Field(default='',max_length=2500)

class Selection(Strict):
    version_id: str = Field(pattern='^[0-9a-f]{32}$')
    preferred: bool = False

def select_version(case_id,request):
    with connection() as con:
        con.execute('BEGIN IMMEDIATE')
        row(con,case_id)
        if not con.execute('SELECT 1 FROM versions WHERE id=? AND case_id=?',(request.version_id,case_id)).fetchone():
            raise HTTPException(404,'Version does not belong to this case')
        image_path(request.version_id)
        column='preferred_id' if request.preferred else 'selected_id'
        con.execute(f'INSERT INTO selections(case_id,{column}) VALUES(?,?) ON CONFLICT(case_id) DO UPDATE SET {column}=excluded.{column}',(case_id,request.version_id))
        event(con,case_id,'preferred_version' if request.preferred else 'version_selected',request.version_id)
    return get(case_id)

def refinement_input(con,case_id,request,enforce_limit=True):
    if not request.instruction.strip():
        raise HTTPException(422,'Enter an explicit refinement instruction')
    parent=con.execute('SELECT * FROM versions WHERE id=? AND case_id=?',(request.parent_id,case_id)).fetchone()
    if not parent:
        raise HTTPException(404,'Parent version does not belong to this case')
    image_path(request.parent_id)
    description,style,snapshot=generation_input(con,case_id,request.draft,enforce_limit=False)
    # Include only explicit requests along this branch, never model-invented changes.
    ancestors=[];cursor=parent
    while cursor:
        previous=con.execute('SELECT instruction FROM refinement_requests WHERE job_id=?',(cursor['id'],)).fetchone()
        if previous:ancestors.append(previous[0])
        cursor=con.execute('SELECT * FROM versions WHERE id=? AND case_id=?',(cursor['parent_id'],case_id)).fetchone() if cursor['parent_id'] else None
    if ancestors:
        description+='\nPrior operator refinements (latest explicit request takes precedence):\n'+'\n'.join(reversed(ancestors))
    description+='\nLatest operator refinement (not witness testimony; supersedes conflicting earlier directions):\n'+request.instruction
    description+='\nPreserve remaining requested characteristics where possible. Text-only regeneration; visual identity preservation is not guaranteed.'
    if enforce_limit and len(description)>2500:
        raise HTTPException(422,f'Prompt is {len(description)}/2500 characters. Nothing was truncated. Reduce optional requests explicitly.')
    data=json.loads(snapshot);data.update(_parent_id=request.parent_id,_refinement=request.instruction,_workspace='refinement')
    return description,style,json.dumps(data,ensure_ascii=False)

def refinement_preview(case_id,request):
    with connection() as con:
        description,style,_=refinement_input(con,case_id,request,enforce_limit=False)
    return {'description':description,'length':len(description),'limit':2500,'over_limit':len(description)>2500,'style':style,'mode':'prompt_regeneration'}

def previous_request(case_id,request):
    with connection() as con:
        existing=con.execute('SELECT * FROM refinement_requests WHERE request_key=?',(request.request_key,)).fetchone()
        if existing:
            if existing['case_id']!=case_id or existing['payload']!=request.model_dump_json():
                raise HTTPException(409,'Request key already used for different inputs')
            return existing['job_id']
