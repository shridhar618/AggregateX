import { useState, useEffect, useRef } from 'react';
import { isPlaceholderImage } from '../utils/imageSource';
import PhaseHeader from './ui/PhaseHeader';
import LiquidReveal from './ui/LiquidReveal';
import Icon from './ui/Icon';
import SafeImage from './ui/SafeImage';

const MultiWitnessConsensus = ({ witnesses, apiKey, returnPhase, onOpenSettings }) => {
  const [isMerging, setIsMerging] = useState(true);
  const [consensusImage, setConsensusImage] = useState(null);
  const [agreedTraits, setAgreedTraits] = useState([]);
  const [dissimilarTraits, setDissimilarTraits] = useState([]);
  const latestFusionRequestId = useRef(0);

  const confirmedWitnesses = witnesses.filter(w => w.selectedCandidate);
  const confirmedSignature = confirmedWitnesses
    .map(w => `${w.id}:${w.selectedCandidate || 'none'}`)
    .sort()
    .join('|');

  // Presentation-only: did any witness confirm a stock placeholder instead of a generated sketch?
  const usesPlaceholderInputs = confirmedWitnesses.some(w =>
    isPlaceholderImage(w.candidates.find(c => c.id === w.selectedCandidate)?.image)
  );

  const traitSummary = confirmedWitnesses.reduce((acc, witness) => {
    Object.entries(witness.structuredTraits || {}).forEach(([key, trait]) => {
      if (!acc[key]) {
        acc[key] = { valueCounts: {}, confidences: [] };
      }
      const normalizedValue = (trait.value || '').toString().trim().toLowerCase();
      if (normalizedValue) {
        acc[key].valueCounts[normalizedValue] = (acc[key].valueCounts[normalizedValue] || 0) + 1;
      }
      if (Number.isFinite(trait.confidence)) {
        acc[key].confidences.push(trait.confidence);
      }
    });
    return acc;
  }, {});

  const reportTraits = Object.entries(traitSummary)
    .map(([key, summary]) => {
      const mostLikelyValue = Object.entries(summary.valueCounts)
        .sort((a, b) => b[1] - a[1])[0]?.[0] || 'not determined';
      const avgConfidence = summary.confidences.length
        ? Math.round((summary.confidences.reduce((sum, value) => sum + value, 0) / summary.confidences.length) * 100)
        : 0;

      return {
        trait: key.replaceAll('_', ' '),
        value: mostLikelyValue,
        confidence: avgConfidence
      };
    })
    .sort((a, b) => b.confidence - a.confidence);

  const escapeHtml = (text = '') => text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');

  const handleGeneratePrintableReport = () => {
    const reportWindow = window.open('', '_blank', 'width=900,height=1100');
    if (!reportWindow) {
      window.alert('Unable to open print preview. Please allow pop-ups for this site.');
      return;
    }

    const now = new Date();
    const reportDate = now.toLocaleString();
    const traitsHtml = reportTraits.length
      ? reportTraits.map(row => `
        <tr>
          <td>${escapeHtml(row.trait)}</td>
          <td>${escapeHtml(row.value)}</td>
          <td>${row.confidence}%</td>
        </tr>
      `).join('')
      : '<tr><td colspan="3">No traits available.</td></tr>';

    const reportHtml = `
      <!doctype html>
      <html>
      <head>
        <meta charset="utf-8" />
        <title>VeriSketch AI — Case Report</title>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link href="https://fonts.googleapis.com/css2?family=Onest:wght@400;500;600;700&display=swap" rel="stylesheet" />
        <style>
          body {
            font-family: 'Onest', -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            margin: 0;
            padding: 32px 24px;
            color: #0a0a0a;
            background: #ffffff;
          }
          .wrapper {
            max-width: 820px;
            margin: 0 auto;
          }
          .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            gap: 16px;
            border-bottom: 2px solid #0a0a0a;
            padding-bottom: 14px;
            margin-bottom: 18px;
          }
          .brand {
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: #b15f2c;
            margin-bottom: 6px;
          }
          .case-meta {
            text-align: right;
            font-size: 12px;
            color: #5f5c57;
            line-height: 1.5;
          }
          .disclaimer {
            font-size: 12.5px;
            color: #5f5c57;
            border-left: 3px solid #b15f2c;
            padding: 6px 12px;
            margin: 0 0 14px;
          }
          .placeholder-warning {
            background: #fff7dd;
            border: 1px solid #f1d27a;
            color: #5c4500;
            border-radius: 8px;
            padding: 10px 12px;
            margin: 0 0 14px;
            font-size: 13px;
            font-weight: 600;
          }
          .title {
            margin: 0;
            font-size: 30px;
            font-weight: 600;
            letter-spacing: -0.025em;
          }
          .subtitle {
            margin: 5px 0 0;
            font-size: 14px;
            color: #5f5c57;
          }
          .notice {
            background: #0a0a0a;
            color: #ffffff !important;
            border-radius: 12px;
            padding: 12px;
            margin: 12px 0 18px;
            font-weight: 600;
          }
          .image-wrap {
            text-align: center;
            margin: 8px 0 16px;
          }
          .photo {
            width: 300px;
            height: 300px;
            object-fit: cover;
            border: 1px solid #0a0a0a;
            border-radius: 16px;
            background: #f1f0ee;
          }
          .section-title {
            font-size: 18px;
            margin: 0 0 8px;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 4px;
          }
          th, td {
            border-bottom: 1px solid #e7e5e1;
            padding: 9px;
            text-align: left;
            font-size: 14px;
          }
          th {
            background: #f1f0ee;
            font-size: 11px;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: #5f5c57;
          }
          td:first-child {
            text-transform: capitalize;
          }
          .meta {
            margin-top: 14px;
            font-size: 13px;
            color: #5f5c57;
          }
          .actions {
            margin-top: 18px;
            display: flex;
            justify-content: flex-end;
            gap: 8px;
          }
          .actions button {
            border: 1px solid #0a0a0a;
            background: #ffffff;
            color: #0a0a0a;
            border-radius: 999px;
            padding: 9px 18px;
            font: inherit;
            cursor: pointer;
          }
          @media print {
            body {
              padding: 14px;
            }
            .actions {
              display: none;
            }
          }
        </style>
      </head>
      <body>
        <div class="wrapper">
          <div class="header">
            <div>
              <div class="brand">VeriSketch AI</div>
              <h1 class="title">Person of Interest Report</h1>
              <p class="subtitle">Generated from multi-witness consensus</p>
            </div>
            <div class="case-meta">Target ID: 24-Alpha<br />${escapeHtml(reportDate)}</div>
          </div>

          <div class="notice">If you have seen this person, contact the police immediately and provide any relevant location/time details.</div>

          <p class="disclaimer">This image is an AI-generated composite built from witness descriptions. It is an investigative lead, not a photograph of a real person and not evidence of identity.</p>
          ${usesPlaceholderInputs ? '<div class="placeholder-warning">Warning: at least one witness confirmed a stock placeholder photo instead of an AI-generated sketch. The composite is partly based on that stock photo.</div>' : ''}

          <div class="image-wrap">
            ${consensusImage ? `<img class="photo" src="${consensusImage}" alt="Person of interest" />` : '<div class="photo" style="display:inline-flex;align-items:center;justify-content:center;">No image available</div>'}
          </div>

          <h2 class="section-title">Traits & Confidence</h2>
          <table>
            <thead>
              <tr>
                <th>Trait</th>
                <th>Most Likely Value</th>
                <th>Confidence</th>
              </tr>
            </thead>
            <tbody>
              ${traitsHtml}
            </tbody>
          </table>

          <div class="meta">
            <div><b>Report time:</b> ${escapeHtml(reportDate)}</div>
            <div><b>Witnesses included:</b> ${confirmedWitnesses.length}</div>
          </div>

          <div class="actions">
            <button id="printBtn">Print Report</button>
            <button id="closeBtn">Close</button>
          </div>
        </div>
        <script>
          document.getElementById('printBtn').addEventListener('click', function () { window.print(); });
          document.getElementById('closeBtn').addEventListener('click', function () { window.close(); });
        </script>
      </body>
      </html>
    `;

    reportWindow.document.open();
    reportWindow.document.write(reportHtml);
    reportWindow.document.close();

    reportWindow.focus();
  };

  useEffect(() => {
    let isCancelled = false;
    const requestId = ++latestFusionRequestId.current;

    const doFusion = async () => {
      setIsMerging(true);
      setConsensusImage(null);

      const toDataUrlFromImageSrc = async (imageSrc) => {
        if (!imageSrc) return null;

        if (imageSrc.startsWith('data:')) {
          return imageSrc;
        }

        try {
          const res = await fetch(imageSrc);
          if (!res.ok) return null;
          const blob = await res.blob();
          const base64Data = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => {
              const result = reader.result;
              if (typeof result === 'string') {
                resolve(result.split(',')[1]);
              } else {
                reject(new Error('Invalid image conversion result'));
              }
            };
            reader.onerror = () => reject(new Error('Image conversion failed'));
            reader.readAsDataURL(blob);
          });
          return `data:${blob.type || 'image/jpeg'};base64,${base64Data}`;
        } catch {
          return null;
        }
      };

      const traitsSummary = {};
      confirmedWitnesses.forEach(w => {
        Object.entries(w.structuredTraits).forEach(([key, trait]) => {
          if (!traitsSummary[key]) traitsSummary[key] = { values: new Set(), list: [] };
          traitsSummary[key].values.add(trait.value.toLowerCase().trim());
          traitsSummary[key].list.push(trait.value);
        });
      });

      const agreed = [];
      const dissimilar = [];
      Object.entries(traitsSummary).forEach(([key, summary]) => {
        const readableKey = key.replaceAll('_', ' ');
        if (summary.values.size === 1) {
          agreed.push({ key: readableKey, value: summary.list[0] });
        } else {
          dissimilar.push({ key: readableKey, values: Array.from(summary.values) });
        }
      });

      if (!isCancelled && requestId === latestFusionRequestId.current) {
        setAgreedTraits(agreed);
        setDissimilarTraits(dissimilar);
      }

      const selectedImages = confirmedWitnesses
        .map(w => w.candidates.find(c => c.id === w.selectedCandidate)?.image)
        .filter(Boolean);
      const normalizedImages = (await Promise.all(selectedImages.map(toDataUrlFromImageSrc))).filter(Boolean);
      const imageParts = normalizedImages.map((imageSrc) => {
        const [header, base64Data] = imageSrc.split(',');
        const mimeType = header.split(':')[1].split(';')[0];
        return {
          inlineData: { mimeType, data: base64Data }
        };
      });

      try {
        if (!apiKey) {
          throw new Error('Missing API key for consensus generation');
        }

        if (!imageParts.length) {
          throw new Error('No valid witness image data available for consensus generation');
        }

        const agreedPrompt = agreed.map(t => `${t.key}: ${t.value}`).join(', ');
        const dissimilarPrompt = dissimilar.map(t => `${t.key}: ${t.values.join(' / ')}`).join(', ');

        const fusionInstruction = [
          'Create ONE final face that is a mixed consensus of ALL provided witness-selected faces.',
          'Use the provided images as the primary identity source and blend their shared geometry.',
          agreed.length ? `Keep these shared traits: ${agreedPrompt}.` : '',
          dissimilar.length ? `Reconcile these differing traits naturally: ${dissimilarPrompt}.` : '',
          'Passport-style centered portrait, head and shoulders, neutral background.',
          'No text, no watermark, no logos, no borders.'
        ].filter(Boolean).join(' ');

        const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent?key=${apiKey}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            contents: [{
              parts: [
                { text: `${fusionInstruction} Variant: ${Math.random().toString(36).substring(7)}` },
                ...imageParts
              ]
            }],
            generationConfig: { responseModalities: ["IMAGE"] }
          })
        });

        const resData = await res.json();
        const inline = resData.candidates?.[0]?.content?.parts?.[0]?.inlineData;

        if (!isCancelled && requestId === latestFusionRequestId.current && inline?.data) {
          setConsensusImage(`data:${inline.mimeType};base64,${inline.data}`);
        }
      } catch (err) {
        console.error("Fusion failed:", err);
      } finally {
        if (!isCancelled && requestId === latestFusionRequestId.current) {
          setIsMerging(false);
        }
      }
    };

    if (confirmedWitnesses.length > 0) {
      doFusion();
    } else {
      setConsensusImage(null);
      setAgreedTraits([]);
      setDissimilarTraits([]);
      setIsMerging(false);
    }

    return () => {
      isCancelled = true;
    };
  }, [apiKey, confirmedSignature]);

  return (
    <div className="phase phase--consensus animate-fade-in">
      <PhaseHeader
        index="03"
        eyebrow="Multi-witness consensus"
        title="Multi-Witness Consensus"
        description="Fusing independent accounts into a definitive target."
        meta={<span className="chip mono">{confirmedWitnesses.length} of {witnesses.length} witnesses confirmed</span>}
        actions={
          <button className="btn" onClick={returnPhase}>
            <Icon name="arrowLeft" />
            Back
          </button>
        }
      />

      {usesPlaceholderInputs && (
        <div className="notice notice--placeholder" role="status">
          <Icon name="alert" />
          <div>
            <strong>Composite inputs include placeholder photos.</strong> At least one witness confirmed a stock placeholder
            instead of an AI-generated sketch. Any composite below is partly based on that stock photo, not on witness testimony.
          </div>
        </div>
      )}

      <div className="consensus-grid">

        {/* Left Side: Witnesses */}
        <section className="consensus-witnesses" aria-labelledby="matches-title">
          <h2 id="matches-title" className="section-label">Individual Witness Matches</h2>
          {confirmedWitnesses.length === 0 ? (
            <div className="empty-state">
              <Icon name="user" />
              <span>No witnesses have confirmed a match yet.</span>
            </div>
          ) : (
            <ul className="witness-matches">
              {confirmedWitnesses.map((w, i) => {
                const matchedCand = w.candidates.find(c => c.id === w.selectedCandidate);
                const isPlaceholder = isPlaceholderImage(matchedCand?.image);
                return (
                  <li key={w.id} className="witness-match">
                    <span className="witness-match__index mono">{String(i + 1).padStart(2, '0')}</span>
                    <div className={`witness-match__thumb ${isPlaceholder ? 'is-placeholder' : ''}`}>
                      <SafeImage src={matchedCand?.image} alt={`${w.name} selected ${isPlaceholder ? 'placeholder photo' : 'candidate'}`} fallbackLabel="Unavailable" />
                    </div>
                    <div className="witness-match__text">
                      <h3>{w.name}</h3>
                      <span className="text-success witness-match__status"><Icon name="check" /> Match Confirmed</span>
                      <span className="witness-match__label">{matchedCand?.label}</span>
                    </div>
                    {isPlaceholder ? (
                      <span className="badge badge--placeholder">Placeholder</span>
                    ) : (
                      <span className="chip">AI-generated</span>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        {/* Right Side: Consensus */}
        <section className="consensus-stage surface-ink" aria-live="polite" aria-busy={isMerging}>
          {isMerging ? (
            <div className="consensus-stage__loading">
              <div className="scan-frame" aria-hidden="true">
                <span className="scan-frame__line" />
                <Icon name="user" className="icon scan-frame__icon" strokeWidth={1} />
              </div>
              <h3 className="animate-pulse">Reconciling Memory Discrepancies...</h3>
              <p>Identifying common facial anchors across {confirmedWitnesses.length} witnesses</p>
            </div>
          ) : (
            <div className="consensus-stage__result animate-fade-in">
              {consensusImage ? (
                <figure className="composite">
                  <LiquidReveal
                    baseSrc={consensusImage}
                    baseAlt="AI-generated consensus composite"
                    baseBadge={<span className="badge badge--ai"><Icon name="sparkle" /> AI-generated composite</span>}
                    compareSources={confirmedWitnesses
                      .map(w => {
                        const c = w.candidates.find(cand => cand.id === w.selectedCandidate);
                        return c?.image ? { id: w.id, label: w.name, src: c.image, isPlaceholder: isPlaceholderImage(c.image) } : null;
                      })
                      .filter(Boolean)}
                  />
                </figure>
              ) : (
                <div className="composite composite--missing">
                  <Icon name="image" className="icon composite__missing-icon" />
                  <strong>No composite generated</strong>
                  <span>
                    {!apiKey
                      ? 'A Gemini API key is required to fuse witness matches.'
                      : confirmedWitnesses.length === 0
                        ? 'Confirm at least one witness match first.'
                        : 'Gemini did not return a composite image. Nothing is shown in its place.'}
                  </span>
                  {!apiKey && onOpenSettings && (
                    <button type="button" className="btn btn-sm btn-primary" onClick={onOpenSettings}>
                      Open menu <Icon name="arrowRight" />
                    </button>
                  )}
                </div>
              )}

              <div className="composite__title">
                <span className="eyebrow">Composite subject</span>
                <h2>Target ID: 24-Alpha</h2>
              </div>

              <div className="trait-groups">
                <div className="trait-group">
                  <h4 className="trait-group__title text-success">
                    <Icon name="check" /> Shared Consensus
                  </h4>
                  <ul className="trait-group__list">
                    {agreedTraits.length > 0 ? agreedTraits.map((t, idx) => (
                      <li key={idx} className="consensus-row">
                        <span className="consensus-row__key">{t.key}</span>
                        <b className="consensus-row__value">{t.value}</b>
                      </li>
                    )) : <li className="consensus-row consensus-row--empty">No perfect shared matches.</li>}
                  </ul>
                </div>

                <div className="trait-group">
                  <h4 className="trait-group__title text-warning">
                    <Icon name="layers" /> Dissimilar Traits
                  </h4>
                  <ul className="trait-group__list">
                    {dissimilarTraits.length > 0 ? dissimilarTraits.map((t, idx) => (
                      <li key={idx} className="consensus-row">
                        <span className="consensus-row__key">{t.key}</span>
                        <b className="consensus-row__value">{t.values.join(' / ')}</b>
                      </li>
                    )) : <li className="consensus-row consensus-row--empty">No major discrepancies.</li>}
                  </ul>
                </div>
              </div>

              <button className="btn btn-primary btn-block btn-lg" onClick={handleGeneratePrintableReport}>
                <Icon name="printer" />
                Generate Printable Report
              </button>
            </div>
          )}
        </section>

      </div>
    </div>
  );
};

export default MultiWitnessConsensus;
