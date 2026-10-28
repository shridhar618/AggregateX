import { useState, useRef, useEffect } from 'react';
import { parseTraits } from '../utils/parser';
import PhaseHeader from './ui/PhaseHeader';
import CompletenessPanel from './ui/CompletenessPanel';
import Icon from './ui/Icon';

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
  skin_tone: 'Skin tone',
  facial_hair: 'Facial hair'
};

const CONTRADICTION_RULES = [
  {
    key: 'eye_color',
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
    key: 'hair_color',
    label: 'Hair color',
    patterns: [
      { label: 'black', regex: /\bblack\s+hair\b/i },
      { label: 'brown', regex: /\bbrown\s+hair\b/i },
      { label: 'blonde', regex: /\bblonde\s+hair\b/i },
      { label: 'red', regex: /\b(?:red|ginger)\s+hair\b/i },
      { label: 'gray', regex: /\b(?:gray|grey|white|silver)\s+hair\b/i }
    ]
  },
  {
    key: 'gender',
    label: 'Gender',
    patterns: [
      { label: 'male', regex: /\b(man|male|boy|guy|he|his|him)\b/i },
      { label: 'female', regex: /\b(woman|female|girl|lady|she|her)\b/i }
    ]
  }
];

const findContradictions = (description = '') => {
  if (!description.trim()) return [];

  return CONTRADICTION_RULES.map(rule => {
    const matched = rule.patterns
      .filter(p => p.regex.test(description))
      .map(p => p.label);

    if (matched.length > 1) {
      return `${rule.label}: ${matched.join(' vs ')}`;
    }
    return null;
  }).filter(Boolean);
};

