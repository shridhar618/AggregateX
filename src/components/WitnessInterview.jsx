import { useState, useRef, useEffect } from 'react';
import { parseTraits } from '../utils/parser';

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

  return (
    <div className="glass-panel animate-fade-in" style={{ width: '100%', maxWidth: '920px', margin: '0 auto', padding: '24px 28px', display: 'flex', flexDirection: 'column', minHeight: '82vh' }}>
      <div style={{ borderBottom: '1px solid var(--surface-border)', paddingBottom: '20px', marginBottom: '18px', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '8px' }}>
        <span style={{ fontSize: '0.72rem', letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--text-secondary)', background: 'rgba(59, 130, 246, 0.12)', border: '1px solid rgba(59, 130, 246, 0.3)', borderRadius: '999px', padding: '4px 12px', fontWeight: '700' }}>
          Phase 1
        </span>
        <h2 style={{ margin: 0, fontSize: '2rem', letterSpacing: '-0.02em' }}>Witness Interview</h2>
        <p style={{ color: 'var(--text-secondary)', marginTop: '2px', maxWidth: '640px', fontSize: '0.98rem' }}>
          Please describe the subject in natural language.
        </p>
      </div>

      <div className="glass-panel" style={{ padding: '18px', borderRadius: '16px', marginBottom: '18px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '8px' }}>
          <h3 style={{ margin: 0, fontSize: '1.05rem' }}>Case Completeness</h3>
          <span style={{ color: scoreTone, fontWeight: '800', fontSize: '1rem' }}>{caseCompletenessScore}%</span>
        </div>
        <div style={{ height: '10px', borderRadius: '999px', background: 'rgba(255,255,255,0.08)', overflow: 'hidden', marginBottom: '12px' }}>
          <div style={{ width: `${caseCompletenessScore}%`, height: '100%', background: `linear-gradient(90deg, ${scoreTone}, rgba(255,255,255,0.85))`, transition: 'width 0.35s ease' }} />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '10px' }}>
          <div style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--surface-border)', borderRadius: '10px', padding: '10px' }}>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-secondary)', marginBottom: '6px' }}>Missing Traits</div>
            <div style={{ fontSize: '0.86rem', color: missingCoreTraits.length ? 'var(--warning)' : 'var(--success)' }}>
              {missingCoreTraits.length ? missingCoreTraits.slice(0, 3).join(', ') + (missingCoreTraits.length > 3 ? '…' : '') : 'None'}
            </div>
          </div>

          <div style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--surface-border)', borderRadius: '10px', padding: '10px' }}>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-secondary)', marginBottom: '6px' }}>Confidence Gaps</div>
            <div style={{ fontSize: '0.86rem', color: (lowConfidenceTraits.length || mediumConfidenceTraits.length) ? 'var(--warning)' : 'var(--success)' }}>
              {lowConfidenceTraits.length
                ? `Low: ${lowConfidenceTraits.slice(0, 2).join(', ')}${lowConfidenceTraits.length > 2 ? '…' : ''}`
                : mediumConfidenceTraits.length
                  ? `Mid: ${mediumConfidenceTraits.slice(0, 2).join(', ')}${mediumConfidenceTraits.length > 2 ? '…' : ''}`
                  : 'Strong'}
            </div>
          </div>

          <div style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--surface-border)', borderRadius: '10px', padding: '10px' }}>
            <div style={{ fontSize: '0.72rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-secondary)', marginBottom: '6px' }}>Potential Contradictions</div>
            <div style={{ fontSize: '0.86rem', color: contradictions.length ? 'var(--warning)' : 'var(--success)' }}>
              {contradictions.length ? contradictions[0] : 'None detected'}
            </div>
          </div>
        </div>
      </div>

      {/* Chat Area */}
      <div ref={scrollRef} style={{ flex: '0 1 auto', minHeight: '280px', maxHeight: '42vh', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px', paddingRight: '12px', marginBottom: '8px' }}>
        {messages.map((msg, index) => {
          const isAi = msg.sender === 'ai';
          const isInitialAi = isAi && index === 0;

          return (
          <div
            key={msg.id}
            style={{
              alignSelf: msg.sender === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '85%',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
              alignItems: msg.sender === 'user' ? 'flex-end' : 'flex-start'
            }}
          >
            <span style={{
              fontSize: '0.7rem',
              fontWeight: 'bold',
              color: isAi ? '#93c5fd' : 'var(--text-secondary)',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              marginLeft: isAi ? '12px' : '0',
              marginRight: isAi ? '0' : '12px',
              background: isAi ? 'rgba(59, 130, 246, 0.18)' : 'transparent',
              border: isAi ? '1px solid rgba(96, 165, 250, 0.35)' : 'none',
              borderRadius: '999px',
              padding: isAi ? '4px 10px' : '0'
            }}>
              {msg.sender === 'ai' ? '🤖 Forensic Artist' : '👤 Witness'}
            </span>
            <div style={{
              padding: '14px 20px',
              borderRadius: msg.sender === 'ai' ? '4px 20px 20px 20px' : '20px 4px 20px 20px',
              background: msg.sender === 'ai'
                ? (isInitialAi
                  ? 'linear-gradient(135deg, rgba(59, 130, 246, 0.32) 0%, rgba(37, 99, 235, 0.18) 50%, rgba(30, 64, 175, 0.12) 100%)'
                  : 'linear-gradient(135deg, rgba(59, 130, 246, 0.18) 0%, rgba(37, 99, 235, 0.08) 100%)')
                : 'rgba(255, 255, 255, 0.05)',
              border: `1px solid ${msg.sender === 'ai' ? (isInitialAi ? 'rgba(96, 165, 250, 0.55)' : 'rgba(59, 130, 246, 0.35)') : 'var(--surface-border)'}`,
              backdropFilter: 'blur(10px)',
              boxShadow: msg.sender === 'ai'
                ? (isInitialAi ? '0 8px 20px rgba(59, 130, 246, 0.25)' : '0 4px 15px rgba(0, 0, 0, 0.1)')
                : '0 4px 15px rgba(0, 0, 0, 0.1)',
              color: '#fff',
              lineHeight: '1.5',
              fontSize: '0.95rem'
            }}>
              {msg.text}
            </div>
          </div>
        )})}
        {isTyping && (
          <div className="animate-pulse" style={{ alignSelf: 'flex-start', background: 'rgba(255, 255, 255, 0.03)', padding: '12px 20px', borderRadius: '4px 16px 16px 16px', border: '1px solid var(--surface-border)', display: 'flex', gap: '4px', marginLeft: '12px' }}>
            <span style={{ display: 'inline-block', width: '6px', height: '6px', background: 'var(--accent-blue)', borderRadius: '50%' }}></span>
            <span style={{ display: 'inline-block', width: '6px', height: '6px', background: 'var(--accent-blue)', borderRadius: '50%' }}></span>
            <span style={{ display: 'inline-block', width: '6px', height: '6px', background: 'var(--accent-blue)', borderRadius: '50%' }}></span>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="glass-panel" style={{ marginTop: '24px', padding: '18px', borderRadius: '16px' }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <input
            type="file"
            id="imageUpload"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={handleImageUpload}
          />
          <label htmlFor="imageUpload" className="btn" style={{ cursor: 'pointer', padding: '8px 12px', background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            📷
          </label>
          <input
            className="input-glass"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="e.g. He had a crooked nose, dark hair, and maybe a sharp jawline..."
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            style={{ flex: 1 }}
          />
          <button className="btn btn-primary" onClick={handleSend}>Send</button>
        </div>

        {/* Image Preview Area */}
        {uploadedImage && (
          <div className="animate-fade-in" style={{ marginTop: '12px', display: 'flex', alignItems: 'center', gap: '12px', background: 'rgba(0,0,0,0.2)', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--surface-border)' }}>
             <img src={uploadedImage} alt="Uploaded evidence" style={{ height: '40px', width: '40px', objectFit: 'cover', borderRadius: '4px' }} />
             <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', flex: 1 }}>Reference Image Attached</span>
             <button onClick={() => {
               setUploadedImage(null);
               onDataChange({ ...data, sourceImage: null });
             }} style={{ background: 'none', border: 'none', color: 'var(--warning)', cursor: 'pointer', fontSize: '0.85rem' }}>✕ Remove</button>
          </div>
        )}
      </div>

      {/* Schema Live View & Actions */}
      <div className="animate-fade-in" style={{
        marginTop: '28px',
        background: 'rgba(0,0,0,0.4)',
        padding: '32px',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--surface-border)',
        minHeight: '640px',
        overflowY: 'visible',
        boxShadow: 'inset 0 0 20px rgba(0,0,0,0.2)'
      }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h4 style={{ color: 'var(--accent-blue)', margin: 0, fontSize: '1.1rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Forensic Profile</h4>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', margin: '4px 0 0' }}>Real-time trait synchronization active</p>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
              <button
                className={`btn btn-primary ${(!needsClarification && Object.keys(traits).length > 0) ? 'glow-active' : ''}`}
                onClick={advancePhase}
                disabled={Object.keys(traits).length === 0 || needsClarification}
                style={{
                  opacity: (Object.keys(traits).length > 0 && !needsClarification) ? 1 : 0.4,
                  minWidth: '220px',
                  height: '44px',
                  fontSize: '0.9rem',
                  letterSpacing: '0.05em'
                }}
              >
                {needsClarification ? '🔒 Locked (Clarify Details)' : '✨ Generate Candidates'}
              </button>
              {needsClarification && (
                <div style={{
                  background: 'rgba(245, 158, 11, 0.1)',
                  border: '1px solid rgba(245, 158, 11, 0.3)',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  color: 'var(--warning)',
                  animation: 'fadeIn 0.3s ease'
                }}>
                  Required: <b>{lowConfidenceTraits[0]}</b>
                </div>
              )}
            </div>
          </div>
            {Object.keys(data.structuredTraits).length === 0 && (
              <div style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid var(--surface-border)',
                borderRadius: '12px',
                padding: '16px',
                color: 'var(--text-secondary)',
                fontSize: '0.95rem'
              }}>
                Not determined yet.
              </div>
            )}
            {Object.entries(data.structuredTraits).map(([key, trait]) => {
              const isLow = trait.confidence < 0.6;
              return (
                <div key={key} style={{
                  display: 'grid',
                  gridTemplateColumns: 'minmax(100px, 150px) minmax(100px, 1fr) minmax(170px, 220px) minmax(120px, 160px)',
                  alignItems: 'center',
                  gap: '12px',
                  background: 'rgba(255,255,255,0.05)',
                  padding: '10px 16px',
                  borderRadius: '10px',
                  position: 'relative',
                  borderLeft: isLow ? '3px solid var(--warning)' : '3px solid transparent',
                  minWidth: 0
                }}>
                  <div style={{ fontWeight: 500, textTransform: 'capitalize', fontSize: '0.9rem' }}>
                    {key.replaceAll('_', ' ')}
                  </div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {trait.value}
                  </div>
                  <select
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
                    style={{
                      cursor: 'pointer',
                      width: '100%',
                      background: 'rgba(0,0,0,0.25)',
                      color: 'var(--text-primary)',
                      border: '1px solid var(--surface-border)',
                      borderRadius: '8px',
                      padding: '8px 10px'
                    }}
                  >
                    <option value="low">Not so confident</option>
                    <option value="mid">Middle</option>
                    <option value="high">Very confident</option>
                  </select>
                  <div style={{ textAlign: 'right', fontWeight: 'bold', color: isLow ? 'var(--warning)' : 'var(--success)', fontSize: '0.9rem' }}>
                    {CONFIDENCE_LEVELS[getConfidenceLevel(trait.confidence)].label}
                  </div>
                  {isLow && (
                    <div style={{
                      position: 'absolute',
                      bottom: '-4px',
                      left: '136px',
                      fontSize: '0.65rem',
                      color: 'var(--warning)',
                      background: 'var(--surface)',
                      padding: '0 4px',
                      borderRadius: '4px'
                    }}>
                      Clarification suggested
                    </div>
                  )}
                </div>
              );
            })}
      </div>
    </div>
  );
};

export default WitnessInterview;
