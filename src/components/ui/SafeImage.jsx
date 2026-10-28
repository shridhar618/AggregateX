import { useState } from 'react';
import Icon from './Icon';

// <img> that degrades to a neutral tile when the source fails to load
// (e.g. the external placeholder service is unreachable), instead of a broken icon.
const SafeImage = ({ src, alt, className = '', style, fallbackLabel = 'Image unavailable' }) => {
  const [failedSrc, setFailedSrc] = useState(null);
  if (!src || failedSrc === src) {
    return (
      <span className={`safe-image__fallback ${className}`} role="img" aria-label={`${alt} (${fallbackLabel.toLowerCase()})`}>
        <Icon name="image" />
        <span>{fallbackLabel}</span>
      </span>
    );
  }
  return <img src={src} alt={alt} className={className} style={style} onError={() => setFailedSrc(src)} />;
};

export default SafeImage;
