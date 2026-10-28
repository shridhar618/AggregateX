import { useEffect, useRef, useState } from 'react'
import { witness, imageUrl, downloadUrl } from '../api/witnesstrace'
import { useApp } from '../state/AppContext'
import { applyTheme, getStoredTheme } from '../lib/theme'
import { navigate } from '../lib/router'
import CompareSlider from '../components/sketch/CompareSlider'

const empty = () => ({ value: null, confidence: 'unknown', source: 'operator', quote: '' })
const clone = value => structuredClone(value)
const key = () => crypto.randomUUID().replaceAll('-', '')
const call = (record, suffix, body, method) => witness.operation(`/api/cases/${record.id}${suffix}`, body, method)

export function RevisionList() {
  const { wt } = useApp()
  const r = wt.record
  return <div className="wt-fields">{r?.versions.map((v, i) => <div key={v.id} className="wt-revision"><img src={imageUrl(v)} alt={`Revision ${i + 1}`} loading="lazy" /><div><button className="btn btn--sm" disabled={wt.busy} aria-pressed={r.selected_version_id === v.id} onClick={() => wt.update(() => call(r, '/selection', { version_id: v.id }))}>Select V{i + 1}</button><button className="btn btn--sm" disabled={wt.busy} onClick={() => wt.update(() => call(r, '/selection', { version_id: v.id, preferred: true }))}>{r.preferred_version_id === v.id ? '★ Preferred' : 'Set preferred'}</button><p className="mono wt-id">{v.workspace} · {v.id}<br />Parent: {v.parent_id || 'original'}<br />SHA-256: {v.sha256}</p><a href={imageUrl(v)} target="_blank" rel="noreferrer">Full resolution</a> · <a href={downloadUrl(r.id, v.id)} download>PNG</a></div></div>)}</div>
}

