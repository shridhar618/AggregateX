// Real Gemini output is always stored as an inline `data:image/...` URL.
// Anything else (e.g. the pravatar.cc stand-ins used when generation fails)
// is a placeholder and must never be presented as an AI-generated sketch.
export const isGeneratedImage = (src) => typeof src === 'string' && src.startsWith('data:image/');

export const isPlaceholderImage = (src) => Boolean(src) && !isGeneratedImage(src);
