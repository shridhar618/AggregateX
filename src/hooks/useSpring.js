import { useEffect, useRef } from 'react';
import { whenBooted } from '../utils/boot';

const reducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

/**
 * Minimal rAF spring (replaces react-spring for this app).
 * Animates from the previous value toward `target` and reports each frame via
 * `onFrame(value)` — writing straight to the DOM, so no React re-renders.
 * The first run waits for the intro loader to finish.
 */
export const useSpring = (target, onFrame, { from = 0, stiffness = 120, damping = 20, mass = 1 } = {}) => {
  const state = useRef({ value: from, velocity: 0 });
  const raf = useRef(0);
  const frameRef = useRef(onFrame);

  useEffect(() => {
    frameRef.current = onFrame;
  });

  useEffect(() => {
    const s = state.current;
    let cancelled = false;

    const start = () => {
      if (cancelled) return;
      if (reducedMotion()) {
        s.value = target;
        s.velocity = 0;
        frameRef.current(target);
        return;
      }
      let last = performance.now();
      const step = (now) => {
        const dt = Math.min(0.064, (now - last) / 1000);
        last = now;
        const force = -stiffness * (s.value - target) - damping * s.velocity;
        s.velocity += (force / mass) * dt;
        s.value += s.velocity * dt;
        if (Math.abs(s.velocity) < 0.01 && Math.abs(s.value - target) < 0.01) {
          s.value = target;
          s.velocity = 0;
          frameRef.current(target);
          return;
        }
        frameRef.current(s.value);
        raf.current = requestAnimationFrame(step);
      };
      cancelAnimationFrame(raf.current);
      raf.current = requestAnimationFrame(step);
    };

    frameRef.current(s.value);
    const unsubscribe = whenBooted(start);
    return () => {
      cancelled = true;
      unsubscribe();
      cancelAnimationFrame(raf.current);
    };
  }, [target, stiffness, damping, mass]);
};
