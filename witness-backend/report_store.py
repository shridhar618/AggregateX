"""Immutable persisted-case report bundles. No browser drafts, AI calls or auth data."""
import hashlib
import html
import io
import json
import uuid
from pathlib import Path
from fastapi import HTTPException
from PIL import Image,ImageOps
from pydantic import Field
import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image as PDFImage,Table,TableStyle,Preformatted,PageBreak,KeepTogether
import case_store as store
from lab_schema import FIELDS,phrase
from sketch_store import owned

TITLE='WitnessTrace AI — Illustrative Facial Composite Report'
DISCLAIMER='This composite is a computer-generated investigative illustration, not a verified photograph or proof of identity. It is not proof of guilt. Uploaded sources and local edits have the provenance recorded below; no missing facial information is authenticated.'
FONT_DIR=Path(reportlab.__file__).parent/'fonts'
pdfmetrics.registerFont(TTFont('WT',str(FONT_DIR/'Vera.ttf')))
pdfmetrics.registerFont(TTFont('WTBold',str(FONT_DIR/'VeraBd.ttf')))

class Request(store.Strict):
    version_id: str = Field(pattern='^[0-9a-f]{32}$')
    request_key: str = Field(pattern='^[0-9a-f]{32}$')


def png_export(case_id,version_id):
    with store.connection() as con:owned(con,case_id,version_id)
    path=store.image_path(version_id)
    try:
        with Image.open(path) as image:
            if image.width*image.height>16_000_000:raise HTTPException(422,'Selected image exceeds the 16-megapixel report export budget. Its original download remains available.')
            image.load();result=ImageOps.exif_transpose(image).convert('RGBA');result.info.clear()
            out=io.BytesIO();result.save(out,format='PNG');return out.getvalue()
    except (OSError,ValueError,Image.DecompressionBombError):
        raise HTTPException(409,'Selected image cannot be decoded for export.') from None


def attributes(draft):
    validated=store.Draft.model_validate(draft)
    fields={**validated.attributes,**validated.lab};rows=[]
    for key,field in FIELDS.items():
        a=fields[key];unknown=a.value is None
        rows.append({'key':key,'label':field['label'],'value':a.value,'interpretation':'Unknown' if unknown else phrase(key,a.value),'uncertainty':a.confidence,'source':a.source,'quote':a.quote,'status':'Unknown / not provided' if unknown else ('Witness-reported' if a.source=='witness' else 'Operator direction')+'; '+a.confidence+' (subjective)'})
    return rows


def public_version(v):
    allowed=['id','parent_id','created_at','sha256','style','workspace','generation_job_id','mode','outcome','width','height','creation_kind','source','modified_illustration','generation_route','image_reference_used','refinement_prompt','generation_prompt','adjustments','engine','source_id','source_filename','source_format','editing_metadata','source_revision','panel_status']
    result={key:v[key] for key in allowed if key in v}
    if 'editing_metadata' in result:
        result['editing_metadata']={k:value for k,value in result['editing_metadata'].items() if k in ['source_version_id','operation_count','tools']}
    if 'source_revision' in result:result['source_revision']={k:value for k,value in result['source_revision'].items() if k in ['id','sha256','created_at','style','mode']}
    return result


