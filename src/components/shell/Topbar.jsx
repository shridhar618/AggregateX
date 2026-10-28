import { useEffect, useRef, useState } from 'react'
import { relativeTime } from '../../lib/format'
import { useApp } from '../../state/AppContext'
import { LogoMark } from '../brand/Logo'
import CaseClock from '../ui/CaseClock'
import Icon from '../ui/Icon'

const KIND_ICON = { ok: 'ok', info: 'info', warn: 'alert', error: 'error' }

const Topbar = ({ title, eyebrow, onMenu }) => {
  const { activeCase, notifications, clearNotifications, health } = useApp()
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return undefined
    const onDoc = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    const onKey = (e) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <header className="topbar">
      <button type="button" className="btn btn--ghost btn--icon topbar__menu" onClick={onMenu} aria-label="Open navigation">
        <Icon name="menu" />
      </button>
      <span className="topbar__logo"><LogoMark size={28} /></span>

      <div className="topbar__title">
        <span className="label">{eyebrow}</span>
        <h1>{title}</h1>
      </div>

      <div className="topbar__right">
        <div className={`case-chip ${activeCase ? 'is-active' : ''}`} title="Active case">
          <span className="label">Case</span>
          <span className="mono case-chip__id">
            {activeCase?.id ? activeCase.id : activeCase?.draft ? 'UNSAVED DRAFT' : 'NONE ACTIVE'}
          </span>
          {activeCase?.revision ? <span className="mono faint">R{activeCase.revision}</span> : null}
        </div>

        <div className="topbar__engine" title={health ? 'Local engine reachable' : 'Local engine not reachable'}>
          <span className={`dot ${health ? 'dot--ok' : 'dot--err'}`} />
          <span className="mono">{health ? 'LOCAL' : 'OFFLINE'}</span>
        </div>

        <CaseClock />

        <div className="notif" ref={ref}>
          <button
            type="button"
            className="btn btn--ghost btn--icon notif__btn"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-label={`Notifications (${notifications.length})`}
          >
            <Icon name="bell" />
            {notifications.length > 0 && <span className="notif__count mono">{Math.min(9, notifications.length)}</span>}
          </button>
          {open && (
            <div className="notif__panel panel" role="dialog" aria-label="Notifications">
              <div className="panel__head">
                <span className="panel__title">Notifications</span>
                <span className="label">This session</span>
              </div>
              {notifications.length === 0 ? (
                <p className="notif__empty muted">No notifications yet.</p>
              ) : (
                <ul className="notif__list">
                  {notifications.map((n) => (
                    <li key={n.id} className={`notif__item is-${n.kind}`}>
                      <Icon name={KIND_ICON[n.kind] || 'info'} />
                      <div>
                        <strong>{n.title}</strong>
                        {n.message && <p>{n.message}</p>}
                      </div>
                      <span className="mono faint">{relativeTime(n.at)}</span>
                    </li>
                  ))}
                </ul>
              )}
              {notifications.length > 0 && (
                <div className="notif__foot">
                  <button type="button" className="btn btn--ghost btn--sm" onClick={clearNotifications}>Clear</button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export default Topbar
