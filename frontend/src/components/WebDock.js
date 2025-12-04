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
  const [sources, setSources] = useState([]);
  const [selectedSource, setSelectedSource] = useState('duckduckgo');
  const [loadingSources, setLoadingSources] = useState(false);
  
  const pollingIntervalRef = useRef(null);

  const showToast = useCallback((msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 1800);
  }, []);

  // Load available sources on mount
  useEffect(() => {
    const fetchSources = async () => {
      if (!isOpen) return;
      setLoadingSources(true);
      try {
        const r = await axios.get('/web/sources');
        setSources(r.data.sources || []);
      } catch (e) {
        console.error('Failed to load sources:', e);
      } finally {
        setLoadingSources(false);
      }
    };
    fetchSources();
  }, [isOpen]);

  // Poll jobs when Queue tab is active
  useEffect(() => {
    const fetchJobs = async () => {
      try {
        const r = await axios.get('/web/jobs');
        const fetchedJobs = r.data.jobs || [];
        setJobs(fetchedJobs);
        
        // Stop polling if all jobs are done or failed
        const hasActiveJobs = fetchedJobs.some(j => 
          j.status === 'pending' || j.status === 'in_progress'
        );
        
        if (!hasActiveJobs && pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
          pollingIntervalRef.current = null;
        }
      } catch (err) {
        console.error('Failed to fetch jobs:', err);
      }
    };
    
    if (active === 2 && isOpen) {
      fetchJobs(); // Initial fetch
      // Only start polling if not already polling
      if (!pollingIntervalRef.current) {
        pollingIntervalRef.current = setInterval(fetchJobs, 2500);
      }
    }
    
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
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
      const r = await axios.post('/web/search', { 
        query,
        source: selectedSource,
        limit: 10
      });
      setResults(r.data.results || []);
      setActive(0);
      if (r.data.errors && r.data.errors.length > 0) {
        console.warn('Search errors:', r.data.errors);
      }
    } catch (e) {
      showToast('Search failed');
      console.error('Search error:', e);
    } finally {
      setSearching(false);
    }
  }, [query, selectedSource, showToast]);

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
            
            {/* Source Selector */}
            <div className="webdock-source-selector">
              <label className="webdock-label">Search Source:</label>
              <select 
                className="webdock-select" 
                value={selectedSource} 
                onChange={(e) => setSelectedSource(e.target.value)}
                disabled={loadingSources}
              >
                <option value="all">🌐 All Sources</option>
                {sources.filter(s => s.enabled).map(source => (
                  <option key={source.name} value={source.name}>
                    {source.icon} {source.display_name}
                    {source.requires_key && !source.enabled ? ' (needs key)' : ''}
                    {source.is_free ? ' 🆓' : ''}
                  </option>
                ))}
              </select>
            </div>

            <div className="webdock-actions">
              <button className="webdock-btn primary" onClick={doSearch} disabled={searching}>{searching ? 'Searching...' : 'Search'}</button>
            </div>
            <div className="webdock-list">
              {results.map((r, idx) => (
                <div key={idx} className="webdock-card">
                  {r.source && (
                    <div className="webdock-source-badge">
                      <span className="source-icon">{r.source_icon}</span>
                      <span className="source-name">{r.source}</span>
                    </div>
                  )}
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
            {/* Queue Summary */}
            {jobs.length > 0 && (
              <div className="webdock-queue-summary">
                {jobs.filter(j => j.status === 'done').length > 0 && (
                  <span className="queue-stat">✅ {jobs.filter(j => j.status === 'done').length} completed</span>
                )}
                {jobs.filter(j => j.status === 'in_progress' || j.status === 'pending').length > 0 && (
                  <span className="queue-stat">⏳ {jobs.filter(j => j.status === 'in_progress' || j.status === 'pending').length} in progress</span>
                )}
                {jobs.filter(j => j.status === 'failed').length > 0 && (
                  <span className="queue-stat">❌ {jobs.filter(j => j.status === 'failed').length} failed</span>
                )}
              </div>
            )}
            
            <div className="webdock-list">
              {jobs.map((j) => (
                <div key={j.id} className={`webdock-card ${j.status === 'done' ? 'job-done' : j.status === 'failed' ? 'job-failed' : ''}`}>
                  {j.status === 'done' && <div className="job-status-icon">✓</div>}
                  {j.status === 'failed' && <div className="job-status-icon error">✗</div>}
                  <div className="webdock-card-title" title={j.title || j.url}>{j.title || j.url}</div>
                  <div className="webdock-card-meta">
                    {j.domain || (j.url ? new URL(j.url).hostname : '')} • 
                    <span className={`status-badge status-${j.status}`}> {j.status}</span>
                  </div>
                  {j.status !== 'done' && j.status !== 'failed' && (
                    <div className="webdock-progress">
                      <div style={{width: `${j.progress||0}%`}}/>
                    </div>
                  )}
                  {j.error && (
                    <div className="job-error">Error: {j.error}</div>
                  )}
                  {j.status === 'done' && j.result_id && (
                    <div className="webdock-card-actions">
                      <button className="webdock-btn primary" onClick={() => setActive(3)}>View Result</button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {active === 3 && (
          <div className="webdock-section">
            <div className="webdock-list">
              {items.map((it) => (
                <div key={it.id} className="webdock-card webdock-result-card">
                  <div className="webdock-card-title" title={it.title}>{it.title || it.source_url}</div>
                  <div className="webdock-card-meta">
                    {new URL(it.source_url).hostname} • {new Date(it.created_at).toLocaleDateString()}
                  </div>
                  
                  {/* Summary */}
                  <div className="webdock-result-summary">{it.summary || ''}</div>
                  
                  {/* Key Points */}
                  {it.structured_json?.key_points && it.structured_json.key_points.length > 0 && (
                    <details className="webdock-details">
                      <summary className="webdock-details-summary">
                        📌 Key Points ({it.structured_json.key_points.length})
                      </summary>
                      <ul className="webdock-list-bullets">
                        {it.structured_json.key_points.slice(0, 5).map((point, idx) => (
                          <li key={idx}>{point}</li>
                        ))}
                        {it.structured_json.key_points.length > 5 && (
                          <li style={{fontStyle:'italic'}}>...and {it.structured_json.key_points.length - 5} more</li>
                        )}
                      </ul>
                    </details>
                  )}
                  
                  {/* Entities */}
                  {it.structured_json?.entities && it.structured_json.entities.length > 0 && (
                    <div className="webdock-entities">
                      <span className="webdock-entities-label">🏷️ Entities:</span>
                      <div className="webdock-tags">
                        {it.structured_json.entities.slice(0, 8).map((entity, idx) => (
                          <span key={idx} className="webdock-tag">{entity}</span>
                        ))}
                        {it.structured_json.entities.length > 8 && (
                          <span className="webdock-tag">+{it.structured_json.entities.length - 8} more</span>
                        )}
                      </div>
                    </div>
                  )}
                  
                  <div className="webdock-card-actions">
                    <a className="webdock-btn" href={it.source_url} target="_blank" rel="noreferrer">Open Original</a>
                    <button className="webdock-btn" onClick={() => copyText(`# ${it.title}\n\n${it.summary || ''}`)}>Copy Markdown</button>
                    <button className="webdock-btn" onClick={() => copyText(JSON.stringify(it, null, 2))}>Export JSON</button>
                    <button className="webdock-btn" onClick={() => { window.dispatchEvent(new CustomEvent('insert-into-editor', { detail: it })); showToast('Sent to editor'); }}>Insert into Editor</button>
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

