import { useState } from 'react'
import { downloadUrl, imageUrl } from '../api/witnesstrace'
import SketchViewer from '../components/sketch/SketchViewer'
import { navigate } from '../lib/router'
import { useApp } from '../state/AppContext'
import { CharacterLab, Refinement, RevisionList, Deliverables } from './WitnessTools'
import './witness.css'

function CaseControls({ wt }) {
  const [title, setTitle] = useState('')
  const [synthetic, setSynthetic] = useState(true)
  return <section className="panel"><div className="panel__head"><h2 className="panel__title">WitnessTrace cases</h2></div><div className="panel__body wt-fields">
    <p role="status">{wt.connection ? `Connected · Codex CLI ${wt.connection.codex_installed ? 'installed' : 'unavailable'}` : 'Backend not connected'}</p>
    <button className="btn btn--sm" onClick={wt.reconnect} disabled={wt.busy}>Reconnect / reload cases</button>
    <label className="label" htmlFor="wt-case">Select case</label>
    <select id="wt-case" value={wt.record?.id || ''} disabled={wt.busy} onChange={e => e.target.value && wt.select(e.target.value)}><option value="">Choose a case</option>{wt.cases.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}</select>
    <form onSubmit={async e => { e.preventDefault(); const saved = await wt.create(title, synthetic); if (saved) { setTitle(''); navigate('new') } }} className="wt-fields">
      <label htmlFor="wt-title" className="label">New case title</label><input id="wt-title" required maxLength={120} value={title} onChange={e => setTitle(e.target.value)} />
      <label><input type="checkbox" checked={synthetic} onChange={e => setSynthetic(e.target.checked)} /> Synthetic fictional case</label><button className="btn btn--primary" disabled={wt.busy || !title.trim()}>Create case</button>
    </form>
    {wt.error && <p className="alert alert--error" role="alert">{wt.error}</p>}
  </div></section>
}

export function WitnessWorkspace() {
  const { wt } = useApp()
  return <div className="workspace wt-workspace"><section className="hero panel panel--corners"><div className="hero__text"><span className="label label--cyan">Revelio · WitnessTrace</span><h2 className="hero__title">From witness description<br />to forensic sketch.</h2><p className="hero__lead">Create a case, preserve the original account and explicitly request a Codex composite. A composite is not proof of identity.</p><button className="btn btn--primary" onClick={() => navigate('new')}>Open composite studio</button></div></section><section className="stats"><div className="stat panel"><span className="label">Saved cases</span><strong className="stat__value mono">{wt.connection ? wt.cases.length : '—'}</strong></div></section><CaseControls wt={wt} />{wt.record && <section className="panel"><div className="panel__body wt-fields"><h2>{wt.record.title}</h2><p>Generation: {wt.job?.status || 'idle'} · {wt.record.versions.length} saved revisions</p><RevisionList /><details><summary>Recent case activity</summary>{wt.record.events?.slice(-10).reverse().map((event, index) => <p className="mono wt-id" key={index}>{event.created_at} · {event.kind || event.type} · {event.detail}</p>)}</details></div></section>}</div>
}

export default function WitnessStudio() {
  const { wt } = useApp()
  const { record, job } = wt
  const [text, setText] = useState('')
  const [clarification, setClarification] = useState('')
  const [source, setSource] = useState('operator')
  const original = record?.statements.find(s => s.kind === 'original')?.text || ''
  const version = record?.versions.find(v => v.id === record.selected_version_id) || record?.versions.at(-1)
  const pending = job?.status === 'working'
  return <div className="studio wt-studio"><div className="studio__head"><div className="studio__ident"><h2>{record?.title || 'New Sketch'}</h2><span className="mono faint wt-id">{record?.id || 'Select or create a synthetic case'}</span></div><span className="tag">Codex CLI · explicit generation</span></div>
    <div className="studio__grid"><div className="studio__input"><CaseControls wt={wt} />
      {record && <section className="panel" key={record.id}><div className="panel__head"><h2 className="panel__title">Witness description</h2></div><div className="panel__body wt-fields">
        <label htmlFor="wt-description" className="label">{record.frozen_at ? 'Original testimony · immutable' : 'Original testimony · save once'}</label>
        <textarea id="wt-description" rows={8} readOnly={!!record.frozen_at} maxLength={1800} value={record.frozen_at ? original : text} onChange={e => setText(e.target.value)} />
        {!record.frozen_at && <button className="btn" disabled={wt.busy || text.trim().length < 10} onClick={() => wt.freeze(text)}>Save original testimony</button>}
        {record.frozen_at && <><label htmlFor="wt-clarify" className="label">Append sourced clarification</label><textarea id="wt-clarify" rows={3} maxLength={1800} value={clarification} onChange={e => setClarification(e.target.value)} /><select aria-label="Clarification source" value={source} onChange={e => setSource(e.target.value)}><option value="operator">Operator</option><option value="witness">Witness</option></select><button className="btn" disabled={wt.busy || pending || !clarification.trim()} onClick={async () => { await wt.clarify(clarification, source) }}>Add clarification</button></>}
        <button className="btn btn--primary" onClick={wt.generate} disabled={!record.frozen_at || wt.busy || pending || !wt.connection?.codex_installed}>{wt.busy ? 'Submitting…' : pending ? 'Generation running…' : 'Generate composite'}</button>
        <p className="faint">Original account: 1,800 characters maximum. Complete generation prompt: 2,500. Generation is prompt-based; identity consistency is not guaranteed.</p>
      </div></section>}
    </div><div className="studio__center"><SketchViewer src={version ? imageUrl(version) : null} kind="ai" label={record?.title || 'Composite preview'} sublabel={version?.id} loading={pending} error={wt.error} onDownload={() => { if (version) window.location.assign(downloadUrl(record.id, version.id)) }} meta={version ? [['Revision', version.id], ['SHA-256', version.sha256]] : []} empty={<p>{pending ? 'Codex is working. You can navigate away and return.' : 'Save a witness description and explicitly generate a composite.'}</p>} />
      <section className="panel"><div className="panel__body" role="status" aria-live="polite">{job ? `${job.status === 'complete' && !version ? 'Verifying saved output' : job.status} · ${job.message}` : 'No generation submitted in this case.'}</div></section>
    </div><aside className="studio__side panel"><div className="panel__head"><h2 className="panel__title">Saved revisions</h2></div><div className="panel__body wt-fields"><RevisionList /></div></aside></div>
    {record && <div className="wt-tools-grid"><div><CharacterLab key={record.id} /><Refinement /><Deliverables /></div></div>}
  </div>
}
