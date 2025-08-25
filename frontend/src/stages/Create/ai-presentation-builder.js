import React, { useEffect, useRef, useState } from "react";
import config from "../../config";
import "./ai-presentation-builder.css";

export default function AiPresentationBuilder() {
  const [topic, setTopic] = useState("Photosynthesis");
  const [audience, setAudience] = useState("Grade 8");
  const [slides, setSlides] = useState(8);

  const [progressId, setProgressId] = useState(null);
  const [pct, setPct] = useState(0);
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");
  const pollRef = useRef(null);

  const token = localStorage.getItem("token");
  const headers = { "Authorization": `Bearer ${token || ""}`, "Content-Type": "application/json" };
  const BASE = `${config.API_BASE_URL}/ai-presentation-builder`;

  const start = async () => {
    setErr(""); setResult(null); setPct(0); setStatus("queued");
    try {
      const body = { params: { topic, audience, slides } };
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

  const copyMarkdown = async () => {
    if (!result?.markdown) return;
    await navigator.clipboard.writeText(result.markdown);
  };

  return (
    <div className="tool-card">
      <div className="tool-head">
        <h3>AI Presentation Builder</h3>
        <button className="btn" onClick={start}>Run</button>
      </div>

      <div className="tool-inputs">
        <label htmlFor="apb-topic">Topic</label>
        <input id="apb-topic" value={topic} onChange={(e)=>setTopic(e.target.value)} />
        <label htmlFor="apb-audience">Audience</label>
        <input id="apb-audience" value={audience} onChange={(e)=>setAudience(e.target.value)} />
        <label htmlFor="apb-slides">Slides</label>
        <input id="apb-slides" type="number" min={5} max={20} value={slides} onChange={(e)=>setSlides(parseInt(e.target.value||"8",10))} />
      </div>

      {err && <div className="tool-err">{err}</div>}

      <div className="tool-progress">
        <div className="bar"><div className="fill" style={{ width: `${pct}%` }}/></div>
        <div className="meta">{status} • {pct}%</div>
      </div>

      {result && (
        <div className="tool-result">
          <div className="tool-actions">
            {result.markdown && <button className="btn" onClick={copyMarkdown}>Copy Markdown</button>}
          </div>
          <div className="slides">
            {(result.slides || []).map((s, i) => (
              <div key={i} className="slide">
                <div className="slide-title">{s.title}</div>
                <ul>{(s.bullets || []).map((b, j) => <li key={j}>{b}</li>)}</ul>
              </div>
            ))}
          </div>
          {result.markdown && (
            <details className="md-preview">
              <summary>Markdown</summary>
              <pre>{result.markdown}</pre>
            </details>
          )}
        </div>
      )}
    </div>
  );
}