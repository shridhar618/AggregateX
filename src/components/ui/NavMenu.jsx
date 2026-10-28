import { useEffect, useRef, useState } from 'react';
import Icon from './Icon';

const PHASES = [
  { id: 'interview', index: '01', label: 'Interview', hint: 'Collect the witness description' },
  { id: 'candidates', index: '02', label: 'Refinement', hint: 'Generate and refine candidate sketches' },
  { id: 'consensus', index: '03', label: 'Consensus', hint: 'Fuse confirmed matches into one composite' },
];

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

// Full-screen ink overlay: case navigation + Gemini key settings.
const NavMenu = ({
  open,
  onClose,
  witnesses,
  activeWitnessId,
  currentPhase,
  onSelectWitness,
  onAddWitness,
  apiKey,
  onApiKeyChange,
}) => {
  const panelRef = useRef(null);
  const closeRef = useRef(null);
  const [showKey, setShowKey] = useState(false);

  // Escape to close, Tab trapped inside the overlay, body scroll locked.
  useEffect(() => {
    if (!open) return undefined;
    document.body.classList.add('is-locked');
    const focusTimer = setTimeout(() => closeRef.current?.focus(), 60);

    const onKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key !== 'Tab' || !panelRef.current) return;
      const nodes = Array.from(panelRef.current.querySelectorAll(FOCUSABLE));
      if (nodes.length === 0) return;
      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', onKeyDown);
    return () => {
      clearTimeout(focusTimer);
      document.removeEventListener('keydown', onKeyDown);
      document.body.classList.remove('is-locked');
    };
  }, [open, onClose]);

  const handleClose = () => {
    setShowKey(false);
    onClose();
  };

  const clearKey = () => {
    onApiKeyChange({ target: { value: '' } });
    setShowKey(false);
  };

  const phaseIndex = PHASES.findIndex((p) => p.id === currentPhase);
  const hasKey = Boolean(apiKey);

  return (
    <div
      className={`nav-menu surface-ink ${open ? 'is-open' : ''}`}
      role="dialog"
      aria-modal="true"
      aria-label="Case menu"
      aria-hidden={!open}
      inert={!open}
      ref={panelRef}
    >
      <div className="nav-menu__inner">
        <div className="nav-menu__head">
          <span className="eyebrow">Case menu</span>
          <button ref={closeRef} type="button" className="btn btn-sm" onClick={handleClose}>
            <Icon name="close" />
            Close
          </button>
        </div>

        <div className="nav-menu__grid">
          {/* Workflow status */}
          <section className="nav-menu__section" aria-labelledby="menu-workflow">
            <h2 id="menu-workflow" className="nav-menu__label">Workflow</h2>
            <ol className="nav-menu__phases">
              {PHASES.map((p, i) => {
                const state = i < phaseIndex ? 'done' : i === phaseIndex ? 'current' : 'upcoming';
                return (
                  <li key={p.id} className={`nav-menu__phase is-${state}`} aria-current={state === 'current' ? 'step' : undefined}>
                    <span className="nav-menu__phase-index mono">{p.index}</span>
                    <span className="nav-menu__phase-label">{p.label}</span>
                    <span className="nav-menu__phase-hint">{p.hint}</span>
                  </li>
                );
              })}
            </ol>
          </section>

          {/* Witnesses */}
          <section className="nav-menu__section" aria-labelledby="menu-witnesses">
            <h2 id="menu-witnesses" className="nav-menu__label">Witnesses</h2>
            <ul className="nav-menu__witnesses">
              {witnesses.map((w) => {
                const isActive = w.id === activeWitnessId;
                const isDone = Boolean(w.selectedCandidate);
                return (
                  <li key={w.id}>
                    <button
                      type="button"
                      className={`nav-menu__witness ${isActive ? 'is-active' : ''}`}
                      onClick={() => {
                        onSelectWitness(w.id);
                        handleClose();
                      }}
                      aria-current={isActive ? 'true' : undefined}
                    >
                      <span className="nav-menu__witness-id">{w.id}</span>
                      <span className="nav-menu__witness-name">{w.name}</span>
                      <span className={`chip ${isDone ? 'chip--success' : ''}`}>
                        {isDone ? 'Match confirmed' : 'In progress'}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
            <button
              type="button"
              className="btn btn-sm nav-menu__add"
              onClick={() => {
                onAddWitness();
                handleClose();
              }}
            >
              <Icon name="plus" />
              Add witness
            </button>
          </section>

          {/* Gemini API key */}
          <section className="nav-menu__section nav-menu__section--key" aria-labelledby="menu-key">
            <h2 id="menu-key" className="nav-menu__label">Gemini API key</h2>
            <div className="key-field">
              <label htmlFor="gemini-key" className="sr-only">Gemini API key</label>
              <Icon name="key" className="icon key-field__icon" />
              <input
                id="gemini-key"
                className="input key-field__input"
                type={showKey ? 'text' : 'password'}
                value={apiKey}
                onChange={onApiKeyChange}
                placeholder="Paste your Gemini API key"
                autoComplete="off"
                autoCapitalize="off"
                autoCorrect="off"
                spellCheck={false}
                data-1p-ignore="true"
                data-lpignore="true"
                aria-describedby="gemini-key-help"
              />
              <button
                type="button"
                className="btn btn-sm btn-ghost key-field__toggle"
                onClick={() => setShowKey((v) => !v)}
                aria-pressed={showKey}
                aria-controls="gemini-key"
                disabled={!hasKey}
              >
                <Icon name={showKey ? 'eyeOff' : 'eye'} />
                {showKey ? 'Hide' : 'Show'}
              </button>
            </div>

            <div className="key-field__status" aria-live="polite">
              <span className={`chip ${hasKey ? 'chip--success' : 'chip--warning'}`}>
                <Icon name={hasKey ? 'check' : 'alert'} className="icon" />
                {hasKey ? 'Key set' : 'No key set'}
              </span>
              {hasKey && (
                <button type="button" className="btn btn-sm btn-ghost" onClick={clearKey}>
                  <Icon name="trash" />
                  Clear key
                </button>
              )}
            </div>

            <div id="gemini-key-help" className="key-field__help">
              <p>
                <strong>How the key is stored.</strong> The key is saved only in this browser&rsquo;s local storage, under the name
                <code> gemini_api_key</code>. It is not uploaded to any VeriSketch server, because there is none.
              </p>
              <p>
                Each image request sends the key from your browser directly to Google&rsquo;s Gemini API. Anyone with access to
                this browser profile can read it, so clear it on shared machines.
              </p>
              <p>
                If this field is empty when the page loads, a key from the project&rsquo;s <code>.env</code> file is used instead, if one exists.
              </p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
};

export default NavMenu;
