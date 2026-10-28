import CountUp from './CountUp';
import Meter from './Meter';

// Ink stats panel for Case Completeness. Purely presentational:
// every value is computed by the phase component that renders it.
const CompletenessPanel = ({ score, toneColor, stats }) => (
  <section className="stats-panel surface-ink" aria-labelledby="completeness-title">
    <div className="stats-panel__head">
      <h2 id="completeness-title" className="stats-panel__title">Case Completeness</h2>
      <span className="eyebrow eyebrow--plain">Live</span>
    </div>
    <div className="stats-panel__score" style={{ color: toneColor }}>
      <CountUp value={score} className="stats-panel__number" />
      <span className="stats-panel__unit">%</span>
    </div>
    <Meter value={score} color={toneColor} label="Case completeness" />
    <dl className="stats-panel__grid">
      {stats.map((s) => (
        <div key={s.label} className="stats-panel__cell">
          <dt>{s.label}</dt>
          <dd style={{ color: s.color }}>{s.value}</dd>
        </div>
      ))}
    </dl>
  </section>
);

export default CompletenessPanel;
