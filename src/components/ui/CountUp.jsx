import { useRef } from 'react';
import { useSpring } from '../../hooks/useSpring';

// Spring count-up (Lumora stats). Screen readers get the final value directly.
const CountUp = ({ value, className = '' }) => {
  const ref = useRef(null);
  useSpring(value, (v) => {
    if (ref.current) ref.current.textContent = String(Math.max(0, Math.round(v)));
  });

  return (
    <>
      <span ref={ref} className={`mono ${className}`} aria-hidden="true">0</span>
      <span className="sr-only">{Math.round(value)}</span>
    </>
  );
};

export default CountUp;
