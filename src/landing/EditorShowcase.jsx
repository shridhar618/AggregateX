import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import CompareSlider from '../components/sketch/CompareSlider'
import Icon from '../components/ui/Icon'
import { optionLabel } from '../lib/format'
import { useEngine } from './engine'
import { Reveal, SplitLines } from './motion'

const SEED = 'An adult with an oval face, short dark hair, thick eyebrows, a narrow nose, and a small scar on the left cheek.'
const SLIDERS = [
  ['face_width', 'Face width'],
  ['jaw_width', 'Jaw width'],
  ['eye_spacing', 'Eye spacing'],
  ['nose_width', 'Nose width'],
  ['nose_length', 'Nose length'],
  ['mouth_width', 'Mouth width'],
]

export default function EditorShowcase() {
  const { status, catalog, retry } = useEngine()
  const [profile, setProfile] = useState(null)
  const [current, setCurrent] = useState(null) // { url }
  const [revisions, setRevisions] = useState([]) // [{ n, url, profile }]
  const [compare, setCompare] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const urls = useRef(new Set())
  const timer = useRef(0)
  const started = useRef(false)

  const renderSvg = async (p) => {
    setLoading(true)
    try {
      const r = await api.render(p, 'DEMO')
      const url = URL.createObjectURL(new Blob([r.svg], { type: 'image/svg+xml' }))
      urls.current.add(url)
      setCurrent({ url })
      setError(null)
      return url
    } catch (err) {
      setError(err.message)
      return null
    } finally {
      setLoading(false)
    }
  }

  // Seed the showcase from the demo description once the engine is reachable.
  useEffect(() => {
    if (status !== 'online' || started.current) return
    started.current = true
    api.extract(SEED)
      .then(async (ex) => {
        setProfile(ex.profile)
        const url = await renderSvg(ex.profile)
        if (url) setRevisions([{ n: 1, url, profile: ex.profile }])
      })
      .catch((err) => setError(err.message))
  }, [status])

  useEffect(() => {
    const set = urls.current
    return () => {
      clearTimeout(timer.current)
      set.forEach((u) => URL.revokeObjectURL(u))
    }
  }, [])

  const change = (next) => {
    setProfile(next)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => renderSvg(next), 90)
  }
  const setAdj = (key, v) => {
    const next = structuredClone(profile)
    if (Math.abs(v) < 0.001) delete next.adjustments[key]
    else next.adjustments[key] = v
    change(next)
  }
  const setTrait = (key, value) => {
    const next = structuredClone(profile)
    next.traits[key] = { value, source: 'manual', evidence: null, certainty: 'stated', alternatives: [] }
    change(next)
  }

  const last = revisions[revisions.length - 1]
  const dirty = profile && last && JSON.stringify(last.profile) !== JSON.stringify(profile)
  const saveRevision = () => {
    if (!current || !dirty) return
    setRevisions((rs) => [...rs, { n: rs.length + 1, url: current.url, profile }])
  }
  const reset = () => {
    if (!revisions[0]) return
    setProfile(revisions[0].profile)
    setCurrent({ url: revisions[0].url })
  }

  const traitByKey = Object.fromEntries((catalog?.traits || []).map((t) => [t.key, t]))
  const known = profile ? Object.entries(profile.traits).filter(([, t]) => t.value) : []
  const before = dirty ? last : revisions[revisions.length - 2]
  const hairline = traitByKey.hairline
  const facial = traitByKey.facial_hair

  return (
    <section id="editor" className="lp-section" aria-labelledby="editor-title">
      <div className="lp-shell">
        <div className="lp-section__head lp-section__head--split">
          <div>
            <Reveal><span className="lp-eyebrow">Interactive editor</span></Reveal>
            <SplitLines lines={['Every control', 'redraws the face.']} className="lp-h2" />
            <span id="editor-title" className="sr-only">Interactive editor showcase</span>
          </div>
          <Reveal delay={150}>
            <p className="lp-section__lead">
              A second live instance of the procedural renderer. Move a slider and the composite is redrawn on the local engine in milliseconds.
              The full workspace adds undo and redo, saved revisions, and exports.
            </p>
          </Reveal>
        </div>

        <Reveal y={40} className="lp-editor">
          <div className="lp-editor__bar">
            <span className="lp-editor__dots" aria-hidden="true"><i /><i /><i /></span>
            <span className="lp-mono">RV-DEMO-0002</span>
            <span className="lp-tag lp-tag--procedural">Procedural · not AI</span>
            <span className="lp-mono lp-faint lp-editor__rev">
              {revisions.length ? `R${dirty ? `${last.n} + edits` : last.n}` : '—'} · demo only, not stored
            </span>
          </div>
          <div className="lp-editor__body">
            <div className="lp-editor__view">
              {compare && before && current ? (
                <div className="lp-editor__compare">
                  <CompareSlider before={before.url} after={current.url} beforeLabel={`R${before.n}`} afterLabel={dirty ? 'Current' : `R${last.n}`} />
                </div>
              ) : current ? (
                <img src={current.url} alt="Live procedural composite in the editor showcase" />
              ) : status === 'offline' ? (
                <div className="lp-demo__empty">
                  <Icon name="cpu" />
                  <strong>Live editor needs the local engine</strong>
                  <span>Start it with <code>npm run dev</code>.</span>
                  <button type="button" className="lp-btn lp-btn--ghost lp-btn--sm" onClick={retry}><Icon name="reset" /> Retry</button>
                </div>
              ) : (
                <div className="lp-skel" aria-busy="true" />
              )}
              {loading && <span className="lp-editor__busy lp-mono"><span className="lp-spinner" /> rendering</span>}
              {error && <p className="lp-error lp-editor__err" role="alert">{error}</p>}
            </div>

            <div className="lp-editor__panel">
              <div className="lp-editor__group">
                <span className="lp-label">Proportions</span>
                {SLIDERS.map(([key, label]) => {
                  const v = profile?.adjustments?.[key] ?? 0
                  return (
                    <label key={key} className="lp-slider">
                      <span>{label} <span className="lp-mono">{v > 0 ? '+' : ''}{v.toFixed(2)}</span></span>
                      <input type="range" min={-1} max={1} step={0.05} value={v} disabled={!profile}
                        style={{ '--fill': `${((v + 1) / 2) * 100}%` }} onChange={(e) => setAdj(key, Number(e.target.value))} />
                    </label>
                  )
                })}
              </div>
              {hairline && facial && (
                <div className="lp-editor__group">
                  <span className="lp-label">Hairline</span>
                  <div className="lp-seg" role="group" aria-label="Hairline">
                    {hairline.options.map((o) => (
                      <button key={o} type="button" disabled={!profile} aria-pressed={profile?.traits.hairline?.value === o}
                        onClick={() => setTrait('hairline', o)}>{optionLabel(hairline, o)}</button>
                    ))}
                  </div>
                  <span className="lp-label">Facial hair</span>
                  <div className="lp-seg" role="group" aria-label="Facial hair">
                    {facial.options.map((o) => (
                      <button key={o} type="button" disabled={!profile} aria-pressed={profile?.traits.facial_hair?.value === o}
                        onClick={() => setTrait('facial_hair', o)}>{optionLabel(facial, o)}</button>
                    ))}
                  </div>
                </div>
              )}
              <div className="lp-editor__group">
                <span className="lp-label">Trait list</span>
                <ul className="lp-editor__traits">
                  {known.map(([k, t]) => (
                    <li key={k}><span>{traitByKey[k]?.label}</span><b>{optionLabel(traitByKey[k], t.value)}</b><i className={`lp-tag lp-tag--${t.source}`}>{t.source}</i></li>
                  ))}
                  {!known.length && <li className="lp-faint">—</li>}
                </ul>
              </div>
              <div className="lp-editor__actions">
                <button type="button" className="lp-btn lp-btn--ghost lp-btn--sm" onClick={saveRevision} disabled={!dirty}>
                  <Icon name="save" /> Save revision
                </button>
                <button type="button" className={`lp-btn lp-btn--sm ${compare ? 'lp-btn--primary' : 'lp-btn--ghost'}`}
                  onClick={() => setCompare((v) => !v)} disabled={!before} aria-pressed={compare}>
                  <Icon name="compare" /> Before / after
                </button>
                <button type="button" className="lp-btn lp-btn--ghost lp-btn--sm" onClick={reset} disabled={!revisions.length}>
                  <Icon name="reset" /> Reset
                </button>
              </div>
              <p className="lp-faint lp-editor__foot">
                Revisions here live only in this page. <a href="/app#/new">Open the workspace</a> to save them with full history.
              </p>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
