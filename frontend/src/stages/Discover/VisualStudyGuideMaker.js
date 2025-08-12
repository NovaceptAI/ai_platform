// src/stages/discover/VisualStudyGuideMaker.jsx
import React, { useState, useMemo, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import './VisualStudyGuideMaker.css';
import config from '../../config';
import axiosInstance from '../../utils/axiosInstance';

export default function VisualStudyGuideMaker() {
  // input method
  const [method, setMethod] = useState('category'); // 'category' | 'text' | 'document'
  const [category, setCategory] = useState('');
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);
  const [vaultFiles, setVaultFiles] = useState([]);
  const [selectedVaultFile, setSelectedVaultFile] = useState('');
  
  // ui state
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // results
  const [studyGuide, setStudyGuide] = useState(null);
  const [compact, setCompact] = useState(false);

  // filters/sorts
  const [filter, setFilter] = useState('');
  const [sortBy, setSortBy] = useState('order'); // 'order' | 'time' | 'alpha'

  const fileInputRef = useRef(null);

  const canSubmit = useMemo(() => {
    if (submitting) return false;
    if (method === 'category') return category.trim().length >= 2;
    if (method === 'text') return text.trim().length >= 10;
    if (method === 'document') return !!file || !!selectedVaultFile;
    return false;
  }, [method, category, text, file, selectedVaultFile, submitting]);

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!canSubmit) return;

    setSubmitting(true);
    setError(null);
    setStudyGuide(null);

    try {
      let response;
      const m = (method || '').trim().toLowerCase();

      if (m === 'category' || m === 'text') {
        const payload = m === 'category'
          ? { method: 'category', category: category.trim() }
          : { method: 'text', text: text.trim() };

        // IMPORTANT: ensure this path matches your Flask route
        response = await fetch(`${config.API_BASE_URL}/study_guide/generate_visual_study_guide`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } else if (m === 'document') {
        if (selectedVaultFile) {
          response = await fetch(`${config.API_BASE_URL}/study_guide/generate_visual_study_guide`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ method: 'document', fromVault: true, filename: selectedVaultFile }),
          });
        } else {
          const formData = new FormData();
          formData.append('file', file);
          formData.append('method', 'document');
          response = await fetch(`${config.API_BASE_URL}/study_guide/generate_visual_study_guide`, {
            method: 'POST',
            body: formData,
          });
        }
      } else {
        throw new Error(`Unknown method "${method}"`);
      }

      // Defensive JSON parse
      let result;
      try {
        result = await response.json();
      } catch {
        throw new Error(`Invalid JSON from server (status ${response?.status})`);
      }

      if (!response.ok) {
        throw new Error(result?.error || `Request failed (${response.status})`);
      }

      setStudyGuide(result);
    } catch (err) {
      setError(err.message || 'Failed to generate the study guide.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    setMethod('category');
    setCategory('');
    setText('');
    setFile(null);
    setSelectedVaultFile('');
    setStudyGuide(null);
    setError(null);
    setFilter('');
    setSortBy('order');
    setCompact(false);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // ----- Derived UI -----
  const topics = useMemo(() => {
    const arr = Array.isArray(studyGuide?.topics) ? [...studyGuide.topics] : [];
    // filter
    const q = filter.trim().toLowerCase();
    const filtered = q
      ? arr.filter(t =>
          (t.name || '').toLowerCase().includes(q) ||
          (t.study_method || '').toLowerCase().includes(q) ||
          (Array.isArray(t.resources) ? t.resources.join(' ').toLowerCase().includes(q) : false)
        )
      : arr;

    // sort
    if (sortBy === 'time') {
      filtered.sort((a, b) => (a.time ?? 1e9) - (b.time ?? 1e9));
    } else if (sortBy === 'alpha') {
      filtered.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    } else {
      filtered.sort((a, b) => (a.order ?? 1e9) - (b.order ?? 1e9));
    }
    return filtered;
  }, [studyGuide, filter, sortBy]);

  const totalMinutes = useMemo(() => {
    if (!Array.isArray(studyGuide?.topics)) return 0;
    return studyGuide.topics.reduce((sum, t) => sum + (parseInt(t.time) || 0), 0);
  }, [studyGuide]);

  // exports
  const downloadJSON = () => {
    const blob = new Blob([JSON.stringify(studyGuide, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    triggerDownload(url, 'study_guide.json');
  };

  const downloadMarkdown = () => {
    const md = toMarkdown(studyGuide);
    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    triggerDownload(url, 'study_guide.md');
  };

  const triggerDownload = (url, filename) => {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  useEffect(() => {
    (async () => {
      try {
        const res = await axiosInstance.get('/upload/files');
        setVaultFiles(res.data.files || []);
      } catch {
        // silent fail; dropdown will just be empty
      }
    })();
  }, []);

  return (
    <div className="vsg-wrap">
      {!studyGuide ? (
        <div className="vsg-card">
          <header className="vsg-header">
            <h1 className="vsg-title">🎨 Visual Study Guide Maker</h1>
            <p className="vsg-subtitle">Create a clean, visual study plan from a category, text, or document.</p>
          </header>

          {/* input method segmented control */}
          <div className="vsg-seg">
            <button
              type="button"
              className={`seg-btn ${method === 'category' ? 'active' : ''}`}
              onClick={() => setMethod('category')}
            >
              Category
            </button>
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

          <form onSubmit={handleSubmit} className="vsg-form">
            {method === 'category' && (
              <div className="vsg-field">
                <label className="vsg-label" htmlFor="category">Category</label>
                <input
                  id="category"
                  className="vsg-input"
                  type="text"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  placeholder="e.g., Newtonian Mechanics, Organic Chemistry, Mughal Empire"
                  autoFocus
                />
                <div className="hint">Tip: Be specific to get a better plan (e.g., “Thermodynamics basics”).</div>
              </div>
            )}

            {method === 'text' && (
              <div className="vsg-field">
                <label className="vsg-label" htmlFor="text">Paste Text</label>
                <textarea
                  id="text"
                  className="vsg-textarea"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  placeholder="Paste a paragraph or two. We’ll extract topics and build a plan."
                  rows={8}
                />
                <div className="hint">At least 10 characters.</div>
              </div>
            )}

            {method === 'document' && (
            <div className="vsg-field">
              <label className="vsg-label">Choose Document</label>

              {/* Row: Upload button + file name */}
              <div className="vsg-upload">
                <input
                  ref={fileInputRef}
                  id="file"
                  type="file"
                  onChange={(e) => {
                    onFilePicked(e);
                    // if user uploads a file, clear any vault selection
                    setSelectedVaultFile('');
                  }}
                  hidden
                />
                <label htmlFor="file" className="btn-ghost">{file ? 'Change File' : 'Upload File'}</label>
                <span className="vsg-file-name">{file ? file.name : 'No file selected'}</span>
                {file && (
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => { setFile(null); if (fileInputRef.current) fileInputRef.current.value = ''; }}
                    title="Clear uploaded file"
                    style={{ marginLeft: 8 }}
                  >
                    ✕
                  </button>
                )}
              </div>

              {/* Divider */}
              <div className="vsg-divider">or</div>

              {/* Row: Knowledge Vault dropdown */}
              <div className="vsg-upload">
                <select
                  className="vsg-select"
                  value={selectedVaultFile}
                  onChange={(e) => {
                    setSelectedVaultFile(e.target.value);
                    // if user picks from vault, clear any uploaded file
                    if (fileInputRef.current) fileInputRef.current.value = '';
                    setFile(null);
                  }}
                  aria-label="Select from Knowledge Vault"
                >
                  <option value="">Vault: choose file…</option>
                  {vaultFiles.map((vf, idx) => (
                    <option key={idx} value={vf.stored_name}>{vf.name}</option>
                  ))}
                </select>
                {selectedVaultFile && (
                  <button
                    type="button"
                    className="btn-ghost"
                    onClick={() => setSelectedVaultFile('')}
                    title="Clear vault selection"
                    style={{ marginLeft: 8 }}
                  >
                    ✕
                  </button>
                )}
              </div>

              <div className="hint">Max 25MB for uploads. PDFs and DOCX work best. Vault files don’t hit this limit.</div>
            </div>
          )}

            {error && <div className="vsg-error">{error}</div>}

            <div className="vsg-actions">
              <button type="submit" className="btn-primary" disabled={!canSubmit}>
                {submitting ? 'Generating…' : 'Generate Study Guide'}
              </button>
              <button type="button" className="btn-secondary" onClick={handleReset} disabled={submitting}>
                Reset
              </button>
            </div>
          </form>
        </div>
      ) : (
        <div className="vsg-results">
          <div className="vsg-results-head">
            <div className="vsg-results-left">
              <h2>Your Visual Study Guide</h2>
              <div className="vsg-mini-stats">
                <StatChip label="Topics" value={Array.isArray(studyGuide.topics) ? studyGuide.topics.length : 0} />
                <StatChip label="Total Minutes" value={totalMinutes} />
              </div>
            </div>
            <div className="vsg-results-actions">
              <button className="btn-secondary" onClick={() => setCompact(v => !v)}>
                {compact ? 'Comfort View' : 'Compact View'}
              </button>
              <button className="btn-secondary" onClick={downloadMarkdown}>Export Markdown</button>
              <button className="btn-secondary" onClick={downloadJSON}>Export JSON</button>
              <button className="btn-primary" onClick={handleReset}>Create Another</button>
            </div>
          </div>

          {/* summary (optional) */}
          {studyGuide?.summary && (
            <div className="vsg-summary">
              <ReactMarkdown>{String(studyGuide.summary)}</ReactMarkdown>
            </div>
          )}

          {/* toolbar: filter/sort */}
          <div className="vsg-toolbar">
            <input
              type="text"
              className="vsg-input"
              placeholder="Filter topics (keyword)…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              style={{maxWidth: 380}}
            />
            <div className="vsg-sort">
              <label className="vsg-label" style={{margin:0}}>Sort By</label>
              <select className="vsg-select" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
                <option value="order">Order</option>
                <option value="time">Time (asc)</option>
                <option value="alpha">Alphabetical</option>
              </select>
            </div>
          </div>

          {/* progress bar (total minutes to relative scale) */}
          <StudyLoadBar minutes={totalMinutes} />

          <div className={`vsg-topics ${compact ? 'compact' : ''}`}>
            {topics.length > 0 ? (
              topics.map((topic, idx) => (
                <div key={`${topic.name}-${idx}`} className="topic-card">
                  <div className="topic-head">
                    <span className="topic-order">#{topic.order ?? idx + 1}</span>
                    <h3 className="topic-title">{topic.name || 'Untitled Topic'}</h3>
                    {!!topic.time && <span className="topic-chip">{topic.time} min</span>}
                  </div>

                  {topic.study_method && (
                    <div className="topic-body">
                      <ReactMarkdown>{String(topic.study_method)}</ReactMarkdown>
                    </div>
                  )}

                  {Array.isArray(topic.resources) && topic.resources.length > 0 && (
                    <div className="topic-resources">
                      {topic.resources.map((r, i) => (
                        <span className="topic-chip" key={i}>{r}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="empty">No topics match your filter.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------- little helpers ---------- */

function StatChip({ label, value }) {
  return (
    <span className="stat-chip">
      <b>{value}</b> <span>{label}</span>
    </span>
  );
}

function StudyLoadBar({ minutes }) {
  const cap = Math.max(minutes, 60); // scale baseline 60 min
  const pct = Math.min(100, Math.round((minutes / cap) * 100));
  return (
    <div className="vsg-load">
      <div className="vsg-load-head">
        <span>Study Load</span>
        <span>{minutes} min</span>
      </div>
      <div className="vsg-load-rail">
        <div className="vsg-load-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function toMarkdown(guide) {
  if (!guide) return '# Study Guide\n\n_No data_';
  let md = `# Study Guide\n\n`;
  if (guide.summary) {
    md += `${guide.summary}\n\n`;
  }
  const topics = Array.isArray(guide.topics) ? [...guide.topics] : [];
  topics.sort((a, b) => (a.order ?? 1e9) - (b.order ?? 1e9));
  for (const t of topics) {
    md += `## ${t.order ? `${t.order}. ` : ''}${t.name || 'Topic'}\n\n`;
    if (t.time) md += `**Time:** ${t.time} min  \n`;
    if (Array.isArray(t.resources) && t.resources.length) {
      md += `**Resources:** ${t.resources.join(', ')}  \n`;
    }
    if (t.study_method) md += `\n${t.study_method}\n\n`;
  }
  return md.trim() + '\n';
}