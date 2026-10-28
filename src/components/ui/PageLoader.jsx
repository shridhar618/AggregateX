import { useEffect, useRef, useState } from 'react';
import { markBooted } from '../../utils/boot';

const DURATION_MS = 1500;
const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

// Full-screen ink intro: counts 000 → 100, then slides up and unmounts.
const PageLoader = ({ onDone }) => {
  const counterRef = useRef(null);
  const barRef = useRef(null);
  const [leaving, setLeaving] = useState(false);
  const [gone, setGone] = useState(false);
  const onDoneRef = useRef(onDone);

  useEffect(() => {
    onDoneRef.current = onDone;
  }, [onDone]);

  useEffect(() => {
    const reduced = prefersReducedMotion();
    const total = reduced ? 1 : DURATION_MS;
    const start = performance.now();
    let raf = 0;
    let exitTimer = 0;

    const tick = (t) => {
      const p = Math.min(1, (t - start) / total);
      // ease-in-out so the count lingers at both ends, like the reference
      const eased = p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
      const value = Math.round(eased * 100);
      if (counterRef.current) counterRef.current.textContent = String(value).padStart(3, '0');
      if (barRef.current) barRef.current.style.transform = `scaleX(${eased})`;
      if (p < 1) {
        raf = requestAnimationFrame(tick);
      } else {
        setLeaving(true);
        markBooted();
        onDoneRef.current?.();
        exitTimer = setTimeout(() => setGone(true), reduced ? 0 : 900);
      }
    };
    raf = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(exitTimer);
    };
  }, []);

  if (gone) return null;

  return (
    <div className={`page-loader surface-ink ${leaving ? 'is-leaving' : ''}`} role="status" aria-live="polite">
      <div className="page-loader__top">
        <span className="page-loader__brand">VeriSketch AI</span>
        <span className="eyebrow eyebrow--plain">Forensic composite workspace</span>
      </div>
      <div className="page-loader__bottom">
        <span className="page-loader__label">Initializing case workspace</span>
        <span ref={counterRef} className="page-loader__count mono" aria-hidden="true">000</span>
      </div>
      <div className="page-loader__bar" aria-hidden="true">
        <span ref={barRef} />
      </div>
      <span className="sr-only">Loading VeriSketch AI</span>
    </div>
  );
};

export default PageLoader;
