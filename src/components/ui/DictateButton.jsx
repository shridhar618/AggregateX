import { useEffect, useRef, useState } from 'react'
import { useApp } from '../../state/AppContext'
import Icon from './Icon'

const Recognition = typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : null

// Embedded Electron views (VS Code's browser, desktop shells) and Brave expose the
// API but have no access to the speech service, so every attempt fails with "network".
const NO_SERVICE = typeof navigator !== 'undefined' && (/Electron\//.test(navigator.userAgent) || 'brave' in navigator)

const OPEN_ELSEWHERE = 'Open Revelio in Chrome, Edge or Safari to use dictation.'

const ERRORS = {
  'not-allowed': 'Microphone access was blocked. Allow it in the browser’s site settings to dictate.',
  'service-not-allowed': 'Speech recognition is disabled in this browser.',
  'audio-capture': 'No microphone was found.',
  network: `This browser could not reach its speech recognition service. Check your connection. ${OPEN_ELSEWHERE}`,
  'language-not-supported': 'Speech recognition does not support this language.',
}

// Only one field dictates at a time; starting another stops the current one.
let active = null

// Appends a dictated phrase to existing text, starting a new sentence with a capital.
function append(base, phrase) {
  const text = phrase.trim()
  if (!text) return base
  const head = base.replace(/\s+$/, '')
  const sentence = !head || /[.!?]$/.test(head)
  const chunk = sentence ? text[0].toUpperCase() + text.slice(1) : text
  return head ? `${head} ${chunk}` : chunk
}

// Speech-to-text for witness input, via the browser's Web Speech API.
// Final phrases are appended to `value`; the in-progress phrase is shown live.
// Renders nothing where the API is unavailable (e.g. Firefox).
const DictateButton = ({ value, onChange, maxLength, label = 'Dictate', lang }) => {
  const { notify } = useApp()
  const [listening, setListening] = useState(false)
  const [interim, setInterim] = useState('')
  const rec = useRef(null)
  const want = useRef(false)
  const latest = useRef({ value, onChange, maxLength })
  useEffect(() => { latest.current = { value, onChange, maxLength } })

  useEffect(() => () => {
    want.current = false
    rec.current?.abort()
    if (active === rec.current) active = null
  }, [])

  if (!Recognition) return null

  const stop = () => {
    want.current = false
    rec.current?.stop()
  }

  const start = () => {
    if (NO_SERVICE) {
      notify({ kind: 'warn', title: 'Dictation unavailable here', message: `This browser has no speech recognition service. ${OPEN_ELSEWHERE}` })
      return
    }
    if (active && active !== rec.current) active.stop()
    const r = new Recognition()
    r.continuous = true
    r.interimResults = true
    r.lang = lang || document.documentElement.lang || navigator.language || 'en-US'
    r.onresult = (e) => {
      let pending = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i]
        if (res.isFinal) {
          const { value: v, onChange: set, maxLength: max } = latest.current
          const next = append(v, res[0].transcript)
          latest.current.value = max ? next.slice(0, max) : next
          set(latest.current.value)
        } else {
          pending += res[0].transcript
        }
      }
      setInterim(pending)
    }
    r.onerror = (e) => {
      if (e.error === 'no-speech' || e.error === 'aborted') return
      want.current = false
      notify({ kind: 'error', title: 'Dictation stopped', message: ERRORS[e.error] || `Speech recognition error: ${e.error}` })
    }
    r.onend = () => {
      // Browsers end sessions after silence or a time limit; resume until the operator stops.
      if (want.current && rec.current === r) {
        try { r.start(); return } catch { /* fall through */ }
      }
      setListening(false)
      setInterim('')
      if (active === r) active = null
    }
    rec.current = r
    active = r
    want.current = true
    try {
      r.start()
      setListening(true)
    } catch {
      want.current = false
    }
  }

  return (
    <span className="dictate">
      {listening && (
        <span className="dictate__live" aria-live="polite">
          <span className="dictate__pulse" aria-hidden="true" />
          <span className="dictate__interim">{interim || 'Listening…'}</span>
        </span>
      )}
      <button
        type="button"
        className={`btn btn--sm ${listening ? 'btn--danger' : 'btn--ghost'}`}
        aria-pressed={listening}
        onClick={listening ? stop : start}
        title={listening ? 'Stop dictation' : 'Dictate with the microphone. Uses the browser’s speech recognition service.'}
      >
        <Icon name={listening ? 'micOff' : 'mic'} /> {listening ? 'Stop' : label}
      </button>
    </span>
  )
}

export default DictateButton
