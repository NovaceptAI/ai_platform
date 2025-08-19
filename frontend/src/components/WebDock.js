import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import './WebDock.css';
import axios from '../utils/axiosInstance';

const TABS = ["Ask / Search", "Paste Links", "Queue", "Results"];

export default function WebDock({ isOpen, onClose }) {
  const [active, setActive] = useState(0);
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState([]);
  const [paste, setPaste] = useState("");
  const [queuing, setQueuing] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [items, setItems] = useState([]);
  const [toast, setToast] = useState(null);

  const showToast = useCallback((msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 1800);
  }, []);

  // Poll jobs when Queue tab is active
  useEffect(() => {
    let timer;
    const fetchJobs = async () => {
      try {
        const r = await axios.get('/web/jobs');
        setJobs(r.data.jobs || []);
      } catch {}
    };
    if (active === 2 && isOpen) {
      fetchJobs();
      timer = setInterval(fetchJobs, 2500);
    }
    return () => timer && clearInterval(timer);
  }, [active, isOpen]);

  // Load results when Results tab opens
  useEffect(() => {
    const fetchResults = async () => {
      try {
        const r = await axios.get('/web/results');
        setItems(r.data.items || []);
      } catch {}
    };
    if (active === 3 && isOpen) fetchResults();
  }, [active, isOpen]);

  const doSearch = useCallback(async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const r = await axios.post('/web/search', { query });
      setResults(r.data.results || []);
      setActive(0);
    } catch (e) {
      showToast('Search failed');
    } finally {
      setSearching(false);
    }
  }, [query, showToast]);

  const queueUrls = useCallback(async (urls) => {
    if (!urls || urls.length === 0) return;
    setQueuing(true);
    try {
      await axios.post('/web/queue', { urls });
      showToast('Queued for scraping');
      setActive(2);
    } catch (e) {
      showToast('Queue failed');
    } finally {
      setQueuing(false);
    }
  }, [showToast]);

  const validateUrls = useCallback((text) => {
    const lines = text.split(/\n+/).map(s => s.trim()).filter(Boolean);
    const valid = lines.filter(u => /^https?:\/\//i.test(u));
    return { valid, invalid: lines.filter(u => !/^https?:\/\//i.test(u)) };
  }, []);

  const copyText = (t) => navigator.clipboard.writeText(t).then(() => showToast('Copied'));

  return (
    <div className={`webdock-container ${isOpen ? '' : 'closed'}`}>
      <div className="webdock-header">
        <div className="webdock-title">🔎 API Scraper / Web Browser</div>
        <button className="webdock-btn" onClick={onClose}>✕</button>
      </div>

      <div className="webdock-tabs">
        {TABS.map((t, i) => (
          <button key={t} className={`webdock-tab ${active === i ? 'active' : ''}`} onClick={() => setActive(i)}>
            {t}
          </button>
        ))}
      </div>

      <div className="webdock-body">
        {active === 0 && (
          <div className="webdock-section">
            <input className="webdock-input" placeholder="Ask or search the web..." value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && doSearch()} />
            <div className="webdock-actions">
              <button className="webdock-btn primary" onClick={doSearch} disabled={searching}>{searching ? 'Searching...' : 'Search'}</button>
            </div>
            <div className="webdock-list">
              {results.map((r, idx) => (
                <div key={idx} className="webdock-card">
                  <div className="webdock-card-title">{r.title}</div>
                  <div className="webdock-card-meta">{r.domain}</div>
                  <div style={{fontSize:12, color:'#cbd5e1', marginBottom:6}}>{r.snippet}</div>
                  <div className="webdock-card-actions">
                    <a className="webdock-btn" href={r.url} target="_blank" rel="noreferrer">Open</a>
                    <button className="webdock-btn" onClick={() => queueUrls([r.url])} disabled={queuing}>Queue to Scrape</button>
                    <button className="webdock-btn" onClick={() => copyText(r.url)}>Copy</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {active === 1 && (
          <div className="webdock-section">
            <textarea className="webdock-textarea" placeholder="Paste one URL per line" value={paste} onChange={(e) => setPaste(e.target.value)} />
            <div className="webdock-actions">
              <button className="webdock-btn primary" onClick={() => {
                const { valid } = validateUrls(paste);
                queueUrls(valid);
              }} disabled={queuing}>Queue to Scrape</button>
            </div>
          </div>
        )}

        {active === 2 && (
          <div className="webdock-section">
            <div className="webdock-list">
              {jobs.map((j) => (
                <div key={j.id} className="webdock-card">
                  <div className="webdock-card-title" title={j.title || j.url}>{j.title || j.url}</div>
                  <div className="webdock-card-meta">{j.domain || new URL(j.url).hostname} • {j.status}</div>
                  <div className="webdock-progress"><div style={{width: `${j.progress||0}%`}}/></div>
                </div>
              ))}
            </div>
          </div>
        )}

        {active === 3 && (
          <div className="webdock-section">
            <div className="webdock-list">
              {items.map((it) => (
                <div key={it.id} className="webdock-card">
                  <div className="webdock-card-title" title={it.title}>{it.title || it.source_url}</div>
                  <div className="webdock-card-meta">{new URL(it.source_url).hostname}</div>
                  <div style={{fontSize:12, color:'#cbd5e1', marginBottom:6}}>{(it.summary || '').slice(0,240)}</div>
                  <div className="webdock-card-actions">
                    <button className="webdock-btn" onClick={() => copyText(`# ${it.title}\n\n${it.summary || ''}`)}>Copy Markdown</button>
                    <button className="webdock-btn" onClick={() => copyText(JSON.stringify(it, null, 2))}>Export JSON</button>
                    <button className="webdock-btn" onClick={() => { window.dispatchEvent(new CustomEvent('insert-into-editor', { detail: it })); showToast('Sent to editor'); }}>Insert into Editor</button>
                    <button className="webdock-btn" disabled>Saved to Vault</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {toast && <div className="webdock-toast">{toast}</div>}
    </div>
  );
}

