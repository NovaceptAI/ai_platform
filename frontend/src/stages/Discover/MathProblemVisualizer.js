import React, { useMemo, useRef, useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import './MathProblemVisualizer.css';
import config from '../../config';

function CanvasPlot({ plot, title }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (!plot || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const W = canvas.width;
    const H = canvas.height;
    ctx.clearRect(0, 0, W, H);

    const padding = 40;
    const x = plot.x || [];
    const y = plot.y || [];

    if (!x.length || !y.length || x.length !== y.length) {
      ctx.fillText('No numeric plot data', 10, 20);
      return;
    }

    const minX = Math.min(...x), maxX = Math.max(...x);
    const minY = Math.min(...y), maxY = Math.max(...y);
    const xspan = (maxX - minX) || 1;
    const yspan = (maxY - minY) || 1;

    // axes
    ctx.strokeStyle = '#aaa';
    ctx.lineWidth = 1;
    // x axis
    ctx.beginPath();
    ctx.moveTo(padding, H - padding);
    ctx.lineTo(W - padding, H - padding);
    ctx.stroke();
    // y axis
    ctx.beginPath();
    ctx.moveTo(padding, H - padding);
    ctx.lineTo(padding, padding);
    ctx.stroke();

    // labels
    ctx.fillStyle = '#666';
    ctx.font = '12px system-ui, -apple-system, Segoe UI, Roboto, sans-serif';
    if (plot.x_label) ctx.fillText(plot.x_label, W/2 - 20, H - 12);
    if (plot.y_label) {
      ctx.save();
      ctx.translate(12, H/2);
      ctx.rotate(-Math.PI/2);
      ctx.fillText(plot.y_label, 0, 0);
      ctx.restore();
    }

    // data
    ctx.strokeStyle = '#2e7d32';
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < x.length; i++) {
      const px = padding + ((x[i] - minX) / xspan) * (W - 2*padding);
      const py = H - padding - ((y[i] - minY) / yspan) * (H - 2*padding);
      if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
    }
    ctx.stroke();

    // points
    ctx.fillStyle = '#1b5e20';
    for (let i = 0; i < x.length; i++) {
      const px = padding + ((x[i] - minX) / xspan) * (W - 2*padding);
      const py = H - padding - ((y[i] - minY) / yspan) * (H - 2*padding);
      ctx.beginPath();
      ctx.arc(px, py, 2.5, 0, Math.PI * 2);
      ctx.fill();
    }
  }, [plot]);

  return (
    <div className="mpv-plot">
      {title && <div className="mpv-plot-title">{title}</div>}
      <canvas ref={canvasRef} width={520} height={320} />
      {plot?.series_label && <div className="mpv-plot-legend">{plot.series_label}</div>}
    </div>
  );
}

function Diagram({ diag }) {
  const hasSVG = typeof diag.svg === 'string' && diag.svg.includes('<svg');
  if (hasSVG) {
    // NOTE: If you want strict sanitization, run the string through a sanitizer before injecting.
    return (
      <div className="mpv-diagram">
        <div className="mpv-diagram-title">{diag.title}</div>
        <div className="mpv-svg" dangerouslySetInnerHTML={{ __html: diag.svg }} />
      </div>
    );
  }
  if (diag.plot && (diag.plot.x?.length || diag.plot.y?.length)) {
    return <CanvasPlot title={diag.title} plot={diag.plot} />;
  }
  return null;
}

