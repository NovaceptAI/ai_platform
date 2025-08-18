import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FaMagic,
  FaRocket,
  FaCopy,
  FaDownload,
  FaSyncAlt,
  FaFilter,
  FaListUl,
  FaCheck
} from 'react-icons/fa';
import '../../stages/StagesHome.css'; // shared stage styles
import './CreativeWritingPrompts.css'; // this tool's creative styles
// Adjust import if your config path differs:
import config from '../../config.js';

const API_BASE =
  (config && config.API_BASE_URL) ||
  process.env.REACT_APP_API_BASE_URL ||
  '';

function CreativeWritingPrompts() {
  const [fileId, setFileId] = useState('');
  const [force, setForce] = useState(false);

  const [status, setStatus] = useState('idle'); // idle | starting | running | completed | failed
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');

  const [perPage, setPerPage] = useState([]);
  const [merged, setMerged] = useState([]);
  const [activeTab, setActiveTab] = useState('merged'); // merged | per_page
  const [query, setQuery] = useState('');
  const [tagFilter, setTagFilter] = useState('');

  const pollerRef = useRef(null);

  const accessToken = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  const userId = typeof window !== 'undefined' ? (localStorage.getItem('user_id') || '') : '';

  useEffect(() => {
    return () => {
      if (pollerRef.current) clearInterval(pollerRef.current);
    };
  }, []);

  const headers = useMemo(() => {
    const h = {
      'Content-Type': 'application/json',
      'X-User-Id': userId || ''
    };
    if (accessToken) h['Authorization'] = accessToken.startsWith('Bearer ') ? accessToken : `Bearer ${accessToken}`;
    return h;
  }, [accessToken, userId]);

  async function startJob() {
    setError('');
    if (!fileId) {
      setError('Please enter a file ID.');
      return;
    }

    try {
      setStatus('starting');
      setProgress(0);

      const res = await fetch(`${API_BASE}/creative_prompts/start`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ file_id: fileId, user_id: userId, force })
      });

      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.error || `Failed to start: ${res.status}`);
      }

      const data = await res.json();
      const progressId = data.progress_id;
      setStatus('running');
      setProgress(0);
      pollProgress(progressId);
    } catch (err) {
      setStatus('failed');
      setError(err.message || 'Failed to start job.');
    }
  }

  function pollProgress(progressId) {
    if (pollerRef.current) clearInterval(pollerRef.current);

    pollerRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/creative_prompts/progress/${progressId}`, { headers });
        if (!res.ok) {
          const e = await res.json().catch(() => ({}));
          throw new Error(e.error || `Progress error: ${res.status}`);
        }
        const p = await res.json();
        setProgress(Number(p.percentage || 0));

        if (p.status === 'completed') {
          clearInterval(pollerRef.current);
          pollerRef.current = null;
          setStatus('completed');
          await fetchResults();
        } else if (p.status === 'failed') {
          clearInterval(pollerRef.current);
          pollerRef.current = null;
          setStatus('failed');
          setError('Job failed. Check server logs for details.');
        }
      } catch (err) {
        clearInterval(pollerRef.current);
        pollerRef.current = null;
        setStatus('failed');
        setError(err.message || 'Progress polling failed.');
      }
    }, 1200);
  }

  async function fetchResults() {
    try {
      const res = await fetch(`${API_BASE}/creative_prompts/results?file_id=${encodeURIComponent(fileId)}`, {
        headers
      });
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.error || `Failed to fetch results: ${res.status}`);
      }
      const data = await res.json();
      setPerPage(data.per_page || []);
      setMerged(data.merged || []);
    } catch (err) {
      setError(err.message || 'Failed to fetch results.');
    }
  }

  function filteredMerged() {
    let list = merged;
    if (query.trim()) {
      const q = query.toLowerCase();
      list = list.filter(
        (m) =>
          m.prompt.toLowerCase().includes(q) ||
          (m.genre || '').toLowerCase().includes(q) ||
          (m.tone || '').toLowerCase().includes(q) ||
          (m.tags || []).some((t) => t.toLowerCase().includes(q))
      );
    }
    if (tagFilter.trim()) {
      const t = tagFilter.toLowerCase();
      list = list.filter((m) => (m.tags || []).some((x) => x.toLowerCase().includes(t)));
    }
    return list;
  }

  function filteredPerPage() {
    if (!query.trim() && !tagFilter.trim()) return perPage;
    const q = query.toLowerCase();
    const t = tagFilter.toLowerCase();
    return perPage.map((p) => ({
      ...p,
      prompts: (p.prompts || []).filter((m) => {
        const matchQ =
          !q ||
          m.prompt?.toLowerCase().includes(q) ||
          (m.genre || '').toLowerCase().includes(q) ||
          (m.tone || '').toLowerCase().includes(q) ||
          (m.tags || []).some((x) => x.toLowerCase().includes(q));
        const matchT = !t || (m.tags || []).some((x) => x.toLowerCase().includes(t));
        return matchQ && matchT;
      })
    }));
  }

  function copyPrompt(text) {
    navigator.clipboard.writeText(text || '').then(() => {
      // brief visual confirmation would be nice:
      // handled by a small state flash inside the card, see CSS :active for button
    });
  }

  function downloadJSON() {
    const payload = { file_id: fileId, merged, per_page: perPage };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.download = `creative_prompts_${fileId || 'results'}.json`;
    a.href = url;
    a.click();
    URL.revokeObjectURL(url);
  }

  const showResults = status === 'completed' && (merged.length || perPage.length);

  return (
    <div className="cw-wrap">
      <header className="cw-hero">
        <div className="cw-hero-glow" />
        <h1 className="cw-title"><FaMagic className="cw-title-icon" /> Creative Writing Prompts</h1>
        <p className="cw-subtitle">Transform your documents into vivid, ready-to-use story starters.</p>
      </header>

      <section className="cw-toolbar card-ghost">
        <div className="cw-row">
          <label className="cw-label">
            <span>File ID</span>
            <input
              className="cw-input"
              value={fileId}
              onChange={(e) => setFileId(e.target.value)}
              placeholder="e.g. 0b4a7f7c-…"
            />
          </label>

          <label className="cw-check">
            <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} />
            <span>Regenerate (ignore cached)</span>
          </label>

          <div className="cw-actions">
            <button
              className="btn-primary cw-start"
              onClick={startJob}
              disabled={status === 'starting' || status === 'running'}
              title="Start prompt generation"
            >
              <FaRocket /> {status === 'running' || status === 'starting' ? 'Working…' : 'Generate'}
            </button>

            <button
              className="btn-ghost"
              onClick={fetchResults}
              disabled={!fileId}
              title="Fetch latest results"
            >
              <FaSyncAlt /> Refresh
            </button>
          </div>
        </div>

        {(status === 'running' || status === 'starting') && (
          <div className="cw-progress">
            <div className="cw-progress-bar" style={{ width: `${progress}%` }} />
            <div className="cw-progress-text">{progress}%</div>
          </div>
        )}

        {error && <div className="cw-error">{error}</div>}
      </section>

      {showResults && (
        <section className="cw-results">
          <div className="cw-results-top">
            <div className="cw-tabs">
              <button
                className={`cw-tab ${activeTab === 'merged' ? 'active' : ''}`}
                onClick={() => setActiveTab('merged')}
              >
                <FaListUl /> Merged
              </button>
              <button
                className={`cw-tab ${activeTab === 'per_page' ? 'active' : ''}`}
                onClick={() => setActiveTab('per_page')}
              >
                Pages
              </button>
            </div>

            <div className="cw-searchbar">
              <div className="cw-search">
                <FaFilter />
                <input
                  className="cw-input"
                  placeholder="Search prompt / genre / tone / tag…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
              </div>
              <input
                className="cw-input cw-tag-input"
                placeholder="Filter by tag (e.g. mystery)"
                value={tagFilter}
                onChange={(e) => setTagFilter(e.target.value)}
              />
              <button className="btn-ghost" onClick={downloadJSON}><FaDownload /> Download JSON</button>
            </div>
          </div>

          {activeTab === 'merged' ? (
            <div className="cw-grid">
              {filteredMerged().map((m, idx) => (
                <PromptCard key={`${m.prompt}-${idx}`} item={m} onCopy={copyPrompt} />
              ))}
              {!filteredMerged().length && <div className="cw-empty">No prompts match your filters.</div>}
            </div>
          ) : (
            <div className="cw-pages">
              {filteredPerPage().map((pg) => (
                <div key={`page-${pg.page}`} className="cw-page-block">
                  <h3 className="cw-page-title">Page {pg.page}</h3>
                  <div className="cw-grid">
                    {(pg.prompts || []).map((m, idx) => (
                      <PromptCard key={`p${pg.page}-${idx}`} item={m} onCopy={copyPrompt} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {!showResults && status === 'idle' && (
        <div className="cw-placeholder">
          <p>Enter a <strong>File ID</strong> and hit <strong>Generate</strong> to craft tailored prompts from your document.</p>
        </div>
      )}

      <footer className="cw-footnote">
        <span className="muted">Tip: click tags to set the tag filter.</span>
        <Link to="/create" className="cw-back">← Back to Create</Link>
      </footer>
    </div>
  );
}

function PromptCard({ item, onCopy }) {
  const [copied, setCopied] = useState(false);
  const tags = item.tags || [];

  function onCopyClick() {
    onCopy(item.prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 900);
  }

  return (
    <div className="cw-card">
      <div className="cw-card-body">
        <p className="cw-prompt">“{item.prompt}”</p>
        <div className="cw-meta">
          {item.genre && <span className="cw-chip">{item.genre}</span>}
          {item.tone && <span className="cw-chip">{item.tone}</span>}
          {tags.map((t) => (
            <button
              key={t}
              className="cw-chip chip-ghost"
              onClick={() => {
                const el = document.querySelector('.cw-tag-input');
                if (el) el.value = t;
                const evt = new Event('input', { bubbles: true });
                if (el) el.dispatchEvent(evt);
              }}
              title="Filter by tag"
            >
              #{t}
            </button>
          ))}
        </div>
      </div>
      <div className="cw-card-actions">
        <button className="btn-primary" onClick={onCopyClick} title="Copy prompt">
          {copied ? <><FaCheck /> Copied</> : <><FaCopy /> Copy</>}
        </button>
      </div>
    </div>
  );
}

export default CreativeWritingPrompts;