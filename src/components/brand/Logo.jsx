// Original VeriSketch mark: a scanning frame (corner reticle) around a facial
// contour, crossed by a horizontal scan line.
export const LogoMark = ({ size = 32, animated = false }) => (
  <svg
    className={`logo-mark ${animated ? 'is-animated' : ''}`}
    width={size}
    height={size}
    viewBox="0 0 32 32"
    fill="none"
    aria-hidden="true"
  >
    <rect width="32" height="32" rx="8" fill="#0d111b" stroke="#253247" />
    <g strokeLinecap="round" strokeLinejoin="round">
      <path className="logo-mark__frame" d="M6 11V7.5A1.5 1.5 0 0 1 7.5 6H11M21 6h3.5A1.5 1.5 0 0 1 26 7.5V11M26 21v3.5a1.5 1.5 0 0 1-1.5 1.5H21M11 26H7.5A1.5 1.5 0 0 1 6 24.5V21" stroke="#28D7F2" strokeWidth="1.6" />
      <path className="logo-mark__face" d="M16 9c-3.4 0-5.6 2.4-5.6 6 0 3.6 2.1 7 5.6 8 3.5-1 5.6-4.4 5.6-8 0-3.6-2.2-6-5.6-6z" stroke="#F3F6FC" strokeWidth="1.5" />
      <path className="logo-mark__scan" d="M8.5 15.5h15" stroke="#28D7F2" strokeWidth="1.3" />
    </g>
  </svg>
)

export const Wordmark = ({ compact = false }) => (
  <span className="wordmark">
    <span className="wordmark__name">
      VeriSketch<span className="wordmark__ai">AI</span>
    </span>
    {!compact && <span className="wordmark__tag">Forensic composite workspace</span>}
  </span>
)