export default function MathProblemVisualizer() {
  const [method, setMethod] = useState('text');
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);

  const [difficulty, setDifficulty] = useState('intermediate'); // beginner|intermediate|advanced
  const [level, setLevel] = useState('school');                 // school|college|olympiad
  const [showHints, setShowHints] = useState(true);
  const [practiceCount, setPracticeCount] = useState(3);
  const [visualizeTypes, setVisualizeTypes] = useState(['graph','number_line','geometry']);

  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = useMemo(() => {
    if (submitting) return false;
    if (method === 'text') return (text.trim().length >= 5);
    if (method === 'document') return !!file;
    return false;
  }, [method, text, file, submitting]);

  const onFilePicked = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 25 * 1024 * 1024) {
      setError('File too large (max 25MB).');
      return;
    }
    setError(null);
    setFile(f);
  };

  const submit = async () => {
    setSubmitting(true);
    setError(null);
    setResult(null);

    try {
      let resp;
      if (method === 'text') {
        const payload = {
          method: 'text',
          text: text.trim(),
          difficulty,
          level,
          show_hints: showHints,
          practice_count: practiceCount,
          visualize_types: visualizeTypes,
        };
        resp = await fetch(`${config.API_BASE_URL}/math_visualizer/solve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } else {
        const fd = new FormData();
        fd.append('method', 'document');
        fd.append('file', file);
        fd.append('difficulty', difficulty);
        fd.append('level', level);
        fd.append('show_hints', String(showHints));
        fd.append('practice_count', String(practiceCount));
        fd.append('visualize_types', visualizeTypes.join(','));
        resp = await fetch(`${config.API_BASE_URL}/math_visualizer/solve`, {
          method: 'POST',
          body: fd,
        });
      }

      const json = await resp.json();
      if (!resp.ok) throw new Error(json?.error || 'Failed to solve problem.');
      setResult(json);
    } catch (e) {
      setError(e.message || 'Failed to solve problem.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    submit();
  };

  const resetAll = () => {
    setMethod('text');
    setText('');
    setFile(null);
    setDifficulty('intermediate');
    setLevel('school');
    setShowHints(true);
    setPracticeCount(3);
    setVisualizeTypes(['graph','number_line','geometry']);
    setResult(null);
    setError(null);
  };

  const downloadJSON = () => {
    if (!result) return;
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'math_problem_visualization.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mpv-wrap">
      {!result ? (
        <div className="mpv-card">
          <header className="mpv-header">
            <h1 className="mpv-title">🧮 Math Problem Visualizer</h1>
            <p className="mpv-subtitle">Solve step‑by‑step with hints, diagrams, and interactive plots.</p>
          </header>

          <div className="mpv-seg">
            <button
              type="button"
              className={`seg-btn ${method === 'text' ? 'active' : ''}`}
              onClick={() => setMethod('text')}
            >
              Text
            </button>
            <button
              type="button"
              className={`seg-btn ${method === 'document' ? 'active' : ''}`}
              onClick={() => setMethod('document')}
            >
              Document
            </button>
          </div>

          <form className="mpv-form" onSubmit={handleSubmit}>
            {method === 'text' && (
              <div className="mpv-field">
                <label className="mpv-label" htmlFor="problem">Problem</label>
                <textarea
                  id="problem"
                  className="mpv-textarea"
                  rows={6}
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder={`e.g., Solve 2x + 3 = 11.\nOr: Find the vertex and intercepts of y = x^2 - 4x + 1.`}
                />
              </div>
            )}

            {method === 'document' && (
              <div className="mpv-field">
                <label className="mpv-label">Upload Document</label>
                <div className="mpv-upload">
                  <input id="file" type="file" onChange={onFilePicked} hidden />
                  <label htmlFor="file" className="btn-ghost">{file ? 'Change File' : 'Choose File'}</label>
                  <span className="mpv-file-name">{file ? file.name : 'No file selected'}</span>
                </div>
                <div className="hint">Max 25MB. PDFs, DOCX, or TXT work best.</div>
              </div>
            )}

            <div className="mpv-row">
              <div className="mpv-field">
                <label className="mpv-label" htmlFor="level">Level</label>
                <select id="level" className="mpv-input" value={level} onChange={(e) => setLevel(e.target.value)}>
                  <option value="school">School</option>
                  <option value="college">College</option>
                  <option value="olympiad">Olympiad</option>
                </select>
              </div>
              <div className="mpv-field">
                <label className="mpv-label" htmlFor="difficulty">Difficulty</label>
                <select id="difficulty" className="mpv-input" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
                  <option value="beginner">Beginner</option>
                  <option value="intermediate">Intermediate</option>
                  <option value="advanced">Advanced</option>
                </select>
              </div>
              <div className="mpv-field">
                <label className="mpv-label" htmlFor="practice">Practice Qs</label>
                <input
                  id="practice"
                  className="mpv-input"
                  type="number"
                  min={0}
                  max={10}
                  value={practiceCount}
                  onChange={(e) => setPracticeCount(parseInt(e.target.value || '0', 10))}
                />
              </div>
            </div>

            <div className="mpv-row">
              <div className="mpv-field">
                <label className="mpv-label">Visuals</label>
                <div className="mpv-chips">
                  {['graph','number_line','geometry','flowchart'].map(t => (
                    <button
                      type="button"
                      key={t}
                      className={`chip ${visualizeTypes.includes(t) ? 'chip-on' : ''}`}
                      onClick={() => {
                        setVisualizeTypes(v => v.includes(t) ? v.filter(x => x !== t) : [...v, t]);
                      }}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
              <div className="mpv-field mpv-toggle">
                <label className="mpv-label">Hints First</label>
                <input type="checkbox" checked={showHints} onChange={e => setShowHints(e.target.checked)} />
              </div>
            </div>

            {error && <div className="mpv-error">{error}</div>}

            <div className="mpv-actions">
              <button type="submit" className="btn-primary" disabled={!canSubmit}>
                {submitting ? 'Solving…' : 'Solve & Visualize'}
              </button>
              <button type="button" className="btn-secondary" onClick={resetAll} disabled={submitting}>
                Reset
              </button>
            </div>
          </form>
        </div>
      ) : (
        <div className="mpv-results">
          <div className="mpv-results-head">
            <h2>Solution & Visuals</h2>
            <div className="mpv-results-actions">
              <button className="btn-secondary" onClick={downloadJSON}>Download JSON</button>
              <button className="btn-secondary" onClick={resetAll}>New Problem</button>
            </div>
          </div>

          <div className="mpv-problem">
            {result.problem && (
              <>
                <h3>Problem</h3>
                <ReactMarkdown>{result.problem}</ReactMarkdown>
              </>
            )}
            {result.interpretation && (
              <>
                <h4>Interpretation</h4>
                <ReactMarkdown>{result.interpretation}</ReactMarkdown>
              </>
            )}
          </div>

          {Array.isArray(result.formulas) && result.formulas.length > 0 && (
            <div className="mpv-formulas">
              <h3>Key Formulas</h3>
              <ul>
                {result.formulas.map((f, i) => <li key={i}><code>{f}</code></li>)}
              </ul>
            </div>
          )}

          {Array.isArray(result.steps) && result.steps.length > 0 && (
            <div className="mpv-steps">
              <h3>Step-by-Step</h3>
              {result.steps.map((st, i) => (
                <details key={st.id || i} open={!showHints}>
                  <summary>
                    <span className="mpv-step-id">#{st.id || (i+1)}</span>
                    <span className="mpv-step-title">{st.title || `Step ${i+1}`}</span>
                  </summary>
                  {showHints && st.hint && (
                    <div className="mpv-step-hint">
                      <strong>Hint:</strong> {st.hint}
                    </div>
                  )}
                  {st.detail && (
                    <div className="mpv-step-detail">
                      <ReactMarkdown>{st.detail}</ReactMarkdown>
                    </div>
                  )}
                  {st.formula && (
                    <div className="mpv-step-formula">
                      <code>{st.formula}</code>
                    </div>
                  )}
                </details>
              ))}
            </div>
          )}

          {Array.isArray(result.diagrams) && result.diagrams.length > 0 && (
            <div className="mpv-diagrams">
              <h3>Diagrams & Plots</h3>
              {result.diagrams.map((d, idx) => (
                <Diagram key={idx} diag={d} />
              ))}
            </div>
          )}

          {result.final_answer && (
            <div className="mpv-final">
              <h3>Final Answer</h3>
              <div className="mpv-answer"><ReactMarkdown>{result.final_answer}</ReactMarkdown></div>
            </div>
          )}

          {Array.isArray(result.checks) && result.checks.length > 0 && (
            <div className="mpv-checks">
              <h3>Quick Checks</h3>
              <ul>{result.checks.map((c, i) => <li key={i}>{c}</li>)}</ul>
            </div>
          )}

          {Array.isArray(result.alternates) && result.alternates.length > 0 && (
            <div className="mpv-alternates">
              <h3>Alternate Methods</h3>
              <ul>{result.alternates.map((a, i) => <li key={i}>{a}</li>)}</ul>
            </div>
          )}

          {Array.isArray(result.practice) && result.practice.length > 0 && (
            <div className="mpv-practice">
              <h3>Practice</h3>
              <ol>
                {result.practice.map((p, i) => (
                  <li key={i}>
                    <div className="mpv-q">{p.question}</div>
                    <details>
                      <summary>Show answer</summary>
                      <div className="mpv-a">{p.answer}</div>
                      <div className="mpv-diff">Difficulty: {p.difficulty || 'NA'}</div>
                    </details>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {result.latex?.problem && (
            <div className="mpv-latex">
              <h4>LaTeX (Problem)</h4>
              <pre>{result.latex.problem}</pre>
            </div>
          )}
          {result.latex?.answer && (
            <div className="mpv-latex">
              <h4>LaTeX (Answer)</h4>
              <pre>{result.latex.answer}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}