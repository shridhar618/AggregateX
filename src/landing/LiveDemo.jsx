import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import Icon from '../components/ui/Icon'
import { downloadBlob, optionLabel } from '../lib/format'
import { useEngine } from './engine'
import { Reveal, SplitLines } from './motion'

const DEFAULT_DESCRIPTION =
  'An adult with an oval face, short dark hair, thick eyebrows, a narrow nose, and a small scar on the left cheek.'
const CONTROLS = ['face_shape', 'hair_style', 'hairline', 'eyebrow_thickness', 'nose_shape', 'facial_hair', 'eyewear', 'chin']
const SLIDERS = [
  ['jaw_width', 'Jaw width'],
  ['eye_spacing', 'Eye spacing'],
  ['nose_length', 'Nose length'],
  ['mouth_width', 'Mouth width'],
]

/** Calls the real local renderer; the hook owns the preview's object URL. */
function useRenderedSvg() {
  const [state, setState] = useState({ url: null, loading: false, error: null, notes: [] })
  const urlRef = useRef(null)
  const ctrlRef = useRef(null)
  const render = async (profile) => {
    ctrlRef.current?.abort()
    const ctrl = new AbortController()
    ctrlRef.current = ctrl
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const r = await api.render(profile, 'DEMO', ctrl.signal)
      const url = URL.createObjectURL(new Blob([r.svg], { type: 'image/svg+xml' }))
      if (urlRef.current) URL.revokeObjectURL(urlRef.current)
      urlRef.current = url
      setState({ url, loading: false, error: null, notes: r.notes })
      return url
    } catch (err) {
      if (err.name !== 'AbortError') setState((s) => ({ ...s, loading: false, error: err.message }))
      return null
    }
  }
  useEffect(() => () => urlRef.current && URL.revokeObjectURL(urlRef.current), [])
  return [state, render]
}

