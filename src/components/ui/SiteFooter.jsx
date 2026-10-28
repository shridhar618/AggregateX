// Ink footer with disclaimer and oversized watermark.
const SiteFooter = ({ witnessCount, confirmedCount }) => (
  <footer className="site-footer surface-ink">
    <div className="site-footer__inner">
      <div className="site-footer__cols">
        <div className="site-footer__lead">
          <span className="eyebrow">VeriSketch AI</span>
          <p>
            AI-assisted composite reconstruction from witness testimony. Every composite is an investigative lead,
            not evidence of identity.
          </p>
        </div>
        <dl className="site-footer__meta">
          <div>
            <dt>Witnesses</dt>
            <dd className="mono">{String(witnessCount).padStart(2, '0')}</dd>
          </div>
          <div>
            <dt>Confirmed</dt>
            <dd className="mono">{String(confirmedCount).padStart(2, '0')}</dd>
          </div>
          <div>
            <dt>Image model</dt>
            <dd>Gemini</dd>
          </div>
        </dl>
      </div>
      <div className="site-footer__mark" aria-hidden="true">VERISKETCH</div>
    </div>
  </footer>
);

export default SiteFooter;
