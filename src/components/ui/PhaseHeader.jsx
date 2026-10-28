import RevealText from './RevealText';

// Phase title block: eyebrow, line-by-line headline, description, actions,
// and a faint oversized watermark behind it.
const PhaseHeader = ({ index, eyebrow, title, description, meta, actions, watermark = 'VERISKETCH' }) => (
  <header className="phase-header">
    <span className="phase-header__watermark" aria-hidden="true">{watermark}</span>
    <div className="phase-header__text">
      <span className="eyebrow">
        {index && <span className="mono">{index}</span>}
        {eyebrow}
      </span>
      <h1 className="phase-header__title">
        <RevealText text={title} />
      </h1>
      {description && <p className="phase-header__desc">{description}</p>}
      {meta && <div className="phase-header__meta">{meta}</div>}
    </div>
    {actions && <div className="phase-header__actions">{actions}</div>}
  </header>
);

export default PhaseHeader;
