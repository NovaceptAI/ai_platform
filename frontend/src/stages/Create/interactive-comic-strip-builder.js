import React, { useEffect, useState } from 'react';
import './interactive-comic-strip-builder.css';
import config from '../../config';

export default function Interactive_comic_strip_builderTool({ fileId = null }) {
  const [progressId, setProgressId] = useState(null);
  const [progress, setProgress] = useState({ percentage: 0, status: 'idle' });
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const token = localStorage.getItem('token');
  const auth = { 'Authorization': `Bearer ${token}`, 'Content-Type':'application/json' };

  const start = async () => {
    setError('');
    setResult(null);
    try {
      const resp = await fetch(`${config.API_BASE_URL}/interactive-comic-strip-builder/start`, {
        method: 'POST',
        headers: auth,
        body: JSON.stringify({ file_id: fileId, params: {} })
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || 'Failed to start');
      setProgressId(data.progress_id);
      setProgress({ percentage: 0, status: 'queued' });
    } catch (e) { setError(e.message); }
  };

  useEffect(() => {
    if (!progressId) return;
    let timer = setInterval(async () => {
      const r = await fetch(`${config.API_BASE_URL}/interactive-comic-strip-builder/progress/${progressId}`, { headers: auth });
      const d = await r.json();
      if (!r.ok) { setError(d.error || 'Progress error'); clearInterval(timer); return; }
      setProgress({ percentage: d.percentage || 0, status: d.status });
      if (d.status === 'done') {
        clearInterval(timer);
        const rr = await fetch(`${config.API_BASE_URL}/interactive-comic-strip-builder/results/${progressId}`, { headers: auth });
        const rd = await rr.json();
        if (rr.ok) setResult(rd); else setError(rd.error || 'Results error');
      }
      if (d.status === 'failed') clearInterval(timer);
    }, 1200);
    return () => clearInterval(timer);
  }, [progressId]);

  return (
    <div className="interactive-comic-strip-builder-tool">
      <div className="tool-head">
        <h3>Interactive Comic Strip Builder</h3>
        <button className="btn" onClick={start}>Run</button>
      </div>

      {!!error && <div className="tool-error">{error}</div>}

      <div className="tool-progress">
        <div className="bar"><div className="fill" style={{width: `${progress.percentage||0}%`}}/></div>
        <div className="meta">{progress.status} • {progress.percentage||0}%</div>
      </div>

      {result && (
        <div className="tool-result">
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}