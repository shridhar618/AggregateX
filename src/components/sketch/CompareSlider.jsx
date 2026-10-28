import { useRef, useState } from 'react'

// Drag-to-reveal comparison. Keyboard: arrow keys move the divider.
const CompareSlider = ({ before, after, beforeLabel, afterLabel }) => {
  const [pos, setPos] = useState(50)
  const ref = useRef(null)
  const dragging = useRef(false)

  const move = (clientX) => {
    const r = ref.current.getBoundingClientRect()
    setPos(Math.max(0, Math.min(100, ((clientX - r.left) / r.width) * 100)))
  }

  return (
    <div
      ref={ref}
      className="compare"
      onPointerDown={(e) => { dragging.current = true; e.currentTarget.setPointerCapture(e.pointerId); move(e.clientX) }}
      onPointerMove={(e) => dragging.current && move(e.clientX)}
      onPointerUp={() => { dragging.current = false }}
      onPointerCancel={() => { dragging.current = false }}
    >
      <img className="compare__img" src={after} alt={afterLabel} draggable={false} />
      <div className="compare__before" style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}>
        <img className="compare__img" src={before} alt={beforeLabel} draggable={false} />
      </div>
      <span className="compare__tag compare__tag--l mono">{beforeLabel}</span>
      <span className="compare__tag compare__tag--r mono">{afterLabel}</span>
      <div
        className="compare__handle"
        style={{ left: `${pos}%` }}
        role="slider"
        tabIndex={0}
        aria-label="Comparison divider"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(pos)}
        onKeyDown={(e) => {
          if (e.key === 'ArrowLeft') setPos((p) => Math.max(0, p - 5))
          if (e.key === 'ArrowRight') setPos((p) => Math.min(100, p + 5))
        }}
      >
        <span />
      </div>
    </div>
  )
}

export default CompareSlider
