import { Fragment } from 'react';

// Word-by-word masked reveal (Lumora headline style).
// Pure CSS: each word slides up from behind an overflow mask with a stagger.
// Plays once the shell is booted (after the loader) and on every remount.
const RevealText = ({ text, stagger = 0.07, delay = 0.05 }) => {
  const words = String(text).split(' ');
  return (
    <span className="reveal-text" aria-label={text} role="text">
      {words.map((word, i) => (
        <Fragment key={`${word}-${i}`}>
          <span className="reveal-text__mask" aria-hidden="true">
            <span className="reveal-text__word" style={{ animationDelay: `${delay + i * stagger}s` }}>
              {word}
            </span>
          </span>
          {i < words.length - 1 ? ' ' : null}
        </Fragment>
      ))}
    </span>
  );
};

export default RevealText;
