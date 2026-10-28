import { useRef } from 'react';
import { useSpring } from '../../hooks/useSpring';

// Spring-driven progress meter (scaleX keeps it on the compositor).
const Meter = ({ value, color, label }) => {
  const fillRef = useRef(null);
  const clamped = Math.max(0, Math.min(100, value));
  useSpring(clamped, (v) => {
    if (fillRef.current) fillRef.current.style.transform = `scaleX(${Math.max(0, Math.min(1.02, v / 100))})`;
  }, { stiffness: 90, damping: 16 });

  return (
    <div className="meter" role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(clamped)}>
      <span ref={fillRef} className="meter__fill" style={{ background: color, transform: 'scaleX(0)' }} />
    </div>
  );
};

export default Meter;
