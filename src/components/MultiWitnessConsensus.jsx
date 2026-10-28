import { useState, useEffect, useRef } from 'react';

const MultiWitnessConsensus = ({ witnesses, apiKey, returnPhase }) => {
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
        <title>Printable Case Report</title>
        <style>
          body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            margin: 0;
            padding: 24px;
            color: #0f172a;
            background: #ffffff;
          }
          .wrapper {
            max-width: 820px;
            margin: 0 auto;
          }
          .header {
            text-align: center;
            border-bottom: 2px solid #1e293b;
            padding-bottom: 10px;
            margin-bottom: 18px;
          }
          .title {
            margin: 0;
            font-size: 28px;
            letter-spacing: 0.01em;
          }
          .subtitle {
            margin: 5px 0 0;
            font-size: 14px;
            color: #334155;
          }
          .notice {
            background: #f1f5f9;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            padding: 12px;
            margin: 12px 0 18px;
            font-weight: 700;
            color: #0f172a;
          }
          .image-wrap {
            text-align: center;
            margin: 8px 0 16px;
          }
          .photo {
            width: 300px;
            height: 300px;
            object-fit: cover;
            border: 2px solid #1e293b;
            border-radius: 10px;
            background: #e2e8f0;
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
            border: 1px solid #cbd5e1;
            padding: 9px;
            text-align: left;
            font-size: 14px;
          }
          th {
            background: #f8fafc;
          }
          .meta {
            margin-top: 14px;
            font-size: 13px;
            color: #475569;
          }
          .actions {
            margin-top: 18px;
            display: flex;
            justify-content: flex-end;
            gap: 8px;
          }
          .actions button {
            border: 1px solid #334155;
            background: #ffffff;
            color: #0f172a;
            border-radius: 8px;
            padding: 8px 12px;
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
            <h1 class="title">Person of Interest Report</h1>
            <p class="subtitle">Generated from multi-witness consensus</p>
          </div>

          <div class="notice">If you have seen this person, contact the police immediately and provide any relevant location/time details.</div>

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
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Multi-Witness Consensus</h2>
          <p style={{ color: 'var(--text-secondary)' }}>Fusing independent accounts into a definitive target.</p>
        </div>
        <button className="btn" onClick={returnPhase}>← Back</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '48px', alignItems: 'start' }}>

        {/* Left Side: Witnesses */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <h3 style={{ borderBottom: '1px solid var(--surface-border)', paddingBottom: '8px' }}>Individual Witness Matches</h3>
          {confirmedWitnesses.length === 0 ? (
            <p style={{ color: 'var(--text-secondary)' }}>No witnesses have confirmed a match yet.</p>
          ) : (
            confirmedWitnesses.map(w => {
              const matchedCand = w.candidates.find(c => c.id === w.selectedCandidate);
              return (
                <div key={w.id} className="glass-panel" style={{ display: 'flex', gap: '16px', alignItems: 'center', padding: '12px' }}>
                  <div style={{ width: '80px', height: '80px', borderRadius: '8px', overflow: 'hidden', background: '#000' }}>
                    <img src={matchedCand?.image} alt={w.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  </div>
                  <div>
                    <h4 style={{ margin: 0, fontSize: '1.1rem' }}>{w.name}</h4>
                    <div style={{ color: 'var(--success)', fontSize: '0.85rem', fontWeight: 'bold' }}>Match Confirmed</div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Side: Consensus */}
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '32px', minHeight: '500px', position: 'relative' }}>
          {isMerging ? (
            <div style={{ textAlign: 'center' }}>
              <div className="animate-pulse" style={{ width: '64px', height: '64px', border: '4px solid var(--primary)', borderTopColor: 'transparent', borderRadius: '50%', margin: '0 auto 24px', animation: 'spin 1s linear infinite' }}></div>
              <h3 className="animate-pulse">Reconciling Memory Discrepancies...</h3>
              <p style={{ color: 'var(--text-secondary)' }}>Identifying common facial anchors across {confirmedWitnesses.length} witnesses</p>
            </div>
          ) : (
            <div className="animate-fade-in" style={{ textAlign: 'center', width: '100%' }}>
              <div
                className="glow-active"
                style={{
                  width: '100%',
                  maxWidth: '320px',
                  aspectRatio: '1/1',
                  background: '#000',
                  borderRadius: '24px',
                  overflow: 'hidden',
                  margin: '0 auto 32px',
                  boxShadow: '0 0 50px rgba(59, 130, 246, 0.3)',
                  border: '2px solid rgba(59, 130, 246, 0.6)'
                }}
              >
                <img src={consensusImage || "/placeholder_composite.png"} alt="Consensus Target" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              </div>
              <h2 style={{ marginBottom: '12px', fontSize: '2.2rem', letterSpacing: '-0.02em' }}>Target ID: 24-Alpha</h2>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', marginTop: '32px', textAlign: 'left' }}>
                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '20px', borderRadius: '16px', border: '1px solid var(--surface-border)' }}>
                  <h4 style={{ color: 'var(--success)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '1.2rem' }}>✨</span> Shared Consensus
                  </h4>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                    {agreedTraits.length > 0 ? agreedTraits.map((t, idx) => (
                      <span key={idx} style={{ background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)', padding: '6px 12px', borderRadius: '8px', fontSize: '0.85rem' }}>
                        {t.key}: <b style={{ color: '#fff' }}>{t.value}</b>
                      </span>
                    )) : <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>No perfect shared matches.</span>}
                  </div>
                </div>

                <div style={{ background: 'rgba(0,0,0,0.2)', padding: '20px', borderRadius: '16px', border: '1px solid var(--surface-border)' }}>
                  <h4 style={{ color: 'var(--warning)', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '1.2rem' }}>⚖️</span> Dissimilar Traits
                  </h4>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                    {dissimilarTraits.length > 0 ? dissimilarTraits.map((t, idx) => (
                      <span key={idx} style={{ background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.2)', padding: '6px 12px', borderRadius: '8px', fontSize: '0.85rem' }}>
                        {t.key}: <b style={{ color: '#fff' }}>{t.values.join(' / ')}</b>
                      </span>
                    )) : <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>No major discrepancies.</span>}
                  </div>
                </div>
              </div>

              <button className="btn btn-primary glow-active" style={{ marginTop: '40px', width: '100%', height: '50px', fontSize: '1.1rem' }} onClick={handleGeneratePrintableReport}>
                🖨️ Generate Printable Report
              </button>
            </div>
          )}
        </div>

      </div>

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default MultiWitnessConsensus;