export function CharacterLab() {
  const { wt } = useApp()
  const r = wt.record
  const [groups, setGroups] = useState([])
  const [draft, setDraft] = useState(() => clone(r.draft))
  const [undo, setUndo] = useState([])
  const [review, setReview] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { let active = true; witness.operation('/api/lab-schema').then(s => { if (active) setGroups(s.groups) }).catch(e => { if (active) setError(e.message) }); return () => { active = false } }, [])
  const change = next => { setUndo(u => [...u.slice(-29), clone(draft)]); setDraft(next); setReview(null) }
  const edit = (f, a) => { const next = clone(draft); next[f.shared ? 'attributes' : 'lab'][f.key] = a; change(next) }
  const save = async () => {
    const saved = await call(r, '', { revision: r.revision, draft }, 'PUT')
    return saved
  }
  return <section className="panel"><div className="panel__head"><h2 className="panel__title">Character Lab · 45 attributes</h2></div><div className="panel__body wt-fields">
    <p>Seven groups. Unknown stays unspecified. Controls are relative prompt requests, not measurements. Only Update Preview starts generation.</p>
    <label>Output style<select value={draft.style} onChange={e => change({ ...draft, style: e.target.value })}><option value="forensic">Forensic sketch</option><option value="portrait">Realistic illustration</option></select></label>
    <label>Framing<select value={draft.view} onChange={e => change({ ...draft, view: e.target.value })}>{['Portrait', '16:9', 'Upper Body'].map(v => <option key={v}>{v}</option>)}</select></label>
    {groups.map(group => <details key={group.id}><summary>{group.label} · {group.fields.length}</summary><button className="btn btn--sm" onClick={() => { const next = clone(draft); group.fields.forEach(f => { next[f.shared ? 'attributes' : 'lab'][f.key] = empty() }); change(next) }}>Reset group to Unknown</button>{group.fields.map(f => {
      const a = draft[f.shared ? 'attributes' : 'lab'][f.key] || empty()
      return <div className="wt-lab-field" key={f.key}><label htmlFor={'trait-' + f.key}>{f.label} <span className="mono">{a.value ?? 'Unknown'}</span></label>
        {f.kind === 'select' ? <select id={'trait-' + f.key} value={a.value || ''} onChange={e => edit(f, { ...a, value: e.target.value || null, confidence: e.target.value ? 'tentative' : 'unknown' })}><option value="">Unknown / not provided</option>{f.options.map(o => <option key={o}>{o}</option>)}</select> : <><input id={'trait-' + f.key} type={f.kind === 'slider' ? 'range' : f.kind === 'age' ? 'number' : 'text'} min={f.kind === 'age' ? 18 : 0} max={f.kind === 'age' ? 100 : 100} maxLength={100} value={a.value ?? (f.kind === 'slider' ? 50 : '')} onChange={e => edit(f, { ...a, value: e.target.value || null, confidence: e.target.value ? 'tentative' : 'unknown' })} /><button className="btn btn--sm" onClick={() => edit(f, empty())}>Unknown</button>{f.kind === 'slider' && <small>{f.low} → {f.high} · 50 neutral</small>}</>}
        <label>Recollection<select aria-label={f.label + ' confidence'} value={a.confidence} disabled={a.value === null} onChange={e => edit(f, { ...a, confidence: e.target.value })}>{a.value === null && <option value="unknown">Unknown</option>}<option value="tentative">Tentative</option><option value="certain">Certain</option></select></label>
        <label>Source<select aria-label={f.label + ' source'} value={a.source} disabled={a.value === null} onChange={e => edit(f, { ...a, source: e.target.value })}><option value="operator">Operator</option><option value="witness">Witness quote</option></select></label>{a.source === 'witness' && <label>Exact recorded quote<input value={a.quote} maxLength={1800} onChange={e => edit(f, { ...a, quote: e.target.value })} /></label>}
      </div>
    })}</details>)}
    <button className="btn" disabled={!undo.length} onClick={() => { setDraft(undo.at(-1)); setUndo(undo.slice(0, -1)); setReview(null) }}>Undo lab edit</button>
    <button className="btn" disabled={wt.busy} onClick={() => wt.update(save)}>Save draft</button>
    <button className="btn" onClick={async () => { try { setReview(await call(r, '/prompt-preview', draft)); setError('') } catch (e) { setError(e.message) } }}>Review prompt</button>
    {review && <><pre className="wt-prompt">{review.description}</pre><p>{review.length} / {review.limit} characters{review.over_limit ? ' · Too long' : ''}</p></>}
    <button className="btn btn--primary" disabled={wt.busy || !review || review.over_limit || wt.job?.status === 'working'} onClick={() => wt.update(async () => { const saved = await save(); const handle = await witness.submitGeneration({ description: review.description, style: review.style, case_id: r.id, case_revision: saved.revision, workspace: 'lab' }); wt.follow(handle); return handle })}>Update Preview</button>
    {error && <p role="alert">{error}</p>}
  </div></section>
}

export function Refinement() {
  const { wt } = useApp(); const r = wt.record
  const [instruction, setInstruction] = useState(''); const [review, setReview] = useState(null); const [error, setError] = useState('')
  const parent = r.selected_version_id || r.versions.at(-1)?.id
  const payload = () => ({ parent_id: parent, instruction, draft: r.draft, revision: r.revision, request_key: key() })
  return <section className="panel"><div className="panel__head"><h2 className="panel__title">Refine selected revision</h2></div><div className="panel__body wt-fields"><p>Text regeneration creates an immutable child revision. Visual identity can drift.</p><textarea aria-label="Refinement instructions" maxLength={1800} value={instruction} onChange={e => { setInstruction(e.target.value); setReview(null) }} /><button className="btn" disabled={!parent || !instruction.trim()} onClick={async () => { try { const body = payload(); const prompt = await call(r, '/refinement-preview', body); setReview({ body, prompt }); setError('') } catch (e) { setError(e.message) } }}>Review refinement prompt</button>{review && <pre className="wt-prompt">{review.prompt.description}</pre>}<button className="btn btn--primary" disabled={wt.busy || wt.job?.status === 'working' || !review || review.prompt.over_limit || review.body.parent_id !== parent || review.body.revision !== r.revision} onClick={() => wt.update(async () => { const handle = await call(r, '/refine', { ...review.body, reviewed_prompt: review.prompt.description }); wt.follow(handle); setReview(null); return handle })}>Generate refinement</button>{error && <p role="alert">{error}</p>}</div></section>
}