def snapshot(case_id,version_id,report_id,created_at,png):
    record=store.get(case_id)
    selected=next((v for v in record['versions'] if v['id']==version_id),None)
    if not selected:raise HTTPException(404,'Selected version does not belong to this case.')
    data={'schema_version':1,'report_id':report_id,'report_created_at':created_at,'heading':TITLE,'disclaimer':DISCLAIMER,'case':{k:record[k] for k in ['id','title','synthetic','created_at','frozen_at','revision','selected_version_id','preferred_version_id']},'statements':record['statements'],'selected_version':public_version(selected),'selected_image_export':{'format':'PNG','sha256':hashlib.sha256(png).hexdigest(),'source_image_sha256':selected['sha256']},'persisted_case_settings':record['draft'],'selected_attribute_snapshot':selected.get('attribute_snapshot') or record['draft'],'attribute_summary':attributes(selected.get('attribute_snapshot') or record['draft']),'revision_history':[],'refinement_history':record['refinements'],'generation_jobs':[{k:j[k] for k in ['id','status','message','created_at']} for j in record['jobs']],'case_events':record['events'],'notices':['Persisted records only. Unsaved browser changes are excluded.','Unknown attributes remain unknown; recollection labels are subjective, not forensic probabilities.','Local artist edits, local adjustments, uploaded sources and AI-generated interpretations are distinct.','Concept views are 2D interpretations, not a geometrically accurate 3D reconstruction.']}
    for v in record['versions']:
        item=public_version(v)
        try:
            path=store.image_path(v['id']);item['integrity_status']='verified at export'
            with Image.open(path) as im:item['width'],item['height']=ImageOps.exif_transpose(im).size
        except (HTTPException,OSError,ValueError):item['integrity_status']='unavailable or integrity check failed'
        data['revision_history'].append(item)
    with store.connection() as con:
        data['multi_view_requests']=[dict(r) for r in con.execute('SELECT m.job_id,m.parent_id,m.created_at,j.status,j.description,j.style FROM multiview_requests m JOIN jobs j ON j.id=m.job_id WHERE m.case_id=? ORDER BY m.created_at',(case_id,))]
        data['panel_reviews']=[{'id':r['id'],'version_id':r['version_id'],'created_at':r['created_at'],'source_sha256':r['source_sha256'],'panels':json.loads(r['panels']),'note':r['note'],'source':'operator visual review, not witness testimony'} for r in con.execute('SELECT * FROM multiview_layouts WHERE case_id=? ORDER BY created_at',(case_id,))]
    return data


def paragraph(text,style):return Paragraph(html.escape(str(text)).replace('\n','<br/>'),style)


