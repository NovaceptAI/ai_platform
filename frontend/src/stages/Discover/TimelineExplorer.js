import React, { useEffect, useMemo, useRef, useState } from 'react';
import './TimelineExplorer.css';
import config from '../../config';
import axiosInstance from '../../utils/axiosInstance';

export default function TimelineExplorer() {
  const [method, setMethod] = useState('category'); // 'category' | 'text' | 'document'
  const [category, setCategory] = useState('');
  const [text, setText] = useState('');

  // Vault selection
  const [vaultFiles, setVaultFiles] = useState([]);
  const [selectedVaultFile, setSelectedVaultFile] = useState('');

  // Run / progress
  const [progressId, setProgressId] = useState(null);
  const [pct, setPct] = useState(0);
  const [status, setStatus] = useState('idle');
  const [loading, setLoading] = useState(false);

  // Result
  const [timeline, setTimeline] = useState([]);
  const [error, setError] = useState('');

  // UI extras
  const [filter, setFilter] = useState('');
  const [groupByYear, setGroupByYear] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const res = await axiosInstance.get('/upload/files');
        setVaultFiles(res.data.files || []);
      } catch {
        // silent
      }
    })();
  }, []);

  // Poll progress
  useEffect(() => {
    if (!progressId) return;
    const iv = setInterval(async () => {
      try {
        const r = await fetch(`${config.API_BASE_URL}/timeline_explorer/progress/${progressId}`);
        const j = await r.json();
        setPct(j.percentage ?? 0);
        setStatus(j.status || 'in_progress');
        if (j.status === 'completed' || (j.percentage ?? 0) >= 100) {
          clearInterval(iv);
          await fetchResult(progressId);
        }
      } catch {
        // ignore transient errors
      }
    }, 3000);
    return () => clearInterval(iv);
  }, [progressId]);

  const fetchResult = async (pid) => {
    try {
      const r = await fetch(`${config.API_BASE_URL}/timeline_explorer/result/${pid}`);
      const j = await r.json();
      const arr = Array.isArray(j.timeline) ? j.timeline : [];
      setTimeline(arr);
    } catch (e) {
      setError('Failed to fetch result.');
    } finally {
      setLoading(false);
    }
  };

  const startBuild = async (e) => {
    e.preventDefault();
    setError('');
    setTimeline([]);
    setLoading(true);
    setPct(0);
    setStatus('in_progress');
    setProgressId(null);

    try {
      const m = (method || '').trim().toLowerCase();
      let body = {};
      if (m === 'category') {
        if (!category.trim()) throw new Error('Missing category');
        body = { method: 'category', category: category.trim() };
      } else if (m === 'text') {
        if (!text.trim()) throw new Error('Missing text');
        body = { method: 'text', text: text.trim() };
      } else if (m === 'document') {
        if (!selectedVaultFile) throw new Error('Pick a file from Knowledge Vault');
        body = { method: 'document', fromVault: true, filename: selectedVaultFile };
      } else {
        throw new Error('Invalid method');
      }

      const r = await fetch(`${config.API_BASE_URL}/timeline_explorer/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      let j;
      try { j = await r.json(); } catch { j = {}; }
      if (!r.ok) throw new Error(j?.error || `Start failed (${r.status})`);
      setProgressId(j.progress_id);
    } catch (err) {
      setError(err.message || 'Failed to start.');
      setLoading(false);
    }
  };

  const canSubmit = useMemo(() => {
    if (loading || progressId) return false;
    if (method === 'category') return category.trim().length >= 2;
    if (method === 'text') return text.trim().length >= 10;
    if (method === 'document') return !!selectedVaultFile;
    return false;
  }, [loading, progressId, method, category, text, selectedVaultFile]);

  const resetAll = () => {
    setMethod('category');
    setCategory('');
    setText('');
    setSelectedVaultFile('');
    setProgressId(null);
    setPct(0);
    setStatus('idle');
    setTimeline([]);
    setError('');
    setFilter('');
    setGroupByYear(true);
  };

  // ------- Derived UI -------
  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    const arr = Array.isArray(timeline) ? timeline : [];
    if (!q) return arr;
    return arr.filter(ev =>
      (ev.title || '').toLowerCase().includes(q) ||
      (ev.description || '').toLowerCase().includes(q) ||
      (ev.date || '').toLowerCase().includes(q)
    );
  }, [timeline, filter]);

  const grouped = useMemo(() => {
    if (!groupByYear) return null;
    const g = {};
    for (const ev of filtered) {
      const year = parseYear(ev.date);
      const key = isFinite(year) ? String(year) : 'Other';
      (g[key] ||= []).push(ev);
    }
    // sort keys numeric asc but 'Other' last
    const keys = Object.keys(g).sort((a,b) => {
      if (a === 'Other') return 1;
      if (b === 'Other') return -1;
      return Number(a) - Number(b);
    });
    return { g, keys };
  }, [filtered, groupByYear]);

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify({ timeline }, null, 2)], { type:'application/json' });
    const url = URL.createObjectURL(blob);
    dl(url, 'timeline.json');
  };

  const exportCSV = () => {
    const rows = [['date','title','description']];
    for (const ev of timeline) rows.push([ev.date || '', ev.title || '', (ev.description || '').replace(/\n/g,' ')]);
    const csv = rows.map(r => r.map(field => `"${String(field).replace(/"/g,'""')}"`).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type:'text/csv' }));
    dl(url, 'timeline.csv');
  };

  const dl = (url, name) => { const a = document.createElement('a'); a.href=url; a.download=name; a.click(); setTimeout(()=>URL.revokeObjectURL(url), 800); };

  return (
    <div className="timeline-explorer">
      <div className="tl-card">
        <header className="tl-head">
          <h1 className="tl-title">🕰️ Timeline Explorer</h1>
          <p className="tl-subtitle">Generate a chronological sequence from a category, text, or a document in your Knowledge Vault.</p>
        </header>

        {/* Segmented control */}
        <div className="tl-seg">
          {['category','text','document'].map(m => (
            <button
              key={m}
              type="button"
              className={`seg-btn ${method === m ? 'active' : ''}`}
              onClick={() => setMethod(m)}
              disabled={loading || !!progressId}
            >{m[0].toUpperCase()+m.slice(1)}</button>
          ))}
        </div>

        <form onSubmit={startBuild} className="tl-form">
          {method === 'category' && (
            <div className="tl-field">
              <label className="tl-label">Category</label>
              <input
                className="tl-input"
                value={category}
                onChange={e=>setCategory(e.target.value)}
                placeholder="e.g., World War II, Mughal Empire, Web3 history"
              />
              <div className="hint">Be specific to get better events.</div>
            </div>
          )}

          {method === 'text' && (
            <div className="tl-field">
              <label className="tl-label">Paste Text</label>
              <textarea
                className="tl-textarea"
                value={text}
                onChange={e=>setText(e.target.value)}
                placeholder="Paste a few paragraphs. We'll infer key dated events."
                rows={8}
              />
              <div className="hint">At least 10 characters.</div>
            </div>
          )}

          {method === 'document' && (
            <div className="tl-field">
              <label className="tl-label">Knowledge Vault</label>
              <div className="tl-upload">
                <select
                  className="tl-select"
                  value={selectedVaultFile}
                  onChange={e=>setSelectedVaultFile(e.target.value)}
                  aria-label="Select from Knowledge Vault"
                >
                  <option value="">Vault: choose file…</option>
                  {vaultFiles.map((vf, idx) => (
                    <option key={idx} value={vf.stored_name}>{vf.name}</option>
                  ))}
                </select>
                {selectedVaultFile && (
                  <button type="button" className="btn-ghost" onClick={()=>setSelectedVaultFile('')}>✕</button>
                )}
              </div>
              <div className="hint">For now, use vault files (direct upload path can be added later).</div>
            </div>
          )}

          {error && <div className="tl-error">{error}</div>}

          <div className="tl-actions">
            <button type="submit" className="btn-primary" disabled={!canSubmit}>
              {loading || progressId ? 'Working…' : 'Start'}
            </button>
            <button type="button" className="btn-secondary" onClick={resetAll} disabled={loading || !!progressId}>
              Reset
            </button>
          </div>
        </form>

        {/* Inline progress */}
        {progressId && status !== 'completed' && (
          <div className="tl-progress">
            <div className="tl-progress-top">
              <strong>Building timeline…</strong>
              <span>{pct}%</span>
            </div>
            <div className="tl-progress-rail">
              <div className="tl-progress-fill" style={{width:`${Math.max(0,Math.min(100,pct))}%`}} />
            </div>
            <div className="hint">Auto-refreshing every 3 seconds…</div>
          </div>
        )}
      </div>

      {/* Results */}
      {timeline.length > 0 && (
        <div className="tl-results">
          <div className="tl-results-head">
            <h2>Timeline ({timeline.length} events)</h2>
            <div className="tl-results-actions">
              <input
                className="tl-input"
                placeholder="Search events…"
                value={filter}
                onChange={e=>setFilter(e.target.value)}
                style={{maxWidth:300}}
              />
              <label className="switch">
                <input type="checkbox" checked={groupByYear} onChange={e=>setGroupByYear(e.target.checked)} />
                <span>Group by year</span>
              </label>
              <button className="btn-secondary" onClick={exportCSV}>Export CSV</button>
              <button className="btn-secondary" onClick={exportJSON}>Export JSON</button>
            </div>
          </div>

          {groupByYear && grouped ? (
            grouped.keys.map(yr => (
              <div key={yr} className="year-block">
                <h3 className="year-title">{yr}</h3>
                <div className="events-grid">
                  {(grouped.g[yr] || []).map((ev, i) => (
                    <EventCard key={yr+'-'+i} ev={ev} />
                  ))}
                </div>
              </div>
            ))
          ) : (
            <div className="events-grid">
              {filtered.map((ev, i) => <EventCard key={i} ev={ev} />)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EventCard({ ev }) {
  return (
    <div className="event-card">
      <div className="event-head">
        <span className="event-date">{ev.date || '—'}</span>
        <h4 className="event-title">{ev.title || 'Untitled'}</h4>
      </div>
      {ev.description && <p className="event-desc">{ev.description}</p>}
    </div>
  );
}

function parseYear(d) {
  if (!d) return NaN;
  const m = String(d).match(/^\s*(\d{1,4})/);
  return m ? parseInt(m[1], 10) : NaN;
}