export default function LiveDemo() {
  const { status, catalog, retry } = useEngine()
  const [description, setDescription] = useState(DEFAULT_DESCRIPTION)
  const [profile, setProfile] = useState(null)
  const [extraction, setExtraction] = useState(null)
  const [phase, setPhase] = useState('idle') // idle | extracting | ready
  const [inputError, setInputError] = useState(null)
  const [preview, render] = useRenderedSvg()
  const [renders, setRenders] = useState(0)
  const [downloading, setDownloading] = useState(false)
  const debounce = useRef(0)

  const traitByKey = Object.fromEntries((catalog?.traits || []).map((t) => [t.key, t]))
  const offline = status === 'offline'

  const generate = async () => {
    setInputError(null)
    if (description.trim().length < 10) {
      setInputError('Write at least 10 characters describing the (fictional) face.')
      return
    }
    setPhase('extracting')
    try {
      const ex = await api.extract(description.trim())
      setExtraction(ex)
      setProfile(ex.profile)
      const ok = await render(ex.profile)
      if (ok) setRenders((n) => n + 1)
      setPhase('ready')
    } catch (err) {
      setInputError(err.message)
      setPhase(profile ? 'ready' : 'idle')
    }
  }

  const update = (next) => {
    setProfile(next)
    clearTimeout(debounce.current)
    debounce.current = setTimeout(async () => {
      const ok = await render(next)
      if (ok) setRenders((n) => n + 1)
    }, 120)
  }
  useEffect(() => () => clearTimeout(debounce.current), [])

  const setTrait = (key, value) => {
    const next = structuredClone(profile)
    next.traits[key] = value
      ? { value, source: 'manual', evidence: null, certainty: 'stated', alternatives: [] }
      : { value: null, source: 'unknown', evidence: null, certainty: 'stated', alternatives: [] }
    update(next)
  }
  const setAdj = (key, v) => {
    const next = structuredClone(profile)
    if (Math.abs(v) < 0.001) delete next.adjustments[key]
    else next.adjustments[key] = v
    update(next)
  }

  const download = async () => {
    setDownloading(true)
    try {
      downloadBlob(await api.renderPng(profile, 'DEMO'), 'revelio-demo-composite.png')
    } catch (err) {
      setInputError(err.message)
    } finally {
      setDownloading(false)
    }
  }

  const known = profile ? Object.entries(profile.traits).filter(([, t]) => t.value) : []
  const unknownCount = profile ? Object.values(profile.traits).filter((t) => !t.value && !t.alternatives?.length).length : 0

  return (
    <section id="demo" className="lp-section lp-demo" aria-labelledby="demo-title">
      <div className="lp-shell">
        <div className="lp-section__head">
          <Reveal><span className="lp-eyebrow">Live demo · runs on the local engine</span></Reveal>
          <SplitLines lines={['Describe a face.', 'Watch it become a composite.']} className="lp-h2" />
          <span id="demo-title" className="sr-only">Live demo</span>
          <Reveal delay={150}>
            <p className="lp-section__lead">
              This demo uses the same trait extractor and procedural renderer as the workspace. Use a fictional description; nothing is saved.
            </p>
          </Reveal>
        </div>

        <Reveal className="lp-demo__panel" y={36}>
          <div className="lp-demo__input">
            <label className="lp-label" htmlFor="demo-desc">Fictional description</label>
            <textarea id="demo-desc" className="lp-textarea" rows={5} maxLength={2000} value={description}
              onChange={(e) => { setDescription(e.target.value); setInputError(null) }}
              aria-invalid={Boolean(inputError)} />
            <div className="lp-demo__row">
              <span className="lp-mono lp-faint">{description.length} / 2000</span>
              <button type="button" className="lp-link" onClick={() => setDescription(DEFAULT_DESCRIPTION)}>Reset example</button>
            </div>
            {inputError && <p className="lp-error" role="alert">{inputError}</p>}
            <button type="button" className="lp-btn lp-btn--primary lp-btn--block" onClick={generate}
              disabled={offline || phase === 'extracting' || status === 'checking'}>
              {phase === 'extracting' ? <span className="lp-spinner" /> : <Icon name="scan" />}
              {phase === 'extracting' ? 'Extracting & rendering…' : profile ? 'Regenerate from description' : 'Generate Composite'}
            </button>

            {extraction && (
              <div className="lp-demo__extract">
                <span className="lp-label">Extracted traits <span className="lp-mono lp-faint">{known.length} known · {unknownCount} unknown</span></span>
                <ul className="lp-chips">
                  {known.map(([k, t]) => (
                    <li key={k} className={`lp-chip lp-chip--${t.source}`}>
                      {traitByKey[k]?.label}: <b>{optionLabel(traitByKey[k], t.value)}</b>
                    </li>
                  ))}
                  {profile.marks.map((m) => (
                    <li key={m.id} className={`lp-chip lp-chip--${m.source}`}>{m.size} {m.type} · {m.location.replace(/_/g, ' ')}</li>
                  ))}
                </ul>
                {extraction.conflicts.length > 0 && (
                  <p className="lp-warn"><Icon name="alert" /> {extraction.conflicts.length} conflicting statement(s) left unresolved, as in the workspace.</p>
                )}
              </div>
            )}
          </div>

          <div className="lp-demo__stage">
            <div className="lp-demo__label">
              <span className="lp-tag lp-tag--procedural">Procedural demonstration composite</span>
              <span className="lp-mono lp-faint">{renders ? `render #${renders}` : 'no render yet'}</span>
            </div>
            <div className={`lp-demo__frame ${preview.loading ? 'is-loading' : ''}`}>
              {preview.url ? (
                <img src={preview.url} alt="Procedural demonstration composite generated from the description above" />
              ) : offline ? (
                <div className="lp-demo__empty">
                  <Icon name="cpu" />
                  <strong>The local engine isn’t running</strong>
                  <span>The live demo renders on your machine. Start it with <code>npm run dev</code>, then retry.</span>
                  <button type="button" className="lp-btn lp-btn--ghost lp-btn--sm" onClick={retry}><Icon name="reset" /> Retry</button>
                </div>
              ) : (
                <div className="lp-demo__empty">
                  <Icon name="scan" />
                  <strong>Ready when you are</strong>
                  <span>Click <b>Generate Composite</b> to extract traits and render a real procedural composite.</span>
                </div>
              )}
              {preview.loading && <span className="lp-demo__scan" aria-hidden="true" />}
              {preview.error && (
                <div className="lp-demo__err" role="alert">
                  <span>{preview.error}</span>
                  <button type="button" className="lp-btn lp-btn--ghost lp-btn--sm" onClick={() => profile && render(profile)}>Retry</button>
                </div>
              )}
            </div>
            <p className="lp-demo__note">
              Procedural composites are stylised, monochrome drawings built from vector features. They are not photorealistic and do not have the realism of advanced image-generation models.
            </p>
            <button type="button" className="lp-btn lp-btn--ghost lp-btn--block" onClick={download} disabled={!preview.url || downloading}>
              {downloading ? <span className="lp-spinner" /> : <Icon name="download" />} Download PNG
            </button>
          </div>

          <div className="lp-demo__controls" aria-label="Adjust supported characteristics">
            <span className="lp-label">Adjust supported characteristics</span>
            {!profile ? (
              <p className="lp-faint lp-demo__hint">Generate a composite first. Every control below re-renders the image through the real renderer.</p>
            ) : (
              <>
                <div className="lp-demo__selects">
                  {CONTROLS.map((key) => {
                    const t = traitByKey[key]
                    if (!t) return null
                    return (
                      <label key={key} className="lp-field">
                        <span>{t.label}</span>
                        <select className="lp-select" value={profile.traits[key]?.value || ''} onChange={(e) => setTrait(key, e.target.value || null)}>
                          <option value="">Unknown (neutral)</option>
                          {t.options.map((o) => <option key={o} value={o}>{optionLabel(t, o)}</option>)}
                        </select>
                      </label>
                    )
                  })}
                </div>
                {SLIDERS.map(([key, label]) => {
                  const v = profile.adjustments?.[key] ?? 0
                  return (
                    <label key={key} className="lp-slider">
                      <span>{label} <span className="lp-mono">{v > 0 ? '+' : ''}{v.toFixed(2)}</span></span>
                      <input type="range" min={-1} max={1} step={0.05} value={v} style={{ '--fill': `${((v + 1) / 2) * 100}%` }}
                        onChange={(e) => setAdj(key, Number(e.target.value))} />
                    </label>
                  )
                })}
              </>
            )}
          </div>
        </Reveal>
      </div>
    </section>
  )
}