def make_pdf(data,png):
    # Fail clearly on unsupported glyphs instead of silently changing witness text.
    font=pdfmetrics.getFont('WT');coverage=font.face.charToGlyph
    texts=[data['case']['title']]+[s['text'] for s in data['statements']]+[r['quote']+str(r['value'] or '') for r in data['attribute_summary']]
    if any(ord(char)>31 and ord(char) not in coverage for text in texts for char in text):
        raise HTTPException(422,'This report contains characters not supported by the embedded PDF font. Original records are unchanged; use the JSON export or a supported report font.')
    output=io.BytesIO();navy=colors.HexColor('#101b30');blue=colors.HexColor('#345fa8');muted=colors.HexColor('#52637b')
    body=ParagraphStyle('Body',fontName='WT',fontSize=8,leading=12,textColor=navy,spaceAfter=7,wordWrap='CJK')
    small=ParagraphStyle('Small',parent=body,fontSize=6.7,leading=9,spaceAfter=3)
    heading=ParagraphStyle('Heading',parent=body,fontName='WTBold',fontSize=12,leading=16,textColor=blue,spaceBefore=12,spaceAfter=8)
    exact=ParagraphStyle('Exact',parent=body,fontSize=8.2,leading=12,leftIndent=7,borderPadding=8,backColor=colors.HexColor('#f1f4f9'))
    def recorded(text):
        lines=[]
        for line in text.split('\n'):
            current=''
            for char in line:
                if current and pdfmetrics.stringWidth(current+char,'WT',exact.fontSize)>500:
                    lines.append(current);current=''
                current+=char
            lines.append(current)
        return Preformatted('\n'.join(lines),exact,dedent=0)
    def frame(canvas,doc):
        canvas.saveState();w,h=A4;canvas.setFillColor(navy);canvas.rect(0,h-77,w,77,fill=1,stroke=0);canvas.setFillColor(colors.white);canvas.setFont('WTBold',13);canvas.drawString(36,h-29,TITLE);canvas.setFont('WT',8);canvas.drawString(36,h-49,'CASE '+data['case']['id']+'  |  '+data['report_created_at']);canvas.setStrokeColor(blue);canvas.line(36,39,w-36,39);canvas.setFont('WT',7);canvas.setFillColor(muted);canvas.drawString(36,26,'Illustrative composite · not verified identity · not proof of guilt');canvas.drawRightString(w-36,26,'Page '+str(doc.page));canvas.restoreState()
    document=SimpleDocTemplate(output,pagesize=A4,rightMargin=36,leftMargin=36,topMargin=96,bottomMargin=53,title=TITLE,author='WitnessTrace AI',subject='Illustrative facial composite; provenance and uncertainty')
    story=[]
    story.append(paragraph(data['case']['title']+(' · SYNTHETIC DEMO' if data['case']['synthetic'] else ' · Witness case'),heading))
    story.append(paragraph(DISCLAIMER,body));v=data['selected_version'];story.append(paragraph('Selected version: '+v['id']+'\nParent: '+str(v.get('parent_id') or 'None')+'\nMethod: '+v.get('mode','legacy Codex generation')+'\nGeneration / save time: '+v['created_at'],body))
    with Image.open(io.BytesIO(png)) as image:w,h=image.size
    scale=min(440/w,335/h);story.append(PDFImage(io.BytesIO(png),width=w*scale,height=h*scale));story.append(Spacer(1,7))
    story.append(paragraph('Recorded source SHA-256: '+v['sha256']+'\nPNG export SHA-256: '+data['selected_image_export']['sha256'],small))
    story.append(paragraph('Original witness description — exact recorded text',heading))
    original=next(s for s in data['statements'] if s['kind']=='original')
    story.append(paragraph('Source: '+original['source']+' · Frozen: '+str(data['case']['frozen_at'] or 'Not frozen; synthetic operator demo'),small))
    story.append(recorded(original['text']))
    story.append(paragraph('Subsequent sourced clarifications',heading))
    notes=[s for s in data['statements'] if s['kind']!='original']
    if not notes:story.append(paragraph('No subsequent clarifications recorded.',body))
    for note in notes:
        story.append(paragraph(note['source']+' · '+note['created_at'],small));story.append(recorded(note['text']))
    story.append(paragraph('Structured characteristics — requested attributes, not verified image findings',heading))
    story.append(paragraph('Unknown and uncertain values are retained. Operator directions and subjective witness recollection are not independently verified. Relative sliders are not anatomical measurements or probabilities. The selected revision snapshot is shown; current persisted case settings are separately included in JSON.',body))
    rows=[[paragraph(x,small) for x in ['Attribute','Recorded value / direction','Source / uncertainty','Exact witness quote']]]
    for r in data['attribute_summary']:rows.append([paragraph(r['label'],small),paragraph('Unknown' if r['value'] is None else str(r['value'])+' · '+r['interpretation'],small),paragraph(r['status'],small),paragraph(r['quote'] or '—',small)])
    table=Table(rows,colWidths=[110,153,125,135],repeatRows=1,hAlign='LEFT');table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dfe8f6')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f4f6fa')]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),6),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#c7d1df'))]));story.append(table)
    current_rows=attributes(data['persisted_case_settings'])
    selected_rows={row['key']:row for row in data['attribute_summary']}
    changed=[row for row in current_rows if row!=selected_rows[row['key']]]
    if changed:
        story.append(paragraph('Current saved draft changes since selected revision',heading))
        story.append(paragraph('These persisted requests are not asserted to appear in the selected image.',body))
        for row in changed:story.append(paragraph(row['label']+': '+('Unknown' if row['value'] is None else str(row['value']))+' · '+row['status']+' · Quote: '+(row['quote'] or 'None'),small))
    if data['persisted_case_settings'].get('note'):
        story.append(paragraph('Persisted pending note — not an appended witness statement',heading));story.append(recorded(data['persisted_case_settings']['note']))
    story.append(paragraph('Revision history, lineage and integrity',heading));rows=[[paragraph(x,small) for x in ['Version / parent','Method / UTC creation','Dimensions / outcome','SHA-256 / integrity']]]
    for r in data['revision_history']:
        rows.append([paragraph(r['id']+'\nParent: '+str(r.get('parent_id') or 'None'),small),paragraph(r.get('mode','legacy Codex generation')+'\n'+r['created_at'],small),paragraph(str(r.get('width','?'))+' × '+str(r.get('height','?'))+'\n'+r.get('outcome','complete'),small),paragraph(r['sha256']+'\n'+r['integrity_status'],small)])
    t=Table(rows,colWidths=[151,135,75,162],repeatRows=1,hAlign='LEFT');t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dfe8f6')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f4f6fa')]),('BOTTOMPADDING',(0,0),(-1,-1),7),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#c7d1df'))]));story.append(t)
    story.append(paragraph('Local modifications and explicit refinement requests',heading))
    for r in data['revision_history']:
        details=[]
        if r.get('editing_metadata'):details.append('Artist edit: '+json.dumps(r['editing_metadata'],ensure_ascii=False))
        if r.get('adjustments'):details.append('Local adjustment parameters: '+json.dumps(r['adjustments'],ensure_ascii=False))
        if r.get('refinement_prompt'):details.append('Operator refinement: '+r['refinement_prompt'])
        if r.get('mode')=='concept_multiview':details.append('Experimental 2D multi-angle interpretation. Text-only; not a 3D mesh or guaranteed identity match.')
        if r.get('source_filename'):details.append('Uploaded source: '+r['source_filename']+'; raw bytes retained.')
        if details:story.append(paragraph(r['id']+'\n'+'\n'.join(details),small))
    story.append(paragraph('Generation and layout provenance',heading));story.append(paragraph('AI route: existing authenticated Codex CLI → built-in image_gen. No source pixels are supplied. Local canvas saves, pixel adjustments and uploads are not AI jobs.',body))
    for req in data['multi_view_requests']:story.append(paragraph(req['job_id']+' · '+req['status']+' · parent '+req['parent_id']+'\n'+req['description'],small))
    for review in data['panel_reviews']:story.append(paragraph('Panel review '+review['id']+' · operator · '+review['created_at']+'\n'+json.dumps(review['panels'],ensure_ascii=False)+'\n'+review['note'],small))
    story.append(paragraph('Case timeline',heading))
    for event in data['case_events']:story.append(paragraph(event['created_at']+' · '+event['kind']+' · '+event['detail'],small))
    story.append(paragraph('Limitations and provenance notices',heading))
    for notice in data['notices']:story.append(paragraph('• '+notice,body))
    document.build(story,onFirstPage=frame,onLaterPages=frame)
    return output.getvalue()


