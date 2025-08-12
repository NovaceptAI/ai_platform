import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosInstance from '../../utils/axiosInstance';
import '../../stages/StagesHome.css';

// --- Tiny progress bar used inline when modal is closed ---
function InlineProgress({ percentage = 0 }) {
  const pct = Math.max(0, Math.min(100, Number(percentage) || 0));
  return (
    <div style={{marginTop:16, padding:16, borderRadius:12, background:'rgba(0,0,0,0.04)'}}>
      <div style={{display:'flex', justifyContent:'space-between', marginBottom:8}}>
        <strong>Processing…</strong>
        <span>{pct}%</span>
      </div>
      <div style={{height:10, borderRadius:6, overflow:'hidden', background:'rgba(0,0,0,0.08)'}}>
        <div style={{
          width: `${pct}%`,
          height: '100%',
          transition: 'width .4s ease',
          background: 'linear-gradient(90deg,#7c3aed,#06b6d4)'
        }}/>
      </div>
      <div style={{fontSize:12, opacity:.7, marginTop:8}}>Auto-refreshing every 3 seconds…</div>
    </div>
  );
}

// --- A4/Word-like single page viewer ---
function A4Page({ title, content }) {
  return (
    <div style={{
      margin:'24px auto',
      width:'min(900px, 92vw)',
      minHeight:'calc(900px * 1.4142 * 0.7)', // rough A4 ratio, scaled a bit for screens
      background:'#fff',
      borderRadius:12,
      boxShadow:'0 12px 30px rgba(0,0,0,0.12)',
      padding:'48px 56px',
      lineHeight:1.6
    }}>
      <h3 style={{marginTop:0, marginBottom:16}}>{title}</h3>
      <div style={{whiteSpace:'pre-wrap'}}>{content || '—'}</div>
    </div>
  );
}

// --- Tabs header ---
const TABS = [
  { key: 'pages', label: 'Pages' },
  { key: 'topics', label: 'Topics' },
  { key: 'compare', label: 'Compare Pages' },
  { key: 'chronology', label: 'Chronology' },
  { key: 'sentiment', label: 'Sentiment Analyser' },
  { key: 'segments', label: 'Segments' },
  { key: 'doc', label: 'Document Analysis' },
];