export function ProcessingTools() {
  const { wt } = useApp(); const [tool, setTool] = useState('sketch'); const [opened, setOpened] = useState(false); const frame = useRef(null)
  const open = name => { if (opened && frame.current?.contentWindow) { const w = frame.current.contentWindow; w.document.documentElement.dataset.tool = name; w.selectTab?.(name); } else { setTool(name); setOpened(true) } }
  const id = wt.record.id
  useEffect(() => {
    const guard = e => {
      const w = frame.current?.contentWindow
      if ((w?.Sketchpad?.isDirty() || w?.Enhance?.isDirty()) && !window.confirm('Discard unsaved image edits and switch cases?')) e.preventDefault()
    }
    window.addEventListener('witness-before-case', guard)
    return () => window.removeEventListener('witness-before-case', guard)
  }, [id])
  return <section className="panel wt-process"><div className="panel__head"><h2 className="panel__title">Image editing</h2></div><div className="panel__body wt-fields"><p>The preserved editing engine keeps layers and exact enhancement pixels. Canvas state stays open during navigation. Save edits to retain them after refresh or case switching.</p><div><button className="btn" onClick={() => { open('sketch') }}>Digital Sketchpad</button> <button className="btn" onClick={() => { open('enhance') }}>Enhance</button> <button className="btn" onClick={wt.refresh}>Reload saved revisions</button></div>{opened && <iframe ref={frame} className="wt-tool-frame" title="WitnessTrace image editing" src={`/wt-api/tools/index.html?case=${id}&tool=${tool}`} />}</div></section>
}

export function Deliverables() {
  const { wt } = useApp(); const r = wt.record
  const [reports, setReports] = useState([]); const [views, setViews] = useState(null); const [error, setError] = useState('')
  const selected = r.selected_version_id || r.versions.at(-1)?.id
  const run = async op => { try { setError(''); return await op() } catch (e) { setError(e.message) } }
  return <section className="panel"><div className="panel__head"><h2 className="panel__title">Multi-view & case reports</h2></div><div className="panel__body wt-fields"><p>AI-generated 2D interpretations, not geometrically accurate reconstructed 3D models.</p>
    <button className="btn" onClick={() => run(async () => setViews(await call(r, '/multiview')))}>Load saved angle sheets</button>
    {views?.requests.map(view => <div key={view.job_id}><p className="mono wt-id">{view.created_at} · {view.status} · Parent {view.parent_id}</p>{view.image_url && <a href={imageUrl({id: view.job_id, image_url: view.image_url})} target="_blank" rel="noreferrer"><img className="wt-sheet-thumb" src={imageUrl({id: view.job_id, image_url: view.image_url})} alt="Saved 2D concept sheet" /></a>}</div>)}
    <p>Angle generation and reviewed crops are available in the preserved multi-view workspace below.</p>
    <details><summary>Multi-view workspace</summary><iframe className="wt-tool-frame" title="WitnessTrace multi-view and reports" src={`/wt-api/tools/index.html?case=${r.id}&tool=multiview`} /></details>
    {selected && <p><a href={downloadUrl(r.id, selected)} download>Download PNG</a> · <a href={`/wt-api/api/cases/${r.id}/versions/${selected}/export.json`} download>Download case JSON</a></p>}
    <button className="btn" disabled={!selected || wt.busy} onClick={() => run(async () => { await call(r, '/reports', { version_id: selected, request_key: key() }); setReports(await call(r, '/reports')) })}>Create PDF report</button><button className="btn" onClick={() => run(async () => setReports(await call(r, '/reports')))}>Load persisted reports</button>
    {reports.map(report => <div key={report.id} className="wt-fields"><span className="mono wt-id">{report.id} · {report.created_at}</span>{['pdf', 'json', 'png'].map(ext => <a key={ext} href={`/wt-api/api/cases/${r.id}/reports/${report.id}/${ext}`} download>Download {ext.toUpperCase()}</a>)}</div>)}{error && <p role="alert">{error}</p>}
  </div></section>
}

