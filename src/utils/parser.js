export const parseTraits = (description) => {
  const lower = (description || "").toLowerCase();
  const extractedTraits = {};

  const extractMatch = (pattern, fallbackIdx = 1) => {
    const match = lower.match(pattern);
    return match ? match[fallbackIdx].toLowerCase().trim() : null;
  };

  const gender = extractMatch(/\b(woman|girl|lady|female|she|her|man|guy|boy|male|he|his|him)\b/i);
  if (gender) {
    let val = ['man','guy','boy','male','he','his','him'].includes(gender) ? 'male' : 'female';
    extractedTraits.gender = { value: val, confidence: 0.98 };
  }

  const ageMatch = lower.match(/\b(?:age\s+)?(\d{1,2})\b/i);
  if (ageMatch) {
    const ageNum = parseInt(ageMatch[1], 10);
    if (ageNum > 0 && ageNum < 120) {
      extractedTraits.age = { value: `${ageNum} years old`, confidence: 0.95 };
    }
  }

  const hairCol = extractMatch(/\b(dark|black|blonde|light|fair|brown|brunette|red|ginger|gray|grey|white|silver)\s+(?:hair|curls|locks)\b/i) || extractMatch(/\b(dark|black|blonde|light|brown|gray|grey)\s+hair\b/i);
  if (hairCol) {
    extractedTraits.hair = { value: hairCol, confidence: 0.90 };
  }

  const glasses = extractMatch(/\b(rectangular|round|y2k|wire|thick|thin)?\s*(glasses|spectacles|specs|sunglasses|shades)\b/i, 0);
  if (glasses) {
    extractedTraits.accessories = { value: glasses, confidence: 0.95 };
  }
  
  const ethnicity = extractMatch(/\b(arab|middle eastern|asian|hispanic|latino|caucasian|white|black|african)\b/i);
  if (ethnicity) {
    extractedTraits.ethnicity = { value: ethnicity, confidence: 0.90 };
  }

  const faceShape = extractMatch(/\b(round|square|oval|long|thin|wide|heart)\s+(?:face|head|jaw)\b/i);
  if (faceShape) {
    extractedTraits.face_shape = { value: faceShape, confidence: 0.85 };
  }

  const eyes = extractMatch(/\b(blue|brown|green|hazel|gray|grey|dark|light)\s+eyes\b/i) || extractMatch(/\b(almond|round|hooded|narrow)\s+eyes\b/i);
  if (eyes) {
    extractedTraits.eyes = { value: eyes, confidence: 0.88 };
  }

  const nose = extractMatch(/\b(crooked|straight|wide|pointy|sharp|hooked|bulbous|button|flat)\s+nose\b/i);
  if (nose) {
    extractedTraits.nose_shape = { value: nose, confidence: 0.85 };
  }

  const facialHair = extractMatch(/\b(beard|mustache|stubble|goatee|sideburns)\b/i);
  if (facialHair) {
    extractedTraits.facial_hair = { value: facialHair, confidence: 0.90 };
  }

  const lips = extractMatch(/\b(full|thick|thin|wide)\s+lips\b/i);
  if (lips) {
    extractedTraits.lips = { value: lips, confidence: 0.82 };
  }

  const headwear = extractMatch(/\b(hat|cap|beanie|hoodie|turban|hijab)\b/i);
  if (headwear) {
    extractedTraits.headwear = { value: headwear, confidence: 0.85 };
  }

  // Enhanced Skin Tone detection
  const skinKeywords = ['tan', 'pale', 'fair', 'dark', 'light', 'olive', 'clear', 'ebony', 'ivory', 'brown'];
  let foundSkinTones = [];
  skinKeywords.forEach(k => {
    if (new RegExp(`\\b${k}\\b`, 'i').test(lower)) foundSkinTones.push(k);
  });

  if (foundSkinTones.length > 0) {
    // If multiple words, like "light but still tan", join them
    // But only if they likely refer to skin (context check)
    const hasSkinContext = lower.includes('skin') || lower.includes('complexion') || lower.includes('tone') || lower.includes('face');
    if (hasSkinContext || foundSkinTones.length >= 2) {
      extractedTraits.skin_tone = { 
        value: foundSkinTones.join(' '), 
        confidence: hasSkinContext ? 0.90 : 0.75 
      };
    }
  }

  // To keep compatibility with the new async call sites, we wrap it in a promise
  return Promise.resolve({
    traits: extractedTraits,
    extractedAnyNewInfo: Object.keys(extractedTraits).length > 0
  });
};