export default function Summarizer() {
  const navigate = useNavigate();

  // file + results
  const [selectedVaultFile, setSelectedVaultFile] = useState('');
  const [vaultFiles, setVaultFiles] = useState([]);
  const [summaryPages, setSummaryPages] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  // progress
  const [showProcessingModal, setShowProcessingModal] = useState(false);
  const [progressPercentage, setProgressPercentage] = useState(0);
  const [progressId, setProgressId] = useState(null);
  const [fileId, setFileId] = useState(null);

  // UI state
  const [activeTab, setActiveTab] = useState('pages');
  const [currentPageIndex, setCurrentPageIndex] = useState(0);

  // Topics tab state
  const [topicsData, setTopicsData] = useState(null);
  const [topicsLoading, setTopicsLoading] = useState(false);
  const [topicsProgressId, setTopicsProgressId] = useState(null);
  const [topicsPct, setTopicsPct] = useState(0);
  const [topicsError, setTopicsError] = useState('');

  // Chronology state
  const [chronoData, setChronoData] = useState(null);     // { per_page:[], merged:[] }
  const [chronoProgressId, setChronoProgressId] = useState(null);
  const [chronoPct, setChronoPct] = useState(0);
  const [chronoLoading, setChronoLoading] = useState(false);
  const [chronoError, setChronoError] = useState('');
  const [chronoView, setChronoView] = useState('merged'); // 'merged' | 'per_page'

  // Sentiment analysis state
  const [sentData, setSentData] = useState(null);          // { per_page, doc }
  const [sentProgId, setSentProgId] = useState(null);
  const [sentPct, setSentPct] = useState(0);
  const [sentLoading, setSentLoading] = useState(false);
  const [sentError, setSentError] = useState('');
  
  // Segments state
const [segData, setSegData] = useState(null);       // { per_page: [{page, segments}], outline: [...] }
const [segProgId, setSegProgId] = useState(null);
const [segPct, setSegPct] = useState(0);
const [segLoading, setSegLoading] = useState(false);
const [segError, setSegError] = useState('');
const [segView, setSegView] = useState('outline');  // 'outline' | 'per_page'

// Document Analysis state
const [docData, setDocData] = useState(null);     // { per_page:[{page, analysis}], doc:{...}, mind_map? }
const [docProgId, setDocProgId] = useState(null);
const [docPct, setDocPct] = useState(0);
const [docLoading, setDocLoading] = useState(false);
const [docError, setDocError] = useState('');
const [docShowMap, setDocShowMap] = useState(false);

  useEffect(() => { fetchVaultFiles(); }, []);

  // Poll progress every 3s while we have an active progressId
  useEffect(() => {
    if (!progressId || !fileId) return;
    const interval = setInterval(async () => {
      try {
        const res = await axiosInstance.get(`/summarizer/progress/${progressId}`);
        const { percentage = 0, status } = res.data || {};
        setProgressPercentage(percentage ?? 0);

        // Consider done/complete conditions
        if (status === 'done' || status === 'completed' || (percentage ?? 0) >= 100) {
          clearInterval(interval);
          setShowProcessingModal(false);
          await fetchSummary(fileId);
        }
      } catch (e) {
        // Keep polling; just log
        // console.error('Progress check failed', e);
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [progressId, fileId]);

// Kick off Topics when the Topics tab is opened
useEffect(() => {
  if (activeTab !== 'topics') return;
  if (!fileId) return;
  if (topicsData || topicsLoading || topicsProgressId) return; // already loaded or in-flight

  let pollTimer = null;

  (async () => {
    try {
      setTopicsLoading(true);
      setTopicsError('');

      // 1) start
      const start = await axiosInstance.post('/modeller/topics/start', {
        file_id: fileId,
        user_id: 'admin', // TODO: replace with real user id/header
      });
      const { progress_id } = start.data || {};
      if (!progress_id) throw new Error('Could not start topic extraction.');
      setTopicsProgressId(progress_id);
      setTopicsPct(0);

      // 2) poll every 3s
      pollTimer = setInterval(async () => {
        try {
          const pr = await axiosInstance.get(`/modeller/topics/progress/${progress_id}`);
          const { percentage = 0, status } = pr.data || {};
          setTopicsPct(percentage ?? 0);

          if (status === 'completed' || (percentage ?? 0) >= 100) {
            clearInterval(pollTimer);
            // 3) fetch results
            const res = await axiosInstance.get(`/modeller/topics/results?file_id=${fileId}`);
            setTopicsData(res.data);
            setTopicsLoading(false);
            setTopicsProgressId(null);
          }
          if (status === 'failed') {
            clearInterval(pollTimer);
            setTopicsLoading(false);
            setTopicsError('Topic extraction failed. Please try again.');
            setTopicsProgressId(null);
          }
        } catch {
          // keep polling quietly
        }
      }, 3000);
    } catch (e) {
      setTopicsLoading(false);
      setTopicsError(e?.response?.data?.error || e?.message || 'Could not start topic extraction.');
      setTopicsProgressId(null);
    }
  })();

  return () => {
    if (pollTimer) clearInterval(pollTimer);
  };
}, [activeTab, fileId, topicsData, topicsLoading, topicsProgressId]);


useEffect(() => {
  if (activeTab !== 'chronology') return;
  if (!fileId) return;
  if (chronoData || chronoLoading || chronoProgressId) return;

  let t = null;
  (async () => {
    try {
      setChronoError('');
      setChronoLoading(true);
      const { progress_id } = await chronoApi.start(fileId, 'admin', false); // TODO: real user id
      setChronoProgressId(progress_id);
      setChronoPct(0);

      t = setInterval(async () => {
        try {
          const pr = await chronoApi.progress(progress_id);
          const { percentage=0, status } = pr || {};
          setChronoPct(percentage ?? 0);
          if (status === 'completed' || (percentage ?? 0) >= 100) {
            clearInterval(t);
            const res = await chronoApi.results(fileId);
            setChronoData(res);
            setChronoLoading(false);
            setChronoProgressId(null);
          } else if (status === 'failed') {
            clearInterval(t);
            setChronoLoading(false);
            setChronoError('Chronology build failed. Try Rebuild.');
          }
        } catch {}
      }, 3000);
    } catch (e) {
      setChronoLoading(false);
      setChronoError(e?.response?.data?.error || e?.message || 'Could not start chronology.');
    }
  })();

  return () => t && clearInterval(t);
}, [activeTab, fileId, chronoData, chronoLoading, chronoProgressId]);


useEffect(() => {
  if (activeTab !== 'sentiment') return;
  if (!fileId) return;
  if (sentData || sentLoading || sentProgId) return; // already running or loaded

  let timer = null;
  (async () => {
    try {
      setSentError('');
      setSentLoading(true);
      const { progress_id } = await sentimentApi.start(fileId, 'admin', false); // TODO: real user
      setSentProgId(progress_id);
      setSentPct(0);

      timer = setInterval(async () => {
        try {
          const pr = await sentimentApi.progress(progress_id);
          const { percentage=0, status } = pr || {};
          setSentPct(percentage ?? 0);

          if (status === 'completed' || (percentage ?? 0) >= 100) {
            clearInterval(timer);
            const res = await sentimentApi.results(fileId);
            setSentData(res);
            setSentLoading(false);
            setSentProgId(null);
          } else if (status === 'failed') {
            clearInterval(timer);
            setSentLoading(false);
            setSentError('Sentiment analysis failed. Try Rebuild.');
          }
        } catch {/* keep polling */}
      }, 3000);
    } catch (e) {
      setSentLoading(false);
      setSentError(e?.response?.data?.error || e?.message || 'Could not start sentiment analysis.');
    }
  })();

  return () => timer && clearInterval(timer);
}, [activeTab, fileId, sentData, sentLoading, sentProgId]);


useEffect(() => {
  if (activeTab !== 'segments') return;
  if (!fileId) return;
  if (segData || segLoading || segProgId) return;

  let timer = null;
  (async () => {
    try {
      setSegError('');
      setSegLoading(true);
      const { progress_id } = await segmentsApi.start(fileId, 'admin', false); // TODO: real user id
      setSegProgId(progress_id);
      setSegPct(0);

      timer = setInterval(async () => {
        try {
          const pr = await segmentsApi.progress(progress_id);
          const { percentage=0, status } = pr || {};
          setSegPct(percentage ?? 0);
          if (status === 'completed' || (percentage ?? 0) >= 100) {
            clearInterval(timer);
            const res = await segmentsApi.results(fileId);
            setSegData(res);
            setSegLoading(false);
            setSegProgId(null);
          } else if (status === 'failed') {
            clearInterval(timer);
            setSegLoading(false);
            setSegError('Segmentation failed. Try Rebuild.');
          }
        } catch {/* keep polling */}
      }, 3000);
    } catch (e) {
      setSegLoading(false);
      setSegError(e?.response?.data?.error || e?.message || 'Could not start segmentation.');
    }
  })();

  return () => timer && clearInterval(timer);
}, [activeTab, fileId, segData, segLoading, segProgId]);


useEffect(() => {
  if (activeTab !== 'doc') return;
  if (!fileId) return;
  if (docData || docLoading || docProgId) return;

  let timer = null;
  (async () => {
    try {
      setDocError('');
      setDocLoading(true);
      const { progress_id } = await docAnalysisApi.start(fileId, 'admin', false);
      setDocProgId(progress_id); setDocPct(0);

      timer = setInterval(async () => {
        try {
          const pr = await docAnalysisApi.progress(progress_id);
          const { percentage=0, status } = pr || {};
          setDocPct(percentage ?? 0);
          if (status === 'completed' || (percentage ?? 0) >= 100) {
            clearInterval(timer);
            const res = await docAnalysisApi.results(fileId, false);
            setDocData(res);
            setDocLoading(false);
            setDocProgId(null);
          } else if (status === 'failed') {
            clearInterval(timer);
            setDocLoading(false);
            setDocError('Document analysis failed. Try Rebuild.');
          }
        } catch {/* keep polling */}
      }, 3000);
    } catch (e) {
      setDocLoading(false);
      setDocError(e?.response?.data?.error || e?.message || 'Could not start document analysis.');
    }
  })();

  return () => timer && clearInterval(timer);
}, [activeTab, fileId, docData, docLoading, docProgId]);

  const fetchVaultFiles = async () => {
    try {
      const response = await axiosInstance.get('/upload/files');
      setVaultFiles(response.data.files || []);
    } catch {
      setError('Failed to fetch vault files.');
    }
  };

  const resetOutputStates = () => {
    setError('');
    setSummaryPages([]);
    setCurrentPageIndex(0);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError('');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axiosInstance.post('/upload/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const storedAs = response.data.name || response.data.stored_as;
      await fetchVaultFiles();
      setSelectedVaultFile(storedAs);
    } catch (err) {
      setError('File upload failed.');
    } finally {
      setUploading(false);
    }
  };

  const handleFileSubmit = async (e) => {
    e.preventDefault();
    resetOutputStates();
    setLoading(true);

    try {
      if (!selectedVaultFile) {
        setError('Please select or upload a file.');
        return;
      }

      const resp = await axiosInstance.post('/summarizer/summarize_file', {
        filename: selectedVaultFile,
        fromVault: true,
      });

      const { message, progress_id, file_id } = resp.data;

      if (message?.includes('Processing')) {
        setProgressId(progress_id);
        setFileId(file_id);
        setProgressPercentage(0);
        setShowProcessingModal(true);
        setActiveTab('pages'); // default to pages
      } else {
        // already summarized -> show directly
        setFileId(file_id);
        await fetchSummary(file_id);
      }
    } catch (err) {
      setError(err?.response?.data?.error || 'An error occurred while summarizing the file.');
    } finally {
      setLoading(false);
    }
  };

  const fetchSummary = async (fid) => {
    try {
      const response = await axiosInstance.get(`/summarizer/get_summary/${fid}`);
      const pages = response.data.pages || [];
      setSummaryPages(pages);
      setCurrentPageIndex(0);
    } catch (err) {
      // console.error('Failed to fetch summary', err);
    }
  };

  // Derived data
  const currentPage = useMemo(
    () => summaryPages?.[currentPageIndex] || null,
    [summaryPages, currentPageIndex]
  );

  // Simple derived topic list (placeholder: basic split by periods)
  const topics = useMemo(() => {
    if (!summaryPages?.length) return [];
    const words = summaryPages.map(p => p.summary || '').join(' ').split(/\s+/);
    // ultra-naive placeholder – replace with backend topics later
    return Array.from(new Set(words.filter(w => w.length > 6))).slice(0, 30);
  }, [summaryPages]);

   // chronologyService.js (you can inline this near axiosInstance imports)
  const chronoApi = {
    start: (fileId, userId, force=false) =>
      axiosInstance.post('/chronology/start', { file_id: fileId, user_id: userId, force })
        .then(r => r.data),
    progress: (progressId) =>
      axiosInstance.get(`/chronology/progress/${progressId}`).then(r=>r.data),
    results: (fileId) =>
      axiosInstance.get(`/chronology/results?file_id=${fileId}`).then(r=>r.data),
  };


  // sentimentService.js (or inline near axiosInstance)
  const sentimentApi = {
    start: (fileId, userId, force=false) =>
      axiosInstance.post('/sentiment/start', { file_id: fileId, user_id: userId, force }).then(r=>r.data),
    progress: (progressId) =>
      axiosInstance.get(`/sentiment/progress/${progressId}`).then(r=>r.data),
    results: (fileId) =>
      axiosInstance.get(`/sentiment/results?file_id=${fileId}`).then(r=>r.data),
  };

  // segmentsApi helper
  const segmentsApi = {
    start: (fileId, userId, force=false) =>
      axiosInstance.post('/segmenter/start', { file_id: fileId, user_id: userId, force }).then(r=>r.data),
    progress: (progressId) =>
      axiosInstance.get(`/segmenter/progress/${progressId}`).then(r=>r.data),
    results: (fileId) =>
      axiosInstance.get(`/segmenter/results?file_id=${fileId}`).then(r=>r.data),
};

  // docAnalysisApi helper
  const docAnalysisApi = {
    start: (fileId, userId, force=false) =>
      axiosInstance.post('/doc_analysis/start', { file_id: fileId, user_id: userId, force }).then(r=>r.data),
    progress: (progressId) =>
      axiosInstance.get(`/doc_analysis/progress/${progressId}`).then(r=>r.data),
    results: (fileId, withMap=false) =>
      axiosInstance.get(`/doc_analysis/results?file_id=${fileId}${withMap ? '&mind_map=true' : ''}`).then(r=>r.data),
    mindMap: (fileId) =>
      axiosInstance.post('/doc_analysis/mind_map', { file_id: fileId }).then(r=>r.data),
  };

  return (
    <div className="stage-wrap">
      <header className="stage-header">
        <h1 className="stage-title">🖊️ Summarizer</h1>
        <p className="stage-subtitle">
          Upload or pick a file from your Knowledge Vault and generate crisp, page-wise summaries.
        </p>
      </header>

      {/* Source selection */}
      {/* Source selection — COMPACT TOOLBAR CARD */}
      <div className="stage-grid">
        <div className="stage-card card-purple card-compact">
          <div className="card-top compact-top">
            <h3 className="card-title">
              <span aria-hidden>📁</span> Select Source
            </h3>
            {/* optional: quick help or future filters */}
            <div className="compact-actions">
              {/* placeholder for help/settings */}
            </div>
          </div>

          <form onSubmit={handleFileSubmit} className="tool-form compact-form">
            <div className="compact-row">
              {/* File picker (hidden input + small button) */}
              <input
                id="filePicker"
                type="file"
                onChange={handleFileUpload}
                disabled={uploading}
                style={{ display: 'none' }}
              />
              <label htmlFor="filePicker" className="btn-ghost compact-btn" title="Upload a file">
                ⬆️ Upload
              </label>

              {/* Divider dot */}
              <span className="dot-divider" aria-hidden>•</span>

              {/* Vault select (slim) */}
              <select
                value={selectedVaultFile}
                onChange={(e) => setSelectedVaultFile(e.target.value)}
                className="compact-select"
                aria-label="Select from Knowledge Vault"
              >
                <option value="">Vault: choose file…</option>
                {vaultFiles.map((vf, idx) => (
                  <option key={idx} value={vf.stored_name}>{vf.name}</option>
                ))}
              </select>

              {/* Clear selection (only when something is chosen) */}
              {selectedVaultFile && (
                <button
                  type="button"
                  className="btn-ghost compact-btn"
                  onClick={() => setSelectedVaultFile('')}
                  title="Clear selection"
                >
                  ✕
                </button>
              )}

              {/* Summarize (primary, still compact) */}
              <button type="submit" className="btn-primary compact-btn" disabled={loading || uploading}>
                {loading ? 'Summarizing…' : 'Summarize'}
              </button>
            </div>

            {/* Slim status line (only appears if needed) */}
            {(error || uploading || loading) && (
              <div className="compact-status">
                {error && <span className="error-text">{error}</span>}
                {(uploading || loading) && (
                  <span className="muted">{uploading ? 'Uploading…' : 'Working…'}</span>
                )}
              </div>
            )}
          </form>

          {/* Inline progress when modal hidden */}
          {progressId && !showProcessingModal && progressPercentage < 100 && (
            <div className="compact-progress">
              <InlineProgress percentage={progressPercentage} />
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div style={{marginTop:24}}>
        <div style={{
          display: 'flex',
          gap: 8,
          flexWrap: 'wrap',
          justifyContent: 'center'   // ✅ center horizontally
        }}>
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              style={{
                padding:'10px 14px',
                borderRadius:10,
                border:'1px solid rgba(0,0,0,0.12)',
                background: activeTab === t.key ? '#111' : '#fff',
                color: activeTab === t.key ? '#fff' : '#111',
                cursor:'pointer'
              }}
              disabled={t.key !== 'pages' && summaryPages.length === 0}
              title={summaryPages.length === 0 && t.key !== 'pages'
                ? 'Run summarization first' : ''}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      <div style={{marginTop:8}}>
        {/* PAGES (A4 viewer with nav) */}
        {activeTab === 'pages' && (
          <>
            {summaryPages.length > 0 && (
              <div style={{display:'flex', alignItems:'center', justifyContent:'center', gap:16, marginTop:8}}>
                <button
                  onClick={() => setCurrentPageIndex(i => Math.max(0, i - 1))}
                  disabled={currentPageIndex === 0}
                  className="btn-secondary"
                >
                  ← Prev
                </button>
                <div style={{fontSize:14, opacity:.75}}>
                  Page {currentPageIndex + 1} / {summaryPages.length}
                </div>
                <button
                  onClick={() => setCurrentPageIndex(i => Math.min(summaryPages.length - 1, i + 1))}
                  disabled={currentPageIndex >= summaryPages.length - 1}
                  className="btn-secondary"
                >
                  Next →
                </button>
              </div>
            )}

            {currentPage ? (
              <A4Page title={`Page ${currentPage.page_number}`} content={currentPage.summary} />
            ) : (
              <div style={{marginTop:24, textAlign:'center', opacity:.7}}>
                {summaryPages.length === 0 ? 'No pages yet. Summarize a file to view pages.' : 'Loading page…'}
              </div>
            )}
          </>
        )}

        {/* TOPICS */}
        {activeTab === 'topics' && (
          <div style={{margin:'24px auto', width:'min(900px, 92vw)'}}>
            <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', gap:12}}>
              <h3 style={{margin:0}}>Topics</h3>
              {/* Optional: actions */}
              <div style={{display:'flex', gap:8}}>
                {topicsData && !topicsProgressId && (
                  <button
                    className="btn-secondary"
                    onClick={async () => {
                      // refresh without force
                      setTopicsData(null);
                      setTopicsLoading(false);
                      setTopicsProgressId(null);
                      setTopicsPct(0);
                      setTopicsError('');
                      // trigger effect by toggling tab
                      setActiveTab('pages');
                      setTimeout(() => setActiveTab('topics'), 0);
                    }}
                  >
                    Refresh
                  </button>
                )}
                {/* {!topicsProgressId && (
                  <button
                    className="btn-secondary"
                    onClick={async () => {
                      // force rebuild
                      try {
                        setTopicsData(null);
                        setTopicsError('');
                        setTopicsLoading(true);
                        const start = await axiosInstance.post('/modeller/topics/start', {
                          file_id: fileId,
                          user_id: 'admin',
                          force: true
                        });
                        const { progress_id } = start.data || {};
                        setTopicsProgressId(progress_id);
                        setTopicsPct(0);
                      } catch (e) {
                        setTopicsLoading(false);
                        setTopicsError(e?.response?.data?.error || 'Could not force rebuild.');
                      }
                    }}
                  >
                    Rebuild
                  </button>
                )} */}
              </div>
            </div>

            {topicsError && <p className="error-text" style={{marginTop:8}}>{topicsError}</p>}

            {/* Progress while building */}
            {topicsProgressId && (
              <div style={{marginTop:12}}>
                <InlineProgress percentage={topicsPct} />
              </div>
            )}

            {/* Results */}
            {topicsData && !topicsProgressId && (
              <>
                <div style={{margin:'10px 0 14px', fontSize:12, opacity:.7}}>
                  Found {topicsData.topics?.length || 0} unique topics across {topicsData.per_page?.length || 0} pages.
                </div>

                {/* Top topics as chips */}
                <div style={{display:'flex', flexWrap:'wrap', gap:8}}>
                  {(topicsData.topics || []).slice(0, 60).map((t, i) => (
                    <span
                      key={i}
                      style={{
                        fontSize:12, padding:'6px 10px', borderRadius:999,
                        background:'#eef2ff', color:'#3730a3',
                        border:'1px solid rgba(0,0,0,0.06)'
                      }}
                      title={t.pages && t.pages.length ? `Pages: ${t.pages.join(', ')}` : '—'}
                    >
                      {t.topic} <span style={{opacity:.6}}>×{t.count}</span>
                    </span>
                  ))}
                </div>

                {/* Per-page table */}
                <div style={{marginTop:18}}>
                  <h4 style={{marginBottom:8}}>Per Page</h4>
                  <div style={{background:'#fff', borderRadius:10, boxShadow:'0 6px 16px rgba(0,0,0,.06)', padding:12}}>
                    {(topicsData.per_page || []).map((p) => (
                      <div
                        key={p.page}
                        style={{
                          display:'flex', gap:8, alignItems:'baseline',
                          padding:'8px 0', borderBottom:'1px solid #f1f5f9'
                        }}
                      >
                        <strong style={{width:90}}>Page {p.page}</strong>
                        <div style={{display:'flex', flexWrap:'wrap', gap:6}}>
                          {(p.topics || []).map((t,i) => (
                            <span key={i} style={{fontSize:12, padding:'4px 8px', borderRadius:999, background:'#f3f4f6'}}>
                              {t}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* Idle */}
            {!topicsData && !topicsProgressId && !topicsLoading && !topicsError && (
              <p className="muted" style={{marginTop:12}}>Click “Topics” to start extraction for this file.</p>
            )}
          </div>
        )}

        {/* COMPARE PAGES (pick 2, show side-by-side) */}
        {activeTab === 'compare' && (
          <ComparePages pages={summaryPages} />
        )}

        {/* CHRONOLOGY placeholder */}
        {activeTab === 'chronology' && (
          <div style={{margin:'24px auto', width:'min(1000px, 96vw)'}}>
            <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', gap:12}}>
              <h3 style={{margin:0}}>Chronology</h3>
              <div style={{display:'flex', gap:8}}>
                {/* View toggle */}
                <div style={{display:'inline-flex', border:'1px solid #e5e7eb', borderRadius:999, overflow:'hidden'}}>
                  <button
                    className="btn-secondary"
                    style={{borderRadius:0, padding:'6px 10px', background: chronoView==='merged' ? '#111' : '#fff', color: chronoView==='merged' ? '#fff' : '#111'}}
                    onClick={() => setChronoView('merged')}
                    disabled={!chronoData}
                  >Chronology-wise</button>
                  <button
                    className="btn-secondary"
                    style={{borderRadius:0, padding:'6px 10px', background: chronoView==='per_page' ? '#111' : '#fff', color: chronoView==='per_page' ? '#fff' : '#111'}}
                    onClick={() => setChronoView('per_page')}
                    disabled={!chronoData}
                  >Page-wise</button>
                </div>

                {/* Rebuild */}
                {!chronoProgressId && (
                  <button
                    className="btn-secondary"
                    onClick={async () => {
                      try {
                        setChronoError('');
                        setChronoLoading(true);
                        setChronoData(null);
                        const { progress_id } = await chronoApi.start(fileId, 'admin', true);
                        setChronoProgressId(progress_id);
                        setChronoPct(0);
                      } catch (e) {
                        setChronoLoading(false);
                        setChronoError(e?.response?.data?.error || 'Could not rebuild chronology.');
                      }
                    }}
                  >
                    Rebuild
                  </button>
                )}
              </div>
            </div>

            {chronoError && <p className="error-text" style={{marginTop:8}}>{chronoError}</p>}

            {chronoProgressId && (
              <div style={{marginTop:12}}>
                <InlineProgress percentage={chronoPct} />
              </div>
            )}

            {chronoData && !chronoProgressId && (
              <>
                {chronoView === 'merged' ? (
                  <div style={{marginTop:16}}>
                    <div style={{fontSize:12, opacity:.7, marginBottom:8}}>
                      {chronoData.merged.length} events (merged across pages)
                    </div>
                    <div style={{display:'grid', gap:10}}>
                      {chronoData.merged.map((e, i) => (
                        <div key={i} style={{background:'#fff', borderRadius:10, boxShadow:'0 8px 18px rgba(0,0,0,.06)', padding:'12px 14px'}}>
                          <div style={{display:'flex', justifyContent:'space-between', gap:12, flexWrap:'wrap'}}>
                            <strong>{e.date || '—'}</strong>
                            <span style={{fontSize:12, opacity:.7}}>Pages: {e.pages?.join(', ') || '—'}</span>
                          </div>
                          <div style={{marginTop:4, fontWeight:600}}>{e.title}</div>
                          <div style={{marginTop:2, opacity:.85}}>{e.desc}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div style={{marginTop:16}}>
                    <div style={{fontSize:12, opacity:.7, marginBottom:8}}>
                      Page-wise events
                    </div>
                    <div style={{display:'grid', gap:12}}>
                      {chronoData.per_page.map((p) => (
                        <div key={p.page} style={{background:'#fff', borderRadius:10, boxShadow:'0 8px 18px rgba(0,0,0,.06)', padding:'12px 14px'}}>
                          <strong>Page {p.page}</strong>
                          <ul style={{margin:'6px 0 0 18px'}}>
                            {(p.events || []).map((e, idx) => (
                              <li key={idx}>
                                <span style={{opacity:.7}}>{e.date || '—'}</span> — <b>{e.title}</b>: {e.desc}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {!chronoData && !chronoProgressId && !chronoLoading && !chronoError && (
              <p className="muted" style={{marginTop:12}}>Click “Chronology” to build the timeline.</p>
            )}
          </div>
        )}

        {/* SENTIMENT ANALYSER */}
        {activeTab === 'sentiment' && (
          <div style={{margin:'24px auto', width:'min(1000px, 96vw)'}}>
            <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', gap:12}}>
              <h3 style={{margin:0}}>Sentiment Analyser</h3>

              <div style={{display:'flex', gap:8, alignItems:'center'}}>
                {/* Refresh (re-fetch results without recomputing) */}
                {sentData && !sentProgId && (
                  <button
                    className="btn-secondary"
                    onClick={async () => {
                      // UI reset + re-fetch
                      setSentError(''); setSentLoading(true);
                      try {
                        const res = await sentimentApi.results(fileId);
                        setSentData(res);
                      } catch (e) {
                        setSentError(e?.response?.data?.error || 'Refresh failed.');
                      } finally {
                        setSentLoading(false);
                      }
                    }}
                  >
                    Refresh
                  </button>
                )}

                {/* Rebuild (force recompute via Celery) */}
                {!sentProgId && (
                  <button
                    className="btn-secondary"
                    onClick={async () => {
                      try {
                        setSentError('');
                        setSentLoading(true);
                        setSentData(null);
                        const { progress_id } = await sentimentApi.start(fileId, 'admin', true);
                        setSentProgId(progress_id);
                        setSentPct(0);
                      } catch (e) {
                        setSentLoading(false);
                        setSentError(e?.response?.data?.error || 'Could not rebuild sentiment.');
                      }
                    }}
                  >
                    Rebuild
                  </button>
                )}
              </div>
            </div>

            {sentError && <p className="error-text" style={{marginTop:8}}>{sentError}</p>}

            {sentProgId && (
              <div style={{marginTop:12}}>
                <InlineProgress percentage={sentPct} />
              </div>
            )}

            {sentData && !sentProgId && (
              <div style={{marginTop:16, display:'grid', gap:16}}>
                {/* Doc-wise summary */}
                <div style={{background:'#fff', borderRadius:12, boxShadow:'0 8px 18px rgba(0,0,0,.06)', padding:'16px 18px'}}>
                  <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap:'wrap', gap:10}}>
                    <div>
                      <div style={{fontSize:12, opacity:.7}}>Document Sentiment</div>
                      <div style={{fontSize:20, fontWeight:700}}>
                        {sentData.doc?.dominant_label?.replace('_',' ') || 'neutral'}
                      </div>
                    </div>
                    <div>
                      <div style={{fontSize:12, opacity:.7, textAlign:'right'}}>Average Score</div>
                      <div style={{fontSize:20, fontWeight:700, textAlign:'right'}}>
                        {(sentData.doc?.avg_score ?? 0).toFixed(3)}
                      </div>
                    </div>
                  </div>

                  {/* Tiny histogram */}
                  <div style={{display:'flex', gap:8, marginTop:12, alignItems:'flex-end'}}>
                    {['very_negative','negative','neutral','positive','very_positive'].map(k => {
                      const count = sentData.doc?.label_hist?.[k] ?? 0;
                      const max = Math.max(...Object.values(sentData.doc?.label_hist || {neutral:1}));
                      const h = max ? (12 + (count / max) * 48) : 12;
                      return (
                        <div key={k} style={{textAlign:'center'}}>
                          <div style={{width:26, height:h, background:'#111', borderRadius:6, margin:'0 auto'}}/>
                          <div style={{fontSize:10, opacity:.7, marginTop:6, width:56}}>
                            {k.replace('_',' ')} ({count})
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Per-page sentiments */}
                <div style={{display:'grid', gap:12}}>
                  {(sentData.per_page || []).map((pp) => (
                    <div key={pp.page} style={{background:'#fff', borderRadius:12, boxShadow:'0 8px 18px rgba(0,0,0,.06)', padding:'12px 14px'}}>
                      <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', gap:12, flexWrap:'wrap'}}>
                        <strong>Page {pp.page}</strong>
                        <div style={{display:'flex', gap:10, alignItems:'center'}}>
                          <span style={{fontSize:12, opacity:.7}}>Label</span>
                          <span style={{fontWeight:600}}>{pp.sentiment?.label?.replace('_',' ') || 'neutral'}</span>
                          <span style={{fontSize:12, opacity:.7, marginLeft:12}}>Score</span>
                          <span style={{fontWeight:600}}>{Number(pp.sentiment?.score ?? 0).toFixed(3)}</span>
                          <button
                            className="btn-secondary"
                            onClick={() => {
                              // jump to that page in Pages tab
                              setActiveTab('pages');
                              const idx = Math.max(0, Math.min(summaryPages.length - 1, (pp.page || 1) - 1));
                              setCurrentPageIndex(idx);
                            }}
                          >
                            Open Page
                          </button>
                        </div>
                      </div>
                      {pp.sentiment?.rationale && (
                        <div style={{marginTop:6, opacity:.85}}>
                          {pp.sentiment.rationale}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!sentData && !sentProgId && !sentLoading && !sentError && (
              <p className="muted" style={{marginTop:12}}>Click “Sentiment Analyser” to start.</p>
            )}
          </div>
        )}

        {/* SEGMENTS placeholder */}
        {activeTab === 'segments' && (
          <div style={{margin:'24px auto', width:'min(1000px, 96vw)'}}>
            <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', gap:12}}>
              <h3 style={{margin:0}}>Segments</h3>

              <div style={{display:'flex', gap:8, alignItems:'center'}}>
                {/* View toggle */}
                <div style={{display:'inline-flex', border:'1px solid #e5e7eb', borderRadius:999, overflow:'hidden'}}>
                  <button
                    className="btn-secondary"
                    style={{borderRadius:0, padding:'6px 10px', background: segView==='outline' ? '#111' : '#fff', color: segView==='outline' ? '#fff' : '#111'}}
                    onClick={() => setSegView('outline')}
                    disabled={!segData}
                  >Outline</button>
                  <button
                    className="btn-secondary"
                    style={{borderRadius:0, padding:'6px 10px', background: segView==='per_page' ? '#111' : '#fff', color: segView==='per_page' ? '#fff' : '#111'}}
                    onClick={() => setSegView('per_page')}
                    disabled={!segData}
                  >Per‑page</button>
                </div>

                {/* Refresh (quick re-fetch) */}
                {segData && !segProgId && (
                  <button
                    className="btn-secondary"
                    onClick={async () => {
                      setSegError(''); setSegLoading(true);
                      try {
                        const res = await segmentsApi.results(fileId);
                        setSegData(res);
                      } catch (e) {
                        setSegError(e?.response?.data?.error || 'Refresh failed.');
                      } finally {
                        setSegLoading(false);
                      }
                    }}
                  >
                    Refresh
                  </button>
                )}

                {/* Rebuild (force recompute) */}
                {!segProgId && (
                  <button
                    className="btn-secondary"
                    onClick={async () => {
                      try {
                        setSegError('');
                        setSegLoading(true);
                        setSegData(null);
                        const { progress_id } = await segmentsApi.start(fileId, 'admin', true);
                        setSegProgId(progress_id);
                        setSegPct(0);
                      } catch (e) {
                        setSegLoading(false);
                        setSegError(e?.response?.data?.error || 'Could not rebuild segments.');
                      }
                    }}
                  >
                    Rebuild
                  </button>
                )}
              </div>
            </div>

            {segError && <p className="error-text" style={{marginTop:8}}>{segError}</p>}

            {segProgId && (
              <div style={{marginTop:12}}>
                <InlineProgress percentage={segPct} />
              </div>
            )}

            {segData && !segProgId && (
              <>
                {segView === 'outline' ? (
                  <div style={{marginTop:16, display:'grid', gap:12}}>
                    <div style={{fontSize:12, opacity:.7}}>Document outline (merged by heading/level)</div>
                    {segData.outline?.map((seg, i) => (
                      <div key={i} style={{background:'#fff', borderRadius:12, boxShadow:'0 8px 18px rgba(0,0,0,.06)', padding:'12px 14px'}}>
                        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', gap:12, flexWrap:'wrap'}}>
                          <div style={{fontWeight:700}}>
                            {Array(seg.level || 2).fill('•').join(' ')} {seg.heading}
                          </div>
                          <div style={{fontSize:12, opacity:.7}}>Pages: {seg.pages?.join(', ') || '—'}</div>
                        </div>
                        {seg.summary && <div style={{marginTop:6, opacity:.9}}>{seg.summary}</div>}
                        {Array.isArray(seg.tags) && seg.tags.length > 0 && (
                          <div style={{display:'flex', gap:6, flexWrap:'wrap', marginTop:8}}>
                            {seg.tags.map((t, idx) => (
                              <span key={idx} style={{fontSize:12, padding:'4px 8px', background:'#f3f4f6', borderRadius:999}}>{t}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{marginTop:16, display:'grid', gap:12}}>
                    <div style={{fontSize:12, opacity:.7}}>Per‑page segments</div>
                    {segData.per_page?.map((pp) => (
                      <div key={pp.page} style={{background:'#fff', borderRadius:12, boxShadow:'0 8px 18px rgba(0,0,0,.06)', padding:'12px 14px'}}>
                        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', gap:12, flexWrap:'wrap'}}>
                          <strong>Page {pp.page}</strong>
                          <button
                            className="btn-secondary"
                            onClick={() => {
                              setActiveTab('pages');
                              const idx = Math.max(0, Math.min(summaryPages.length - 1, (pp.page || 1) - 1));
                              setCurrentPageIndex(idx);
                            }}
                          >
                            Open Page
                          </button>
                        </div>

                        {(pp.segments || []).length === 0 ? (
                          <div style={{marginTop:6, opacity:.7}}>No segments detected.</div>
                        ) : (
                          <div style={{display:'grid', gap:8, marginTop:10}}>
                            {pp.segments.map((seg, i) => (
                              <div key={i} style={{border:'1px solid #e5e7eb', borderRadius:10, padding:'10px 12px'}}>
                                <div style={{fontWeight:600}}>
                                  {Array(seg.level || 2).fill('•').join(' ')} {seg.heading}
                                </div>
                                {seg.summary && <div style={{marginTop:4, opacity:.9}}>{seg.summary}</div>}
                                {Array.isArray(seg.tags) && seg.tags.length > 0 && (
                                  <div style={{display:'flex', gap:6, flexWrap:'wrap', marginTop:6}}>
                                    {seg.tags.map((t, idx) => (
                                      <span key={idx} style={{fontSize:12, padding:'3px 8px', background:'#f3f4f6', borderRadius:999}}>{t}</span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}

            {!segData && !segProgId && !segLoading && !segError && (
              <p className="muted" style={{marginTop:12}}>Click “Segments” to start segmentation.</p>
            )}
          </div>
        )}

        {/* DOCUMENT ANALYSIS placeholder */}
        {activeTab === 'doc' && (
          <div style={{margin:'24px auto', width:'min(1000px, 96vw)'}}>
            <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', gap:12}}>
              <h3 style={{margin:0}}>Document Analysis</h3>

              <div style={{display:'flex', gap:8, alignItems:'center'}}>
                {/* Toggle Mind Map */}
                <button
                  className="btn-secondary"
                  onClick={async () => {
                    try {
                      if (!docShowMap) {
                        // fetch mind map only when needed
                        setDocError('');
                        setDocLoading(true);
                        const map = await docAnalysisApi.mindMap(fileId);
                        setDocData(prev => ({...(prev||{}), mind_map: map}));
                      }
                      setDocShowMap(v => !v);
                    } catch (e) {
                      setDocError(e?.response?.data?.error || 'Mind map generation failed.');
                    } finally {
                      setDocLoading(false);
                    }
                  }}
                  disabled={!docData || !!docProgId}
                >
                  {docShowMap ? 'Hide Mind Map' : 'Show Mind Map'}
                </button>

                {/* Refresh */}
                {docData && !docProgId && (
                  <button
                    className="btn-secondary"
                    onClick={async () => {
                      try {
                        setDocError(''); setDocLoading(true);
                        const res = await docAnalysisApi.results(fileId, !!docShowMap);
                        setDocData(res);
                      } catch (e) {
                        setDocError(e?.response?.data?.error || 'Refresh failed.');
                      } finally {
                        setDocLoading(false);
                      }
                    }}
                  >
                    Refresh
                  </button>
                )}

                {/* Rebuild */}
                {!docProgId && (
                  <button
                    className="btn-secondary"
                    onClick={async () => {
                      try {
                        setDocError('');
                        setDocLoading(true);
                        setDocData(null);
                        const { progress_id } = await docAnalysisApi.start(fileId, 'admin', true);
                        setDocProgId(progress_id);
                        setDocPct(0);
                      } catch (e) {
                        setDocLoading(false);
                        setDocError(e?.response?.data?.error || 'Could not rebuild document analysis.');
                      }
                    }}
                  >
                    Rebuild
                  </button>
                )}
              </div>
            </div>

            {docError && <p className="error-text" style={{marginTop:8}}>{docError}</p>}

            {docProgId && (
              <div style={{marginTop:12}}>
                <InlineProgress percentage={docPct} />
              </div>
            )}

            {docData && !docProgId && (
              <div style={{marginTop:16, display:'grid', gap:16}}>
                {/* Stats cards */}
                <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fit,minmax(180px,1fr))', gap:12}}>
                  {[
                    {label:'Pages', value: docData.doc?.totals?.pages ?? summaryPages.length},
                    {label:'Words', value: docData.doc?.totals?.words ?? 0},
                    {label:'Characters', value: docData.doc?.totals?.chars ?? 0},
                    {label:'~Tokens', value: docData.doc?.totals?.approx_tokens ?? 0},
                  ].map((it, i) => (
                    <div key={i} style={{background:'#fff', borderRadius:12, padding:'14px 16px', boxShadow:'0 8px 18px rgba(0,0,0,.06)'}}>
                      <div style={{fontSize:12, opacity:.7}}>{it.label}</div>
                      <div style={{fontSize:22, fontWeight:700}}>{it.value}</div>
                    </div>
                  ))}
                </div>

                {/* Entities by type with tiny bars */}
                <div style={{background:'#fff', borderRadius:12, padding:'16px 18px', boxShadow:'0 8px 18px rgba(0,0,0,.06)'}}>
                  <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8}}>
                    <strong>Entities</strong>
                    <span className="muted" style={{fontSize:12}}>Grouped by type</span>
                  </div>
                  <div style={{display:'grid', gridTemplateColumns:'repeat(auto-fit,minmax(240px,1fr))', gap:12}}>
                    {Object.entries(docData.doc?.entities_by_type || {}).map(([ty, items]) => {
                      const maxCount = Math.max(1, ...items.map(x => x.count || 0));
                      return (
                        <div key={ty} style={{border:'1px solid #e5e7eb', borderRadius:10, padding:'10px 12px'}}>
                          <div style={{fontWeight:700, marginBottom:6}}>{ty}</div>
                          <div style={{display:'grid', gap:6}}>
                            {items.slice(0,6).map((e, idx) => (
                              <div key={idx} style={{display:'grid', gridTemplateColumns:'1fr 60px', gap:8, alignItems:'center'}}>
                                <div style={{overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}} title={e.text}>{e.text}</div>
                                <div style={{display:'flex', alignItems:'center', gap:6}}>
                                  <div style={{height:8, width:`${Math.max(10, (e.count/maxCount)*60)}px`, background:'#111', borderRadius:6}}/>
                                  <span style={{fontSize:12, opacity:.7}}>{e.count}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Top tags (chips) */}
                <div style={{background:'#fff', borderRadius:12, padding:'16px 18px', boxShadow:'0 8px 18px rgba(0,0,0,.06)'}}>
                  <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8}}>
                    <strong>Top Tags</strong>
                    <span className="muted" style={{fontSize:12}}>{(docData.doc?.top_tags || []).length} tags</span>
                  </div>
                  <div style={{display:'flex', gap:8, flexWrap:'wrap'}}>
                    {(docData.doc?.top_tags || []).map((t, i) => (
                      <span key={i} title={`Pages: ${t.pages?.join(', ')||'-'}`}
                        style={{fontSize:12, padding:'6px 10px', background:'#f3f4f6', borderRadius:999, border:'1px solid #e5e7eb'}}>
                        {t.tag} <span style={{opacity:.6}}>×{t.count}</span>
                      </span>
                    ))}
                  </div>
                </div>

                {/* Per-page quick view */}
                <div style={{background:'#fff', borderRadius:12, padding:'16px 18px', boxShadow:'0 8px 18px rgba(0,0,0,.06)'}}>
                  <strong>Per‑page Entities & Tags</strong>
                  <div style={{display:'grid', gap:10, marginTop:10}}>
                    {(docData.per_page || []).map(pp => (
                      <div key={pp.page} style={{border:'1px solid #e5e7eb', borderRadius:10, padding:'10px 12px'}}>
                        <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', gap:12}}>
                          <div><b>Page {pp.page}</b></div>
                          <button
                            className="btn-secondary"
                            onClick={() => {
                              setActiveTab('pages');
                              const idx = Math.max(0, Math.min(summaryPages.length - 1, (pp.page || 1) - 1));
                              setCurrentPageIndex(idx);
                            }}
                          >
                            Open Page
                          </button>
                        </div>
                        {/* tags */}
                        <div style={{display:'flex', gap:6, flexWrap:'wrap', marginTop:8}}>
                          {(pp.analysis?.tags || []).slice(0,10).map((tg, i) => (
                            <span key={i} style={{fontSize:12, padding:'4px 8px', background:'#f3f4f6', borderRadius:999}}>{tg}</span>
                          ))}
                        </div>
                        {/* entities (first few) */}
                        <div style={{display:'grid', gap:6, marginTop:8}}>
                          {(pp.analysis?.entities || []).slice(0,6).map((e, i) => (
                            <div key={i} style={{display:'flex', justifyContent:'space-between', gap:8}}>
                              <span style={{overflow:'hidden', textOverflow:'ellipsis'}} title={e.text}>{e.text}</span>
                              <span style={{fontSize:12, opacity:.7}}>{e.type}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Mind Map (simple SVG matrix lines) */}
                {docShowMap && docData.mind_map && (
                  <div style={{background:'#fff', borderRadius:12, padding:'16px 18px', boxShadow:'0 8px 18px rgba(0,0,0,.06)'}}>
                    <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                      <strong>Mind Map</strong>
                      <span className="muted" style={{fontSize:12}}>
                        {docData.mind_map.nodes?.length || 0} nodes • {docData.mind_map.edges?.length || 0} edges
                      </span>
                    </div>
                    {/* Simple non-interactive layout: nodes in two columns with edges listed; 
                        (you can swap to a lib later) */}
                    <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:12, marginTop:10}}>
                      <div>
                        <div style={{fontWeight:700, marginBottom:6}}>Nodes</div>
                        <ul style={{margin:0, paddingLeft:18}}>
                          {(docData.mind_map.nodes || []).map((n, i) => <li key={i}>{n.id}</li>)}
                        </ul>
                      </div>
                      <div>
                        <div style={{fontWeight:700, marginBottom:6}}>Edges</div>
                        <ul style={{margin:0, paddingLeft:18}}>
                          {(docData.mind_map.edges || []).map((e, i) => (
                            <li key={i}><b>{e.source}</b> → <b>{e.target}</b> <span style={{opacity:.7}}>({e.label || 'rel'})</span></li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {!docData && !docProgId && !docLoading && !docError && (
              <p className="muted" style={{marginTop:12}}>Click “Document Analysis” to start.</p>
            )}
          </div>
        )}
      </div>

      {/* Processing Modal */}
      {showProcessingModal && (
        <div className="modal-overlay">
          <div className="modal">
            <h2>Summarization in Progress</h2>
            <p className="muted">{progressPercentage}% completed</p>
            <div className="modal-actions">
              {/* Stay Here hides modal; inline bar continues */}
              <button className="btn-secondary" onClick={() => setShowProcessingModal(false)}>
                Stay Here
              </button>
              <button className="btn-primary" onClick={() => navigate('/dashboard')}>
                Go to Dashboard
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/** Compare Pages sub-component */
function ComparePages({ pages }) {
  const [a, setA] = useState(0);
  const [b, setB] = useState(1);

  if (!pages?.length) {
    return <div style={{marginTop:24, textAlign:'center', opacity:.7}}>No pages yet.</div>;
  }

  const clampIdx = (i) => Math.min(Math.max(i, 0), pages.length - 1);

  return (
    <div style={{margin:'24px auto', width:'min(1200px, 98vw)'}}>
      <div style={{display:'flex', gap:12, alignItems:'center', flexWrap:'wrap'}}>
        <label>Left:
          <select value={a} onChange={e => setA(clampIdx(Number(e.target.value)))} style={{marginLeft:8}}>
            {pages.map((p, idx) => <option key={idx} value={idx}>Page {p.page_number}</option>)}
          </select>
        </label>
        <label>Right:
          <select value={b} onChange={e => setB(clampIdx(Number(e.target.value)))} style={{marginLeft:8}}>
            {pages.map((p, idx) => <option key={idx} value={idx}>Page {p.page_number}</option>)}
          </select>
        </label>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:16, marginTop:16}}>
        <div style={{background:'#fff', borderRadius:12, boxShadow:'0 12px 30px rgba(0,0,0,0.12)', padding:'24px 28px'}}>
          <h4 style={{marginTop:0}}>Page {pages[a]?.page_number}</h4>
          <div style={{whiteSpace:'pre-wrap'}}>{pages[a]?.summary || '—'}</div>
        </div>
        <div style={{background:'#fff', borderRadius:12, boxShadow:'0 12px 30px rgba(0,0,0,0.12)', padding:'24px 28px'}}>
          <h4 style={{marginTop:0}}>Page {pages[b]?.page_number}</h4>
          <div style={{whiteSpace:'pre-wrap'}}>{pages[b]?.summary || '—'}</div>
        </div>
      </div>
    </div>
  );
}