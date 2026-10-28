import { lazy, StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'

/* eslint-disable react-refresh/only-export-components -- entry file, not a component module */

// Two entry points, one Vite build:
//   /      → marketing landing page
//   /app   → the Revelio workspace (unchanged; uses #/hash routes internally)
const App = lazy(() => import('./App.jsx'))
const LandingPage = lazy(() => import('./landing/LandingPage.jsx'))

// One-time carry-over of browser storage saved before the project was renamed.
try {
  for (const k of ['draft', 'prefs']) {
    const old = window.localStorage.getItem(`verisketch.${k}`)
    if (old != null && window.localStorage.getItem(`revelio.${k}`) == null) window.localStorage.setItem(`revelio.${k}`, old)
  }
} catch {
  /* storage unavailable */
}

const { pathname, hash, search } = window.location

// Old bookmarks such as /#/library belonged to the workspace: keep them working.
if ((pathname === '/' || pathname === '') && hash.startsWith('#/')) {
  window.location.replace(`/app${search}${hash}`)
}

const isApp = pathname === '/app' || pathname.startsWith('/app/')
document.title = isApp ? 'Revelio — Forensic Composite Workspace' : 'Revelio — From Witness Description to Forensic Sketch'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Suspense fallback={null}>{isApp ? <App /> : <LandingPage />}</Suspense>
  </StrictMode>,
)
