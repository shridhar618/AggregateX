import { useEffect, useRef, useState } from 'react';

const BRUSH_LIFE_MS = 1100;

const reducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

// Draw `img` into a w×h box with object-fit: cover semantics.
const drawCover = (ctx, img, w, h) => {
  const ir = img.naturalWidth / img.naturalHeight;
  const br = w / h;
  let sw = img.naturalWidth;
  let sh = img.naturalHeight;
  let sx = 0;
  let sy = 0;
  if (ir > br) {
    sw = sh * br;
    sx = (img.naturalWidth - sw) / 2;
  } else {
    sh = sw / br;
    sy = (img.naturalHeight - sh) / 2;
  }
  ctx.drawImage(img, sx, sy, sw, sh, 0, 0, w, h);
};

/**
 * Lumora-style "liquid" cursor reveal.
 * The base image (the composite) is always visible. Moving the pointer paints a
 * soft, fading brush trail that reveals a witness's selected sketch underneath.
 * A toggle button shows the full comparison for keyboard and touch users.
 * Pixels are never read back, so cross-origin placeholder images are safe to draw.
 */
const LiquidReveal = ({ baseSrc, baseAlt, baseBadge = null, compareSources = [] }) => {
  const wrapRef = useRef(null);
  const canvasRef = useRef(null);
  const maskRef = useRef(null);
  const imgRef = useRef(null);
  const pointsRef = useRef([]);
  const rafRef = useRef(0);
  const sizeRef = useRef({ w: 0, h: 0, dpr: 1 });
  const holdRef = useRef(false);

  const [activeId, setActiveId] = useState(compareSources[0]?.id ?? null);
  const [hold, setHold] = useState(false);
  const active = compareSources.find((c) => c.id === activeId) || compareSources[0] || null;
  const activeSrc = active?.src;

  // Render loop: rebuild the mask from live brush points, then composite.
  const renderRef = useRef(() => {});
  useEffect(() => {
    renderRef.current = () => {
      const canvas = canvasRef.current;
      const mask = maskRef.current;
      const img = imgRef.current;
      if (!canvas || !mask) return;
      const { w, h, dpr } = sizeRef.current;
      const ctx = canvas.getContext('2d');
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (!img || !img.complete || !img.naturalWidth || w === 0) return;

      if (holdRef.current) {
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        drawCover(ctx, img, w, h);
        return;
      }

      const now = performance.now();
      pointsRef.current = pointsRef.current.filter((p) => now - p.t < BRUSH_LIFE_MS);
      const points = pointsRef.current;
      if (points.length === 0) return;

      const mctx = mask.getContext('2d');
      mctx.setTransform(1, 0, 0, 1, 0, 0);
      mctx.clearRect(0, 0, mask.width, mask.height);
      mctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const baseRadius = Math.max(48, Math.min(w, h) * 0.17);
      for (const p of points) {
        const age = (now - p.t) / BRUSH_LIFE_MS;
        const alpha = 1 - age * age;
        const r = baseRadius * (0.75 + age * 0.55);
        const g = mctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, r);
        g.addColorStop(0, `rgba(0,0,0,${0.9 * alpha})`);
        g.addColorStop(0.55, `rgba(0,0,0,${0.55 * alpha})`);
        g.addColorStop(1, 'rgba(0,0,0,0)');
        mctx.fillStyle = g;
        mctx.beginPath();
        mctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        mctx.fill();
      }

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      drawCover(ctx, img, w, h);
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.globalCompositeOperation = 'destination-in';
      ctx.drawImage(mask, 0, 0);
      ctx.globalCompositeOperation = 'source-over';
    };
  });

  const loop = () => {
    renderRef.current();
    if (pointsRef.current.length > 0) {
      rafRef.current = requestAnimationFrame(loop);
    } else {
      rafRef.current = 0;
    }
  };

  const kick = () => {
    if (!rafRef.current) rafRef.current = requestAnimationFrame(loop);
  };

  // Keep canvases sized to the element (and device pixel ratio).
  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return undefined;
    if (!maskRef.current) maskRef.current = document.createElement('canvas');
    const resize = () => {
      const rect = wrap.getBoundingClientRect();
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      sizeRef.current = { w: rect.width, h: rect.height, dpr };
      for (const c of [canvasRef.current, maskRef.current]) {
        if (!c) continue;
        c.width = Math.round(rect.width * dpr);
        c.height = Math.round(rect.height * dpr);
      }
      renderRef.current();
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(wrap);
    return () => {
      ro.disconnect();
      cancelAnimationFrame(rafRef.current);
      rafRef.current = 0;
    };
  }, []);

  // Load the comparison image whenever the selected witness changes.
  useEffect(() => {
    if (!activeSrc) {
      imgRef.current = null;
      return undefined;
    }
    const img = new Image();
    img.decoding = 'async';
    img.onload = () => renderRef.current();
    img.src = activeSrc;
    imgRef.current = img;
    return () => {
      img.onload = null;
    };
  }, [activeSrc]);

  useEffect(() => {
    holdRef.current = hold;
    renderRef.current();
  }, [hold]);

  const handlePointerMove = (e) => {
    if (!active || hold) return;
    const rect = wrapRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const now = performance.now();
    const pts = pointsRef.current;
    const last = pts[pts.length - 1];
    // Interpolate so fast strokes stay continuous.
    if (last && !reducedMotion()) {
      const dist = Math.hypot(x - last.x, y - last.y);
      const steps = Math.min(12, Math.floor(dist / 14));
      for (let i = 1; i <= steps; i++) {
        const k = i / (steps + 1);
        pts.push({ x: last.x + (x - last.x) * k, y: last.y + (y - last.y) * k, t: now });
      }
    }
    pts.push({ x, y, t: now });
    if (pts.length > 240) pts.splice(0, pts.length - 240);
    kick();
  };

  return (
    <div className="liquid-reveal-wrap">
      <div
        ref={wrapRef}
        className={`liquid-reveal ${active ? 'is-interactive' : ''}`}
        onPointerMove={handlePointerMove}
      >
        <img className="liquid-reveal__base" src={baseSrc} alt={baseAlt} draggable={false} />
        <canvas ref={canvasRef} className="liquid-reveal__canvas" aria-hidden="true" />
        {active && hold ? (
          <span className={`badge ${active.isPlaceholder ? 'badge--placeholder' : 'badge--ai'} liquid-reveal__tag`}>
            {active.label} sketch{active.isPlaceholder ? ' · placeholder' : ''}
          </span>
        ) : (
          baseBadge && <span className="liquid-reveal__tag">{baseBadge}</span>
        )}
      </div>

      {compareSources.length > 0 && (
        <div className="liquid-reveal__controls">
          <span className="liquid-reveal__hint">
            Move across the composite to reveal a witness&rsquo;s selected sketch.
          </span>
          <div className="liquid-reveal__chips" role="group" aria-label="Compare with witness">
            {compareSources.map((c) => (
              <button
                key={c.id}
                type="button"
                className={`chip liquid-reveal__chip ${c.id === active?.id ? 'is-active' : ''}`}
                aria-pressed={c.id === active?.id}
                onClick={() => setActiveId(c.id)}
              >
                {c.label}
                {c.isPlaceholder && <span className="liquid-reveal__ph">placeholder</span>}
              </button>
            ))}
            <button
              type="button"
              className={`chip liquid-reveal__chip ${hold ? 'is-active' : ''}`}
              aria-pressed={hold}
              onClick={() => setHold((v) => !v)}
            >
              {hold ? 'Show composite' : 'Show full sketch'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default LiquidReveal;
