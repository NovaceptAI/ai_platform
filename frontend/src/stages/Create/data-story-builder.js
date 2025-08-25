import React, { useEffect, useRef, useState } from "react";
import config from "../../config";
import "./data-story-builder.css";

export default function DataStoryBuilder() {
  const [csvText, setCsvText] = useState("month,attendance\nJan,80\nFeb,82\nMar,90\nApr,85");
  const [fileId, setFileId] = useState(""); // integrate with your Vault picker later

  const [progressId, setProgressId] = useState(null);
  const [pct, setPct] = useState(0);
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");
  const pollRef = useRef(null);

  const token = localStorage.getItem("token");
  const headers = { "Authorization": `Bearer ${token || ""}`, "Content-Type": "application/json" };
  const BASE = `${config.API_BASE_URL}/data-story-builder`;

  const start = async () => {
    setErr(""); setResult(null); setPct(0); setStatus("queued");
    try {
      const body = { file_id: fileId || undefined, params: { csv_text: fileId ? undefined : csvText } };
      const r = await fetch(`${BASE}/start`, { method: "POST", headers, body: JSON.stringify(body) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || "Failed to start");
      setProgressId(d.progress_id);
    } catch (e) {
      setErr(e.message || String(e)); setStatus("failed");
    }
  };

  useEffect(() => {
    if (!progressId) return;
    pollRef.current && clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const rp = await fetch(`${BASE}/progress/${progressId}`, { headers });
        const pd = await rp.json();
        if (!rp.ok) throw new Error(pd.error || "Progress error");
        setPct(pd.percentage || 0); setStatus(pd.status);
        if (pd.status === "done") {
          clearInterval(pollRef.current);
          const rr = await fetch(`${BASE}/results/${progressId}`, { headers });
          const rd = await rr.json();
          if (!rr.ok) throw new Error(rd.error || "Results error");
          setResult(rd);
        }
        if (pd.status === "failed") clearInterval(pollRef.current);
      } catch (e) {
        setErr(e.message || String(e)); clearInterval(pollRef.current);
      }
    }, 1100);
    return () => pollRef.current && clearInterval(pollRef.current);
  }, [progressId]);

  return (
    <div className="tool-card">
      <div className="tool-head">
        <h3>Data Story Builder</h3>
        <button className="btn" onClick={start}>Run</button>
      </div>

      <div className="tool-inputs">
        <label htmlFor="dsb-file">File ID (optional)</label>
        <input id="dsb-file" value={fileId} onChange={(e)=>setFileId(e.target.value)} placeholder="Paste file_id from Vault (optional)" />
        {!fileId && (
          <>
            <label htmlFor="dsb-csv">CSV Text</label>
            <textarea id="dsb-csv" rows={6} value={csvText} onChange={(e)=>setCsvText(e.target.value)} />
          </>
        )}
      </div>

      {err && <div className="tool-err">{err}</div>}

      <div className="tool-progress">
        <div className="bar"><div className="fill" style={{ width: `${pct}%` }}/></div>
        <div className="meta">{status} • {pct}%</div>
      </div>

      {result && (
        <div className="tool-result">
          <h4>Insights</h4>
          <ul>{(result.insights || []).map((t,i)=><li key={i}>{t}</li>)}</ul>
          <h4>Charts</h4>
          <pre>{JSON.stringify(result.charts || [], null, 2)}</pre>
        </div>
      )}
    </div>
  );
}