import { useState, useEffect } from 'react';
import { parseTraits } from '../utils/parser';
import { isPlaceholderImage } from '../utils/imageSource';
import PhaseHeader from './ui/PhaseHeader';
import CompletenessPanel from './ui/CompletenessPanel';
import Icon from './ui/Icon';
import SafeImage from './ui/SafeImage';

const initialGenerationLocks = new Set();
const CONFIDENCE_LEVELS = {
  low: { label: 'Not so confident', value: 0.45 },
  mid: { label: 'Middle', value: 0.75 },
  high: { label: 'Very confident', value: 0.92 }
};

const CORE_TRAITS = ['gender', 'age', 'hair', 'eyes', 'face_shape', 'nose_shape', 'skin_tone'];

const TRAIT_LABELS = {
  gender: 'Gender',
  age: 'Age',
  hair: 'Hair',
  eyes: 'Eyes',
  face_shape: 'Face shape',
  nose_shape: 'Nose shape',
  skin_tone: 'Skin tone'
};

const CONTRADICTION_RULES = [
  {
    label: 'Eye color',
    patterns: [
      { label: 'blue', regex: /\bblue\s+eyes\b/i },
      { label: 'brown', regex: /\bbrown\s+eyes\b/i },
      { label: 'green', regex: /\bgreen\s+eyes\b/i },
      { label: 'hazel', regex: /\bhazel\s+eyes\b/i },
      { label: 'gray', regex: /\b(?:gray|grey)\s+eyes\b/i }
    ]
  },
  {
    label: 'Hair color',
    patterns: [
      { label: 'black', regex: /\bblack\s+hair\b/i },
      { label: 'brown', regex: /\bbrown\s+hair\b/i },
      { label: 'blonde', regex: /\bblonde\s+hair\b/i },
      { label: 'red', regex: /\b(?:red|ginger)\s+hair\b/i },
      { label: 'gray', regex: /\b(?:gray|grey|white|silver)\s+hair\b/i }
    ]
  }
];

const findContradictions = (description = '') => {
  if (!description.trim()) return [];

  return CONTRADICTION_RULES.map(rule => {
    const matched = rule.patterns.filter(p => p.regex.test(description)).map(p => p.label);
    if (matched.length > 1) {
      return `${rule.label}: ${matched.join(' vs ')}`;
    }
    return null;
  }).filter(Boolean);
};