def report_dir(case_id,report_id):
    store.identifier(case_id);store.identifier(report_id);root=store.DATA.resolve();path=root/'cases'/case_id/'exports'/report_id
    if not path.resolve().is_relative_to(root/'cases'):raise HTTPException(404,'Invalid export location.')
    return path


def public_report(record):
    manifest=json.loads(record['manifest'])
    return {'id':record['id'],'case_id':record['case_id'],'version_id':record['version_id'],'created_at':record['created_at'],'files':manifest,'preview_url':f"/api/cases/{record['case_id']}/reports/{record['id']}/preview"}


def create(case_id,request):
    signature=hashlib.sha256((case_id+request.version_id).encode()).hexdigest();directory=None;created=False;committed=False
    try:
        with store.connection() as con:
            con.execute('BEGIN IMMEDIATE');owned(con,case_id,request.version_id)
            prior=con.execute('SELECT * FROM report_exports WHERE request_key=?',(request.request_key,)).fetchone()
            if prior:
                if prior['case_id']!=case_id or prior['signature']!=signature:raise HTTPException(409,'Report request key already used for another case/version.')
                return public_report(prior)
            png=png_export(case_id,request.version_id);report_id=uuid.uuid4().hex;timestamp=store.now();data=snapshot(case_id,request.version_id,report_id,timestamp,png)
            payload=json.dumps(data,ensure_ascii=False,indent=2).encode('utf-8');pdf=make_pdf(data,png)
            if not pdf.startswith(b'%PDF-'):raise ValueError('Invalid PDF result')
            directory=report_dir(case_id,report_id);directory.mkdir(parents=True,exist_ok=False);created=True;manifest={}
            for extension,content in [('pdf',pdf),('json',payload),('png',png)]:
                path=directory/('report.'+extension)
                with path.open('xb') as file:file.write(content)
                manifest[extension]={'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content),'url':f'/api/cases/{case_id}/reports/{report_id}/{extension}','filename':f'witnesstrace-{case_id}-{request.version_id}-{report_id}.{extension}'}
            con.execute('INSERT INTO report_exports VALUES(?,?,?,?,?,?,?)',(report_id,case_id,request.version_id,timestamp,request.request_key,signature,json.dumps(manifest)))
            record=con.execute('SELECT * FROM report_exports WHERE id=?',(report_id,)).fetchone();result=public_report(record)
            # Export metadata is separate; no testimony, draft, image revision or witness event is altered.
        committed=True
    finally:
        if created and not committed and directory:
            for path in directory.iterdir():path.unlink()
            directory.rmdir()
    return result


def list_reports(case_id):
    with store.connection() as con:
        store.row(con,case_id);return [public_report(r) for r in con.execute('SELECT * FROM report_exports WHERE case_id=? ORDER BY created_at DESC,id DESC',(case_id,))]


def read_file(case_id,report_id,extension):
    store.identifier(report_id)
    if extension not in {'pdf','json','png'}:raise HTTPException(404,'Unknown export format.')
    with store.connection() as con:
        store.row(con,case_id);record=con.execute('SELECT * FROM report_exports WHERE id=? AND case_id=?',(report_id,case_id)).fetchone()
        if not record:raise HTTPException(404,'Report does not belong to this case.')
        meta=json.loads(record['manifest'])[extension];path=report_dir(case_id,report_id)/('report.'+extension)
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(report_dir(case_id,report_id).resolve()):raise HTTPException(404,'Export file unavailable.')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=meta['sha256']:raise HTTPException(409,'Export integrity check failed.')
        return path,meta


def preview_html(case_id,report_id):
    path,_=read_file(case_id,report_id,'json');data=json.loads(path.read_text());esc=lambda v:html.escape(str(v));version=data['selected_version'];png=f'/api/cases/{case_id}/reports/{report_id}/png?inline=true'
    statements=''.join('<section><h2>'+esc(s['kind'].title()+' · '+s['source'])+'</h2><pre>'+esc(s['text'])+'</pre></section>' for s in data['statements'])
    attrs=''.join('<tr><td>'+esc(r['label'])+'</td><td>'+esc(r['interpretation'])+'</td><td>'+esc(r['status'])+'</td><td>'+esc(r['quote'] or '—')+'</td></tr>' for r in data['attribute_summary'])
    versions=''.join('<tr><td>'+esc(v['id'])+'</td><td>'+esc(v.get('parent_id') or 'None')+'</td><td>'+esc(v.get('mode','legacy Codex generation'))+'</td><td>'+esc(v['sha256'])+'</td></tr>' for v in data['revision_history'])
    return '<!doctype html><html><head><meta charset="utf-8"><title>'+TITLE+'</title><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;background:#f4f6fb;color:#152139;font:13px system-ui}header{padding:24px;background:#101b30;color:#fff}h1{font-size:21px}main{padding:22px;max-width:950px;margin:auto}section{background:#fff;border:1px solid #ccd5e3;border-radius:7px;padding:18px;margin:14px 0}h2{font-size:16px;color:#315a9b}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.7 ui-monospace,monospace}img{max-width:100%;height:340px;object-fit:contain;display:block;margin:auto}table{border-collapse:collapse;width:100%;font-size:10px;table-layout:fixed}td,th{padding:8px;border:1px solid #d2dbe7;overflow-wrap:anywhere;text-align:left;vertical-align:top}th{background:#dfe8f6}p{line-height:1.6;overflow-wrap:anywhere}.notice{padding:14px;border-left:4px solid #4571bc;background:#e7eef9}</style></head><body><header><h1>'+TITLE+'</h1><p>Case '+esc(case_id)+' · '+esc(data['case']['title'])+'<br>Report '+esc(report_id)+' · '+esc(data['report_created_at'])+'</p></header><main><p class="notice">'+esc(DISCLAIMER)+'</p><p>Persisted report snapshot. Unsaved browser changes are excluded. The downloadable PDF also includes modification records, provenance and the case timeline.</p><section><h2>Selected composite · '+esc(version['id'])+'</h2><img alt="Persisted selected image; provenance described below" src="'+png+'"><p>Method: '+esc(version.get('mode','legacy Codex generation'))+' · '+esc(version['created_at'])+'<br>Source SHA-256: '+esc(version['sha256'])+'</p></section>'+statements+'<section><h2>Structured characteristics and uncertainty</h2><table><tr><th>Attribute</th><th>Value / direction</th><th>Source / recollection</th><th>Exact quote</th></tr>'+attrs+'</table></section><section><h2>Revision lineage and integrity</h2><table><tr><th>Version</th><th>Parent</th><th>Method</th><th>SHA-256</th></tr>'+versions+'</table></section></main></body></html>'
