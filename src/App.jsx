import { useCallback, useRef, useState } from 'react';
import WitnessInterview from './components/WitnessInterview';
import CandidateExploration from './components/CandidateExploration';
import MultiWitnessConsensus from './components/MultiWitnessConsensus';
import PageLoader from './components/ui/PageLoader';
import NavMenu from './components/ui/NavMenu';
import CaseClock from './components/ui/CaseClock';
import SiteFooter from './components/ui/SiteFooter';
import Icon from './components/ui/Icon';
import './styles/shell.css';
import './styles/phases.css';
import './styles/motion.css';

const PHASES = [
  { id: 'interview', index: '01', label: 'Interview' },
  { id: 'candidates', index: '02', label: 'Refinement' },
  { id: 'consensus', index: '03', label: 'Consensus' }
];

function App() {
  const [currentPhase, setCurrentPhase] = useState('interview'); // interview, candidates, consensus
  const [apiKey, setApiKey] = useState(localStorage.getItem('gemini_api_key') || import.meta.env.VITE_GEMINI_API_KEY || '');
  const [activeWitnessId, setActiveWitnessId] = useState('A');

  const initialWitness = (id) => ({
    id,
    name: `Witness ${id}`,
    faceDescription: "",
    structuredTraits: {},
    messages: [
      { id: 1, text: `Hi Witness ${id} — I’m VeriSketch AI, your forensic sketch assistant. Take your time and describe the person you saw, and I’ll help build a clear profile with you.`, sender: "ai" }
    ],
    candidates: [],
    selectedCandidate: null,
    sourceImage: null,
    refinements: [],
    generationCount: 1
  });

  const [witnesses, setWitnesses] = useState([initialWitness('A'), initialWitness('B')]);

  const activeWitness = witnesses.find(w => w.id === activeWitnessId);

  const updateWitness = (id, newData) => {
    setWitnesses(prev => prev.map(w => w.id === id ? { ...w, ...newData } : w));
  };

  const advanceAfterCandidateConfirm = () => {
    const remainingWitness = witnesses.find(w => w.id !== activeWitnessId && !w.selectedCandidate);
    if (remainingWitness) {
      setActiveWitnessId(remainingWitness.id);
      setCurrentPhase('interview');
      return;
    }
    setCurrentPhase('consensus');
  };

  const addWitness = () => {
    const nextLabel = String.fromCharCode(65 + witnesses.length); // A, B, C...
    const newW = initialWitness(nextLabel);
    setWitnesses(prev => [...prev, newW]);
    setActiveWitnessId(nextLabel);
    setCurrentPhase('interview');
  };

  const handleKeyChange = (e) => {
    const val = e.target.value;
    setApiKey(val);
    localStorage.setItem('gemini_api_key', val);
  };

  // ---- Presentation-only state (redesign) ----
  const [menuOpen, setMenuOpen] = useState(false);
  const [booted, setBooted] = useState(false);
  const menuButtonRef = useRef(null);

  const closeMenu = useCallback(() => {
    setMenuOpen(false);
    menuButtonRef.current?.focus();
  }, []);

  const openMenu = () => setMenuOpen(true);

  const phaseIndex = PHASES.findIndex(p => p.id === currentPhase);
  const confirmedCount = witnesses.filter(w => w.selectedCandidate).length;

  return (
    <div className={`app-container ${booted ? 'is-booted' : ''}`}>
      <PageLoader onDone={() => setBooted(true)} />

      <header className="app-header">
        <div className="app-header__inner">
          <div className="app-header__left">
            <button
              ref={menuButtonRef}
              type="button"
              className="btn btn-sm menu-trigger"
              onClick={openMenu}
              aria-haspopup="dialog"
              aria-expanded={menuOpen}
            >
              <Icon name="menu" />
              <span>Menu</span>
              {!apiKey && <span className="menu-trigger__dot" title="Gemini API key not set" />}
            </button>
            <div className="brand">
              <span className="brand__mark" aria-hidden="true">
                <svg viewBox="0 0 32 32"><rect width="32" height="32" rx="9" fill="currentColor" /><path d="M9 10.5l7 12 7-12" stroke="#fff" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" /><circle cx="16" cy="10.5" r="1.8" fill="#b15f2c" /></svg>
              </span>
              <span className="brand__text">
                <span className="brand__name">VeriSketch<span className="brand__ai">AI</span></span>
                <span className="brand__tag">Forensic composite workspace</span>
              </span>
            </div>
          </div>

          <nav className="witness-tabs" aria-label="Witnesses">
            {witnesses.map(w => {
              const isDone = Boolean(w.selectedCandidate);
              const isActive = activeWitnessId === w.id;
              return (
                <button
                  key={w.id}
                  type="button"
                  onClick={() => {
                    setActiveWitnessId(w.id);
                  }}
                  className={`witness-tab ${isActive ? 'is-active' : ''} ${isDone ? 'is-done' : ''}`}
                  aria-current={isActive ? 'true' : undefined}
                >
                  <span className="witness-tab__id">{w.id}</span>
                  <span className="witness-tab__name">{w.name}</span>
                  {isDone && <Icon name="check" className="icon witness-tab__check" title="Match confirmed" />}
                </button>
              );
            })}
            <button
              type="button"
              onClick={addWitness}
              className="witness-tab witness-tab--add"
              title="Add Witness"
              aria-label="Add witness"
            >
              <Icon name="plus" />
            </button>
          </nav>

          <CaseClock className="app-header__clock" />
        </div>
      </header>

      <main className="app-main">
        <div className="phase-band" aria-label="Workflow progress">
          <span className="phase-band__case">
            <span className="eyebrow eyebrow--plain">Active witness</span>
            <strong>{activeWitness?.name}</strong>
          </span>
          <ol className="phase-band__pills">
            {PHASES.map((p, i) => (
              <li key={p.id} className="phase-band__item">
                {i > 0 && <span className="phase-band__arrow" aria-hidden="true"><Icon name="arrowRight" /></span>}
                <span
                  className={`phase-pill ${i === phaseIndex ? 'is-current' : ''} ${i < phaseIndex ? 'is-done' : ''}`}
                  aria-current={i === phaseIndex ? 'step' : undefined}
                >
                  <span className="phase-pill__index mono">{p.index}</span>
                  {p.label}
                </span>
              </li>
            ))}
          </ol>
        </div>

        {currentPhase === 'interview' && (
          <WitnessInterview
            key={activeWitnessId}
            apiKey={apiKey}
            advancePhase={() => setCurrentPhase('candidates')}
            onDataChange={(newData) => updateWitness(activeWitnessId, newData)}
            data={activeWitness}
          />
        )}
        {currentPhase === 'candidates' && (
          <CandidateExploration
            key={activeWitnessId}
            apiKey={apiKey}
            advancePhase={advanceAfterCandidateConfirm}
            returnPhase={() => setCurrentPhase('interview')}
            data={activeWitness}
            onDataChange={(newData) => updateWitness(activeWitnessId, newData)}
            onOpenSettings={openMenu}
          />
        )}
        {currentPhase === 'consensus' && (
          <MultiWitnessConsensus
            witnesses={witnesses}
            apiKey={apiKey}
            returnPhase={() => setCurrentPhase('candidates')}
            onOpenSettings={openMenu}
          />
        )}
      </main>

      <SiteFooter witnessCount={witnesses.length} confirmedCount={confirmedCount} />

      <NavMenu
        open={menuOpen}
        onClose={closeMenu}
        witnesses={witnesses}
        activeWitnessId={activeWitnessId}
        currentPhase={currentPhase}
        onSelectWitness={setActiveWitnessId}
        onAddWitness={addWitness}
        apiKey={apiKey}
        onApiKeyChange={handleKeyChange}
      />
    </div>
  );
}

export default App;