const WitnessInterview = ({ advancePhase, onDataChange, data, apiKey }) => {
  const messages = data.messages || [];
  const uploadedImage = data.sourceImage || null;
  const setUploadedImage = (img) => onDataChange({ sourceImage: img });

  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef(null);

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        const uploadUserMessage = {
          id: Date.now(),
          text: `📷 Picture added (${file.name}).`,
          sender: 'user'
        };

        const uploadAiMessage = {
          id: Date.now() + 1,
          text: '✅ Picture added and analyzed. I will use it as visual context while building the forensic profile.',
          sender: 'ai'
        };

        onDataChange({
          sourceImage: reader.result,
          messages: [...messages, uploadUserMessage, uploadAiMessage]
        });
      };
      reader.readAsDataURL(file);
    }
  };

  // Auto-scroll to bottom of chat
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;

    // Add user message
    const newMessages = [...messages, { id: Date.now(), text: input, sender: 'user' }];
    onDataChange({ messages: newMessages });
    const currentInput = input;
    setInput('');
    setIsTyping(true);

    // Simulate AI response & extraction
    setTimeout(async () => {
      const result = await parseTraits(currentInput, apiKey, data.structuredTraits || {});
      setIsTyping(false);

      const aiResponse = (!result || result.error)
        ? { id: Date.now() + 1, text: `I'm having trouble connecting: ${result?.error || 'Unknown Error'}`, sender: 'ai' }
        : { id: Date.now() + 1, text: result.extractedAnyNewInfo ? "I've analyzed those details and updated our reconstruction profile." : "I've noted that, though it seems consistent with what we already have.", sender: 'ai' };

      const newTraits = result?.traits || {};

      onDataChange({
        faceDescription: (data.faceDescription || "") + " " + currentInput,
        structuredTraits: { ...(data.structuredTraits || {}), ...newTraits },
        messages: [...newMessages, aiResponse]
      });
    }, 1500);
  };

  const traits = data.structuredTraits || {};
  const needsClarification = Object.values(traits).some(t => t.confidence < 0.6);
  const lowConfidenceTraits = Object.entries(traits)
    .filter(([, t]) => t.confidence < 0.6)
    .map(([key]) => key.replaceAll('_', ' '));
  const mediumConfidenceTraits = Object.entries(traits)
    .filter(([, t]) => t.confidence >= 0.6 && t.confidence < 0.8)
    .map(([key]) => key.replaceAll('_', ' '));

  const missingCoreTraits = CORE_TRAITS.filter(key => !traits[key]).map(key => TRAIT_LABELS[key]);
  const contradictions = findContradictions(data.faceDescription || '');
  const coverageRatio = (CORE_TRAITS.length - missingCoreTraits.length) / CORE_TRAITS.length;
  const confidenceValues = Object.values(traits).map(trait => trait.confidence).filter(Number.isFinite);
  const avgConfidence = confidenceValues.length > 0
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

  const getConfidenceLevel = (confidence) => {
    if (confidence >= 0.9) return 'high';
    if (confidence >= 0.6) return 'mid';
    return 'low';
  };

  const traitCount = Object.keys(traits).length;
  const canAdvance = traitCount > 0 && !needsClarification;

  return (
    <div className="phase phase--interview animate-fade-in">
      <PhaseHeader
        index="01"
        eyebrow={`Witness interview · ${data.name}`}
        title="Witness Interview"
        description="Please describe the subject in natural language."
      />

      <div className="interview-grid">
        {/* Chat Area */}
        <section className="panel chat-panel" aria-labelledby="testimony-title">
          <div className="panel-head">
            <div>
              <h2 id="testimony-title" className="panel-title">Testimony log</h2>
              <p className="panel-sub">Statements are parsed into structured traits as you type.</p>
            </div>
            <span className="chip mono">{messages.length} entries</span>
          </div>

          <div ref={scrollRef} className="chat-log" role="log" aria-live="polite">
            {messages.map((msg, index) => {
              const isAi = msg.sender === 'ai';
              const isInitialAi = isAi && index === 0;

              return (
                <div
                  key={msg.id}
                  className={`chat-msg ${isAi ? 'chat-msg--ai' : 'chat-msg--user'} ${isInitialAi ? 'chat-msg--intro' : ''}`}
                >
                  <span className="chat-msg__author">
                    {isAi ? 'VeriSketch AI' : 'Witness'}
                  </span>
                  <div className="chat-msg__bubble">{msg.text}</div>
                </div>
              );
            })}
            {isTyping && (
              <div className="chat-msg chat-msg--ai">
                <span className="chat-msg__author">VeriSketch AI</span>
                <div className="chat-msg__bubble chat-typing" aria-label="Analyzing statement">
                  <span /><span /><span />
                </div>
              </div>
            )}
          </div>

          {/* Input Area */}
          <div className="composer">
            <input
              type="file"
              id="imageUpload"
              accept="image/*"
              className="sr-only"
              onChange={handleImageUpload}
            />
            <label htmlFor="imageUpload" className="btn btn-icon composer__attach" title="Attach reference image">
              <Icon name="camera" />
              <span className="sr-only">Attach reference image</span>
            </label>
            <input
              className="input-glass composer__input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="e.g. He had a crooked nose, dark hair, and maybe a sharp jawline..."
              onKeyDown={(e) => e.key === 'Enter' && handleSend()}
              aria-label="Witness statement"
            />
            <button className="btn btn-primary" onClick={handleSend}>
              Send
              <Icon name="send" />
            </button>
          </div>

          {/* Image Preview Area */}
          {uploadedImage && (
            <div className="attachment animate-fade-in">
              <img src={uploadedImage} alt="Uploaded evidence" className="attachment__thumb" />
              <div className="attachment__text">
                <strong>Reference image attached</strong>
                <span>Sent to Gemini as visual context when candidates are generated.</span>
              </div>
              <button
                type="button"
                className="btn btn-sm btn-ghost text-danger"
                onClick={() => {
                  setUploadedImage(null);
                  onDataChange({ ...data, sourceImage: null });
                }}
              >
                <Icon name="close" />
                Remove
              </button>
            </div>
          )}
        </section>

        <aside className="interview-side">
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

          {/* Schema Live View & Actions */}
          <section className="panel profile-panel" aria-labelledby="profile-title">
            <div className="panel-head">
              <div>
                <h2 id="profile-title" className="panel-title">Forensic Profile</h2>
                <p className="panel-sub">Real-time trait synchronization active</p>
              </div>
              <span className="chip mono">{traitCount} traits</span>
            </div>

            {traitCount === 0 && (
              <div className="empty-state">
                <Icon name="scan" />
                <span>Not determined yet.</span>
              </div>
            )}

            <ul className="trait-list">
              {Object.entries(data.structuredTraits).map(([key, trait]) => {
                const isLow = trait.confidence < 0.6;
                return (
                  <li key={key} className={`trait-row trait-row--compact ${isLow ? 'is-low' : ''}`}>
                    <span className="trait-row__name">{key.replaceAll('_', ' ')}</span>
                    <span className={`trait-row__level ${isLow ? 'text-warning' : 'text-success'}`}>
                      {CONFIDENCE_LEVELS[getConfidenceLevel(trait.confidence)].label}
                    </span>
                    <span className="trait-row__value" title={trait.value}>{trait.value}</span>
                    <select
                      className="select trait-row__select"
                      aria-label={`Confidence for ${key.replaceAll('_', ' ')}`}
                      value={getConfidenceLevel(trait.confidence)}
                      onChange={(e) => {
                        const newLevel = e.target.value;
                        const mappedConfidence = CONFIDENCE_LEVELS[newLevel].value;
                        onDataChange({
                          ...data,
                          structuredTraits: {
                            ...data.structuredTraits,
                            [key]: { ...trait, confidence: mappedConfidence }
                          }
                        });
                      }}
                    >
                      <option value="low">Not so confident</option>
                      <option value="mid">Middle</option>
                      <option value="high">Very confident</option>
                    </select>
                    {isLow && <span className="trait-row__hint">Clarification suggested</span>}
                  </li>
                );
              })}
            </ul>

            <div className="profile-panel__action">
              {needsClarification && (
                <div className="notice notice--warning">
                  <Icon name="alert" />
                  <span>Required: clarify <strong>{lowConfidenceTraits[0]}</strong> before generating.</span>
                </div>
              )}
              <button
                className={`btn btn-primary btn-block btn-lg ${canAdvance ? 'glow-active' : ''}`}
                onClick={advancePhase}
                disabled={traitCount === 0 || needsClarification}
              >
                <Icon name={needsClarification ? 'lock' : 'sparkle'} />
                {needsClarification ? 'Locked — clarify details' : 'Generate candidates'}
              </button>
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
};

export default WitnessInterview;