export function WitnessLibrary() {
  const { wt } = useApp(); const [search, setSearch] = useState(''); const [records, setRecords] = useState({})
  useEffect(() => {
    const controller = new AbortController()
    Promise.allSettled(wt.cases.map(c => witness.getCase(c.id, controller.signal))).then(results => {
      if (!controller.signal.aborted) setRecords(Object.fromEntries(results.filter(r => r.status === 'fulfilled').map(r => [r.value.id, r.value])))
    })
    return () => controller.abort()
  }, [wt.cases])
  return <div className="wt-fields"><div className="toolbar panel"><h2>Case library</h2><input aria-label="Search cases" placeholder="Search case titles" value={search} onChange={e => setSearch(e.target.value)} /></div><div className="library__grid">{wt.cases.filter(c => c.title.toLowerCase().includes(search.toLowerCase())).map(c => {
    const record = records[c.id]; const v = record?.versions.find(v => v.id === record.selected_version_id) || record?.versions.at(-1)
    return <article className="lib-card panel" key={c.id}><button className="lib-card__img" onClick={() => wt.select(c.id)} aria-label={'Select ' + c.title}>{v ? <img src={imageUrl(v)} alt={'Saved composite for ' + c.title} loading="lazy" /> : <span>{record ? 'No saved image' : 'Loading saved image…'}</span>}</button><div className="lib-card__body"><h3 className="lib-card__title">{c.title}</h3><p className="lib-card__meta mono wt-id">{c.id}</p><p>{c.synthetic ? 'Synthetic' : 'Witness case'} · {c.frozen_at ? 'Original frozen' : 'Original draft'} · {record?.versions.length ?? '…'} revisions</p><p className="mono">{c.created_at}</p><div className="lib-card__actions"><button className="btn btn--sm" disabled={wt.busy} onClick={() => wt.select(c.id)} aria-pressed={c.id === wt.record?.id}>Select case</button><button className="btn btn--sm" onClick={async () => { await wt.select(c.id); navigate('new') }}>Open studio</button></div></div></article>
  })}</div>{wt.record && <><h3>{wt.record.title}</h3><RevisionList /><details><summary>Persisted case activity</summary>{wt.record.events.map(event => <p className="mono wt-id" key={event.id}>{event.created_at} · {event.kind} · {event.detail}</p>)}</details><Deliverables /></>}</div>
}

export function WitnessCompare() {
  const { wt } = useApp(); const versions = wt.record?.versions || []
  const [a, setA] = useState(''); const [b, setB] = useState(''); const [split, setSplit] = useState(false)
  const before = versions.find(v => v.id === a) || versions.at(-2); const after = versions.find(v => v.id === b) || versions.at(-1)
  return <section className="panel"><div className="panel__body wt-fields"><h2>Compare saved revisions</h2>{['Before', 'After'].map((label, i) => <label key={label}>{label}<select value={(i ? after : before)?.id || ''} onChange={e => (i ? setB : setA)(e.target.value)}>{versions.map((v, n) => <option value={v.id} key={v.id}>V{n + 1} · {v.workspace} · {v.id.slice(0, 8)}</option>)}</select></label>)}<button className="btn" onClick={() => setSplit(!split)}>{split ? 'Before / after slider' : 'Side by side'}</button>{before && after ? split ? <div className="wt-side-by-side"><img src={imageUrl(before)} alt="Before revision" /><img src={imageUrl(after)} alt="After revision" /></div> : <CompareSlider before={imageUrl(before)} after={imageUrl(after)} beforeLabel="Before" afterLabel="After" /> : <p>Select a case with at least two saved revisions.</p>}<RevisionList /></div></section>
}

export function WitnessSettings() {
  const { wt, prefs, updatePrefs } = useApp(); const [theme, changeTheme] = useState(getStoredTheme)
  return <section className="panel"><div className="panel__body wt-fields"><h2>Application settings</h2><label>Interface theme<select value={theme} onChange={e => changeTheme(applyTheme(e.target.value))}><option value="dark">Dark</option><option value="light">Light</option></select></label><label><input type="checkbox" checked={prefs.reduceMotion} onChange={e => updatePrefs({ reduceMotion: e.target.checked })} /> Reduce motion</label><button className="btn" onClick={wt.reconnect}>Check backend health</button><p>Codex CLI: {wt.connection?.codex_installed ? 'installed' : 'unavailable / disconnected'}. Installation does not establish current authentication or quota.</p><pre className="wt-prompt">{JSON.stringify(wt.connection, null, 2)}</pre><p>WitnessTrace owns cases, testimony, images and reports in its configured SQLite and file store. Revelio owns local account sessions and interface preferences. Signed-in users share this local collection.</p>{wt.error && <p role="alert">{wt.error}</p>}</div></section>
}
