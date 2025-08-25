import React, { useEffect, useRef, useState } from "react";
import config from "../../config";
import "./interactive-comic-strip-builder.css";

export default function InteractiveComicStripBuilder() {
  const [template, setTemplate] = useState("3-panel");
  const [progressId, setProgressId] = useState(null);
  const [pct, setPct] = useState(0);
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");
  const pollRef = useRef(null);

  const token = localStorage.getItem("token");
  const headers = { "Authorization": `Bearer ${token || ""}`, "Content-Type": "application/json" };
  const BASE = `${config.API_BASE_URL}/interactive-comic-strip-builder`;

  const start = async () => {
    setErr(""); setResult(null); setPct(0); setStatus("queued");
    try {
      const body = { params: { template } };
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
        <h3>Interactive Comic Strip Builder</h3>
        <button className="btn" onClick={start}>Run</button>
      </div>

      <div className="tool-inputs">
        <label htmlFor="icsb-template">Template</label>
        <select id="icsb-template" value={template} onChange={(e)=>setTemplate(e.target.value)}>
          <option>3-panel</option>
          <option>4-panel</option>
          <option>6-panel</option>
        </select>
      </div>

      {err && <div className="tool-err">{err}</div>}

      <div className="tool-progress">
        <div className="bar"><div className="fill" style={{ width: `${pct}%` }}/></div>
        <div className="meta">{status} • {pct}%</div>
      </div>

      {result && (
        <div className="tool-result">
          <div className="panel-grid">
            {(result.project?.panels || []).map(p => (
              <div key={p.idx} className="panel-card">
                <div className="slot">{p.image_url ? <img src={p.image_url} alt={`Panel ${p.idx}`} /> : "Image slot"}</div>
                <input className="caption-input" placeholder="Caption…" defaultValue={p.caption || ""} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}