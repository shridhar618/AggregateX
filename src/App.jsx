import { lazy, Suspense, useEffect, useState } from 'react'
import { witnessMode } from './api/witnesstrace'
import WitnessStudio, { WitnessWorkspace } from './pages/WitnessStudio'
import { api } from './api/client'
import BootScreen from './components/shell/BootScreen'
import Sidebar from './components/shell/Sidebar'
import Toasts from './components/shell/Toasts'
import Topbar from './components/shell/Topbar'
import Icon from './components/ui/Icon'
import { loginUrl } from './lib/auth'
import { NAV } from './lib/nav'
import { useRoute } from './lib/router'
import Workspace from './pages/Workspace'
import { AppProvider, useApp } from './state/AppContext'
import './styles/app.css'

const NewSketch = lazy(() => import('./pages/NewSketch'))
const Library = lazy(() => import('./pages/Library'))
const Compare = lazy(() => import('./pages/Compare'))
const Settings = lazy(() => import('./pages/Settings'))

const TITLES = {
  workspace: ['Overview', 'Investigation Workspace'],
  new: ['Composite builder', 'New Sketch'],
  library: ['Saved composites', 'Sketch Library'],
  compare: ['Revision analysis', 'Compare Sketches'],
  settings: ['Configuration', 'Settings'],
}

const MIN_BOOT_MS = 900

function PageFallback() {
  return (
    <div className="page-fallback" aria-busy="true">
      <div className="skeleton" style={{ height: 28, width: 260 }} />
      <div className="skeleton" style={{ height: 220 }} />
      <div className="skeleton" style={{ height: 140 }} />
    </div>
  )
}

function EngineOffline({ onRetry, retrying }) {
  return (
    <div className="engine-offline panel panel--corners reveal">
      <Icon name="cpu" className="icon engine-offline__icon" />
      <h2>Local engine not reachable</h2>
      <p className="muted">
        Revelio renders composites and stores sketches with a small local server on this machine.
        It is not running, so nothing can be generated yet. No data is sent anywhere else.
      </p>
      <pre className="code mono">{`npm run dev        # starts the API and the interface together\n# or, if the interface is already running, in a second terminal:\nnpm run dev:api`}</pre>
      <button type="button" className="btn btn--primary" onClick={onRetry} disabled={retrying}>
        {retrying ? <span className="spinner" /> : <Icon name="reset" />}
        Retry connection
      </button>
    </div>
  )
}

function Shell() {
  const route = useRoute()
  const { refreshHealth, loadCatalog, health, catalog, wt } = useApp()
  const [steps, setSteps] = useState({ ui: 'ok', engine: 'pending', catalog: 'pending', providers: 'pending' })
  const [bootState, setBootState] = useState('running') // running | leaving | done
  const [navOpen, setNavOpen] = useState(false)
  const [retrying, setRetrying] = useState(false)

  useEffect(() => {
    let cancelled = false
    const started = performance.now()
    ;(async () => {
      const h = await refreshHealth()
      if (cancelled) return
      if (!h) {
        setSteps({ ui: 'ok', engine: 'error', catalog: 'skipped', providers: 'skipped' })
      } else {
        setSteps((s) => ({ ...s, engine: 'ok' }))
        try {
          await loadCatalog()
          if (!cancelled) setSteps((s) => ({ ...s, catalog: 'ok', providers: 'ok' }))
        } catch {
          if (!cancelled) setSteps((s) => ({ ...s, catalog: 'error', providers: 'ok' }))
        }
      }
      const wait = Math.max(0, MIN_BOOT_MS - (performance.now() - started))
      setTimeout(() => {
        if (cancelled) return
        setBootState('leaving')
        setTimeout(() => !cancelled && setBootState('done'), 420)
      }, wait)
    })()
    return () => {
      cancelled = true
    }
  }, [refreshHealth, loadCatalog])

  const retry = async () => {
    setRetrying(true)
    const h = await refreshHealth()
    if (h) {
      try {
        await loadCatalog()
      } catch {
        /* surfaced below */
      }
    }
    setRetrying(false)
  }

  const page = NAV.some((n) => n.id === route.path) ? route.path : 'workspace'
  const [eyebrow, title] = TITLES[page]
  const ready = Boolean(health && catalog)

  let content
  if (!ready && bootState === 'done') content = <EngineOffline onRetry={retry} retrying={retrying} />
  else if (!ready) content = <PageFallback />
  else if (page === 'workspace') content = witnessMode ? <WitnessWorkspace /> : <Workspace />
  else if (page === 'new' && witnessMode) content = <WitnessStudio key={wt.record?.id || 'new'} />
  else if (page === 'new') content = <NewSketch key={`${route.params.sketch || 'new'}-${route.params.rev || ''}-${route.params.fresh || ''}`} params={route.params} />
  else if (page === 'library') content = <Library />
  else if (page === 'compare') content = <Compare params={route.params} />
  else content = <Settings />

  return (
    <div className={`app ${witnessMode ? 'app--witness' : ''}`}>
      {bootState !== 'done' && <BootScreen steps={steps} leaving={bootState === 'leaving'} />}
      <a href="#main" className="skip-link">Skip to content</a>
      <Sidebar current={page} open={navOpen} onNavigate={() => setNavOpen(false)} onClose={() => setNavOpen(false)} />
      <div className="app__main">
        <Topbar title={title} eyebrow={eyebrow} onMenu={() => setNavOpen(true)} />
        <main id="main" className="content" key={page}>
          {witnessMode && <p className="alert">Local integration · synthetic cases only · Codex generation uses the authenticated CLI. {['library', 'compare', 'settings'].includes(page) && 'This legacy Revelio screen is not connected to WitnessTrace; full integration is deferred to I4.'}</p>}
          <Suspense fallback={<PageFallback />}>{content}</Suspense>
        </main>
        <footer className="app__foot">
          <span className="mono">REVELIO · v1.0</span>
          <span>Investigative assistance only. A composite is not proof of identity.</span>
        </footer>
      </div>
      <Toasts />
    </div>
  )
}

export default function App() {
  const [auth, setAuth] = useState({ checked: false, user: null })

  useEffect(() => {
    api.me()
      .then((r) => setAuth({ checked: true, user: r.user }))
      .catch((err) => {
        if (err.status === 401) window.location.replace(loginUrl())
        // Engine unreachable: render the shell, which explains how to start it.
        else setAuth({ checked: true, user: null, error: err.message })
      })
  }, [])

  if (!auth.checked) return null
  if (!auth.user) return <div className="engine-offline panel" role="alert"><h2>Sign-in service unavailable</h2><p>{auth.error}</p><button className="btn" onClick={() => window.location.reload()}>Retry sign-in check</button></div>
  return (
    <AppProvider user={auth.user}>
      <Shell />
    </AppProvider>
  )
}
