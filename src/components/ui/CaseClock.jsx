import { useEffect, useState } from 'react';

const formatTime = (date) =>
  date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

const zoneLabel = (() => {
  try {
    const parts = new Intl.DateTimeFormat([], { timeZoneName: 'short' }).formatToParts(new Date());
    return parts.find((p) => p.type === 'timeZoneName')?.value || 'LOCAL';
  } catch {
    return 'LOCAL';
  }
})();

// Live local clock — a timestamp anchor for the case session.
const CaseClock = ({ className = '' }) => {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className={`case-clock ${className}`} aria-label={`Local time ${formatTime(now)}`}>
      <span className="case-clock__dot" aria-hidden="true" />
      <time className="mono" dateTime={now.toISOString()}>{formatTime(now)}</time>
      <span className="case-clock__zone">{zoneLabel}</span>
    </div>
  );
};

export default CaseClock;