const CandidateExploration = ({ apiKey, advancePhase, returnPhase, data, onDataChange, onOpenSettings }) => {
  const candidates = data.candidates || [];
  const selectedCandidate = data.selectedCandidate || null;
  const refinements = data.refinements || [];
  const generationCount = data.generationCount || 1;

  const setSelectedCandidate = (id) => onDataChange({ selectedCandidate: id });

  const [refinementInput, setRefinementInput] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [isFallbackActive, setIsFallbackActive] = useState(false);
  const [confidenceSelections, setConfidenceSelections] = useState({});

  const traits = data.structuredTraits || {};
  const traitsList = Object.keys(traits);
  const isFemale = traits.gender?.value === 'female';

  // Build the prompt using confidence to adjust adjectives
  const getPromptWithConfidence = (sourceTraits = traits) => {
    const genderTrait = sourceTraits.gender?.value?.toLowerCase() || 'person';
    const isFemale = genderTrait.includes('female') || genderTrait.includes('woman');
    const genderAnchor = isFemale ? "A passport-style identification portrait of a woman" : "A passport-style identification portrait of a man";

    const features = Object.entries(sourceTraits)
      .filter(([key]) => key !== 'unidentified_features' && key !== 'gender')
      .map(([, trait]) => {
        const val = trait.value;
        const conf = trait.confidence;
        if (conf >= 0.9) return `very prominent ${val}`;
        if (conf >= 0.75) return `distinctive ${val}`;
        if (conf < 0.6) return `subtle or vague ${val}`;
        return val;
      })
      .join(', ');

    return `${genderAnchor}, ${features}`;
  };

  const basePrompt = getPromptWithConfidence();

  const lowConfidenceTraits = Object.entries(traits)
    .filter(([, t]) => t.confidence < 0.6)
    .map(([key]) => key.replaceAll('_', ' '));
  const mediumConfidenceTraits = Object.entries(traits)
    .filter(([, t]) => t.confidence >= 0.6 && t.confidence < 0.8)
    .map(([key]) => key.replaceAll('_', ' '));

  const missingCoreTraits = CORE_TRAITS.filter(key => !traits[key]).map(key => TRAIT_LABELS[key]);
  const contradictions = findContradictions(data.faceDescription || '');
  const coverageRatio = (CORE_TRAITS.length - missingCoreTraits.length) / CORE_TRAITS.length;
  const confidenceValues = Object.values(traits).map(t => t.confidence).filter(Number.isFinite);
  const avgConfidence = confidenceValues.length
    ? confidenceValues.reduce((sum, value) => sum + value, 0) / confidenceValues.length
    : 0;
  const caseCompletenessScore = Math.max(
    0,
    Math.min(
      100,
      Math.round((coverageRatio * 65) + (avgConfidence * 35) - (contradictions.length * 12))
    )
  );
  const scoreTone = caseCompletenessScore >= 75
    ? 'var(--success)'
    : caseCompletenessScore >= 45
      ? 'var(--warning)'
      : 'var(--danger)';

  const needsClarification = lowConfidenceTraits.length > 0;
  const hasPendingConfidenceSelection = Object.values(confidenceSelections).some(Boolean);

  const getConfidenceLevel = (confidence) => {
    if (confidence >= 0.9) return 'high';
    if (confidence >= 0.6) return 'mid';
    return 'low';
  };

  const applyConfidenceSelections = (baseTraits) => {
    let hasSelection = false;
    const updatedTraits = { ...baseTraits };
    const summary = [];

    Object.entries(confidenceSelections).forEach(([key, level]) => {
      if (!level || !updatedTraits[key]) return;
      hasSelection = true;
      updatedTraits[key] = {
        ...updatedTraits[key],
        confidence: CONFIDENCE_LEVELS[level].value
      };
      summary.push(`${key.replaceAll('_', ' ')}: ${CONFIDENCE_LEVELS[level].label}`);
    });

    return { updatedTraits, hasSelection, summary };
  };

  const doGeneration = async (currentPrompt, newGenCount, options = {}) => {
    const { lockKey } = options;
    setIsGenerating(true);
    setIsFallbackActive(false);
    try {
      // Style enforcement
      const styleExt = "single-subject passport photo style, face centered and straight to camera, head and upper shoulders visible, neutral plain background, balanced framing, photorealistic high quality, consistent lighting, no dramatic shadows, NO text, NO numbers, NO logos, NO watermark, NO frames, NO borders";
      const fullPrompt = `${currentPrompt}, ${styleExt}`;

      const generateSingle = async (seedIndex) => {
        try {
          const entropy = Math.random().toString(36).substring(7);
          const parts = [{ text: `${fullPrompt}. Unique Variant ID: ${entropy}. Subtle artistic shift ${seedIndex}.` }];

          if (data.sourceImage) {
            const [header, base64Data] = data.sourceImage.split(',');
            const mimeType = header.split(':')[1].split(';')[0];
            parts.push({
              inlineData: {
                mimeType: mimeType,
                data: base64Data
              }
            });
          }

          const seed = Math.floor(Math.random() * 1000000);
          const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent?key=${apiKey}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              contents: [{ parts: parts }],
              generationConfig: {
                responseModalities: ["IMAGE"],
                seed: seed
              }
            })
          });
          if (!res.ok) {
            return { image: null, issue: true };
          }
          const resData = await res.json();
          if (resData.candidates?.[0]?.content?.parts?.[0]?.inlineData) {
            const inline = resData.candidates[0].content.parts[0].inlineData;
            return { image: `data:${inline.mimeType};base64,${inline.data}`, issue: false };
          } else if (resData.error) {
            console.error("Gemini API Error:", resData.error.message);
            return { image: null, issue: true };
          }
          return { image: null, issue: false };
        } catch (err) {
          console.error("Fetch failed:", err);
          return { image: null, issue: true };
        }
      };

      const generationResults = await Promise.all([generateSingle(1), generateSingle(2), generateSingle(3)]);
      const imgs = generationResults.map(result => result.image);
      const allFallback = imgs.every(img => img === null);
      const hasRealApiIssue = generationResults.some(result => result.issue);
      setIsFallbackActive(allFallback && hasRealApiIssue);

      const newCands = imgs.map((imgUrl, idx) => ({
        id: `${idx + 1}-${newGenCount}`,
        label: `Generation ${newGenCount}.${idx + 1}`,
        notes: newGenCount > 1 ? `Applied: "${refinements[refinements.length - 1] || 'Refinements'}"` : 'Initial baseline',
        image: imgUrl || (isFemale ? `https://i.pravatar.cc/300?u=fallback-f${idx}-${newGenCount}` : `https://i.pravatar.cc/300?u=fallback-m${idx}-${newGenCount}`),
        filter: 'none'
      }));

      onDataChange({ candidates: newCands, generationCount: newGenCount });
    } finally {
      if (lockKey) {
        initialGenerationLocks.delete(lockKey);
      }
      setIsGenerating(false);
    }
  };

  useEffect(() => {
    if (!apiKey || candidates.length > 0 || isGenerating) return;

    const lockKey = `${data.id || 'witness'}-initial`;
    if (initialGenerationLocks.has(lockKey)) return;

    initialGenerationLocks.add(lockKey);
    doGeneration(basePrompt, 1, { lockKey });
  }, [apiKey, candidates.length, isGenerating, basePrompt, data.id]);

  const handleRefine = async () => {
    if (!selectedCandidate || !apiKey) return;

    const typedRefinement = refinementInput.trim();
    const currentTraits = data.structuredTraits || {};

    let parsedTraits = {};
    if (typedRefinement) {
      const parsed = await parseTraits(typedRefinement, apiKey, currentTraits);
      parsedTraits = parsed?.traits || {};
    }

    const mergedTraits = {
      ...currentTraits,
      ...parsedTraits
    };

    const { updatedTraits, hasSelection, summary } = applyConfidenceSelections(mergedTraits);
    if (!typedRefinement && !hasSelection) return;

    const baseCand = candidates.find(c => c.id === selectedCandidate);
    const baseLabel = baseCand ? baseCand.label : 'Previous Candidate';

    const refinementSegments = [];
    if (typedRefinement) {
      refinementSegments.push(`[Based on ${baseLabel}]: ${typedRefinement}`);
    }
    if (hasSelection) {
      refinementSegments.push(`[Confidence update]: ${summary.join(', ')}`);
    }

    const refinementNote = refinementSegments.join(' | ');
    const newRefinements = [...refinements, refinementNote];
    const nextGen = generationCount + 1;
    const adjustedBasePrompt = getPromptWithConfidence(updatedTraits);
    const newPrompt = [adjustedBasePrompt, ...newRefinements].join(', ');

    setRefinementInput('');
    setConfidenceSelections({});

    onDataChange({
      faceDescription: typedRefinement
        ? (data.faceDescription || "") + " | [Refinement]: " + typedRefinement
        : (data.faceDescription || ""),
      structuredTraits: updatedTraits,
      refinements: newRefinements,
      selectedCandidate: null,
      generationCount: nextGen
    });

    doGeneration(newPrompt, nextGen);
  };

  // ---- Presentation-only derived values (redesign) ----
  const placeholderCount = candidates.filter(c => isPlaceholderImage(c.image)).length;
  const selectedCandidateObj = candidates.find(c => c.id === selectedCandidate);
  const selectedIsPlaceholder = Boolean(selectedCandidateObj && isPlaceholderImage(selectedCandidateObj.image));

  return (
    <div className="phase phase--candidates animate-fade-in">
      <PhaseHeader
        index="02"
        eyebrow={`Candidate refinement · ${data.name}`}
        title="Candidate Exploration"
        description="Select the closest match or refine features."
        meta={
          <>
            <span className="chip mono">Iteration {generationCount}</span>
            {refinements.length > 0 && <span className="chip">{refinements.length} refinement{refinements.length > 1 ? 's' : ''} applied</span>}
          </>
        }
        actions={
          <>
            <button className="btn" onClick={returnPhase}>
              <Icon name="arrowLeft" />
              Refine Description
            </button>
            <div className="confirm-group">
              <button
                className="btn btn-primary"
                onClick={advancePhase}
                disabled={!selectedCandidate || needsClarification}
              >
                {needsClarification ? <><Icon name="lock" /> Locked</> : <>Confirm Match <Icon name="arrowRight" /></>}
              </button>
              {needsClarification && (
                <span className="confirm-group__note text-warning">
                  Clarification: <b>{lowConfidenceTraits[0]}</b>
                </span>
              )}
              {!needsClarification && selectedIsPlaceholder && (
                <span className="confirm-group__note text-warning">
                  Selected image is a placeholder, not a generated sketch
                </span>
              )}
            </div>
          </>
        }
      />

      {/* Generation status — placeholders are never presented as AI output */}
      {!isGenerating && apiKey && isFallbackActive && (
        <div className="notice notice--danger" role="alert">
          <Icon name="alert" />
          <div>
            <strong>Image generation failed.</strong> Gemini returned an error for every slot, so the images below are
            stock placeholder photos, not AI-generated sketches. Check your Gemini key in the Menu. To request new images,
            select a card and submit a refinement.
          </div>
        </div>
      )}
      {!isGenerating && apiKey && !isFallbackActive && placeholderCount > 0 && (
        <div className="notice notice--placeholder" role="status">
          <Icon name="info" />
          <div>
            <strong>{placeholderCount} of {candidates.length} images are placeholders.</strong> Gemini did not return an
            image for {placeholderCount === 1 ? 'that slot' : 'those slots'}, so a stock photo is shown instead. These cards
            are marked <b>Placeholder</b> and are not AI-generated sketches.
          </div>
        </div>
      )}

      {isGenerating ? (
        <div className="candidate-zone" aria-busy="true">
          <div className="candidate-grid">
            {[1, 2, 3].map((slot) => (
              <div key={slot} className="candidate-card candidate-card--loading surface-ink">
                <div className="candidate-card__media skeleton" />
                <div className="candidate-card__body">
                  <div className="skeleton" style={{ height: '18px', width: '55%' }} />
                  <div className="skeleton" style={{ height: '12px', width: '85%', marginTop: '12px' }} />
                  <div className="skeleton" style={{ height: '12px', width: '70%', marginTop: '8px' }} />
                </div>
              </div>
            ))}
          </div>
          <div className="generating-note" role="status">
            <span className="spinner" aria-hidden="true" />
            Generating candidate portraits with Gemini…
          </div>
        </div>
      ) : (
        <>
          {/* Candidates Grid */}
          {!apiKey ? (
            <div className="key-required surface-ink">
              <Icon name="key" className="icon key-required__icon" />
              <h2>Missing API Key</h2>
              <p>Add your Gemini API key in the Menu to enable image generation. The key stays in this browser.</p>
              {onOpenSettings && (
                <button type="button" className="btn btn-primary" onClick={onOpenSettings}>
                  Open menu
                  <Icon name="arrowRight" />
                </button>
              )}
            </div>
          ) : candidates.length === 0 ? (
            <div className="empty-state empty-state--large">
              <Icon name="image" />
              <span>No candidates yet.</span>
            </div>
          ) : (
            <div className="candidate-grid" role="radiogroup" aria-label="Candidate sketches">
              {candidates.map(candidate => {
                const isSelected = selectedCandidate === candidate.id;
                const isPlaceholder = isPlaceholderImage(candidate.image);
                return (
                  <button
                    type="button"
                    role="radio"
                    aria-checked={isSelected}
                    key={candidate.id}
                    className={`candidate-card surface-ink hover-card ${isSelected ? 'is-selected' : ''} ${isPlaceholder ? 'is-placeholder' : ''}`}
                    onClick={() => setSelectedCandidate(candidate.id)}
                  >
                    <div className="candidate-card__media">
                      <SafeImage src={candidate.image} alt={isPlaceholder ? `${candidate.label} — stock placeholder photo` : `${candidate.label} — AI-generated candidate`} style={{ filter: candidate.filter }} fallbackLabel={isPlaceholder ? 'Placeholder unavailable' : 'Image unavailable'} />
                      {isPlaceholder ? (
                        <>
                          <span className="candidate-card__hatch" aria-hidden="true" />
                          <span className="badge badge--placeholder candidate-card__badge">
                            <Icon name="alert" /> Placeholder
                          </span>
                          <span className="candidate-card__stamp" aria-hidden="true">Not AI-generated</span>
                        </>
                      ) : (
                        <span className="badge badge--ai candidate-card__badge">
                          <Icon name="sparkle" /> AI-generated
                        </span>
                      )}
                      {isSelected && (
                        <span className="candidate-card__check" aria-hidden="true"><Icon name="check" strokeWidth={2.4} /></span>
                      )}
                    </div>
                    <div className="candidate-card__body">
                      <h3 className="candidate-card__label">{candidate.label}</h3>
                      <p className="candidate-card__notes">{candidate.notes}</p>
                      {isPlaceholder && (
                        <p className="candidate-card__warning">
                          Stock photo stand-in. Gemini did not return an image for this slot.
                        </p>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {/* Refinement Input Box */}
          <section className="panel refine-bar" aria-label="Refine selected candidate">
            {needsClarification ? (
              <p className="refine-bar__status text-warning">
                <Icon name="alert" /> Please provide more details about the <b>{lowConfidenceTraits[0]}</b> to increase certainty before confirming.
              </p>
            ) : !selectedCandidate ? (
              <p className="refine-bar__status text-secondary">
                <Icon name="info" /> Select a candidate above to refine it locally
              </p>
            ) : (
              <p className="refine-bar__status text-success">
                <Icon name="check" /> Refining Candidate {selectedCandidateObj?.label}
              </p>
            )}
            <div className="refine-bar__row">
              <input
                type="text"
                className="input-field"
                placeholder="e.g., 'Make the eyes closer together', 'Straighter hair', 'Lighter skin tone'"
                value={refinementInput}
                onChange={(e) => setRefinementInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleRefine()}
                disabled={!selectedCandidate}
                aria-label="Refinement instruction"
              />
              <button
                className="btn btn-primary"
                onClick={handleRefine}
                disabled={(!refinementInput.trim() && !hasPendingConfidenceSelection) || !selectedCandidate}
              >
                <Icon name="sparkle" />
                Refine Selected
              </button>
            </div>
          </section>
        </>
      )}

      <div className="candidates-lower">
        <section className="panel constraints-panel" aria-labelledby="constraints-title">
          <div className="panel-head">
            <div>
              <h2 id="constraints-title" className="panel-title">Extracted Schema Constraints &amp; Confidence</h2>
              <p className="panel-sub">Adjust confidence, then use Refine Selected to regenerate.</p>
            </div>
            <span className="chip mono">{traitsList.length} traits</span>
          </div>
          <div className="constraints-panel__scroll">
            {traitsList.length === 0 ? (
              <div className="empty-state">
                <Icon name="scan" />
                <span>No specific traits extracted.</span>
              </div>
            ) : (
              <ul className="trait-list">
                {traitsList.map((key, i) => {
                  const trait = traits[key];
                  const isLowConfidence = trait.confidence < 0.6;
                  return (
                    <li key={key} className={`trait-row ${isLowConfidence ? 'is-low' : ''}`}>
                      <span className="trait-row__index mono">{String(i + 1).padStart(2, '0')}</span>
                      <span className="trait-row__name">{key.replaceAll('_', ' ')}</span>
                      <span className="trait-row__value">{trait.value}</span>
                      <select
                        className="select trait-row__select"
                        aria-label={`Confidence update for ${key.replaceAll('_', ' ')}`}
                        value={confidenceSelections[key] || ''}
                        onChange={(e) => {
                          const newLevel = e.target.value;
                          setConfidenceSelections(prev => ({
                            ...prev,
                            [key]: newLevel
                          }));
                        }}
                      >
                        <option value="">Optional: keep current</option>
                        <option value="low">Not so confident</option>
                        <option value="mid">Middle</option>
                        <option value="high">Very confident</option>
                      </select>
                      <span className={`trait-row__level ${isLowConfidence ? 'text-warning' : 'text-success'}`}>
                        {CONFIDENCE_LEVELS[getConfidenceLevel(trait.confidence)].label}
                      </span>
                      {isLowConfidence && <span className="trait-row__hint">Clarification suggested</span>}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </section>

        <CompletenessPanel
          score={caseCompletenessScore}
          toneColor={scoreTone}
          stats={[
            {
              label: 'Missing traits',
              value: missingCoreTraits.length ? missingCoreTraits.slice(0, 3).join(', ') + (missingCoreTraits.length > 3 ? '…' : '') : 'None',
              color: missingCoreTraits.length ? 'var(--warning)' : 'var(--success)'
            },
            {
              label: 'Confidence gaps',
              value: lowConfidenceTraits.length
                ? `Low: ${lowConfidenceTraits.slice(0, 2).join(', ')}${lowConfidenceTraits.length > 2 ? '…' : ''}`
                : mediumConfidenceTraits.length
                  ? `Mid: ${mediumConfidenceTraits.slice(0, 2).join(', ')}${mediumConfidenceTraits.length > 2 ? '…' : ''}`
                  : 'Strong',
              color: (lowConfidenceTraits.length || mediumConfidenceTraits.length) ? 'var(--warning)' : 'var(--success)'
            },
            {
              label: 'Contradictions',
              value: contradictions.length ? contradictions[0] : 'None detected',
              color: contradictions.length ? 'var(--warning)' : 'var(--success)'
            }
          ]}
        />
      </div>
    </div>
  );
};

export default CandidateExploration;
