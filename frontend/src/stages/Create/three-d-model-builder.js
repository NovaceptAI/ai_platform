import React, { useEffect, useRef, useState } from "react";
import "../../config"; // for type-only; actual import below
import config from "../../config";
import "./three-d-model-builder.css";

export default function ThreeDModelBuilder() {
  const [prompt, setPrompt] = useState("snowman with carrot nose");
  const [progressId, setProgressId] = useState(null);
  const [pct, setPct] = useState(0);
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");
  const pollRef = useRef(null);

  const token = localStorage.getItem("token");
  const headers = {
    "Authorization": `Bearer ${token || ""}`,
    "Content-Type": "application/json",
  };
  const BASE = `${config.API_BASE_URL}/three-d-model-builder`;

  const start = async () => {
    setErr("");
    setResult(null);
    setPct(0);
    setStatus("queued");
    try {
      const body = { params: { prompt } };
      const r = await fetch(`${BASE}/start`, { method: "POST", headers, body: JSON.stringify(body) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || "Failed to start");
      setProgressId(d.progress_id);
    } catch (e) {
      setErr(e.message || String(e));
      setStatus("failed");
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
        setPct(pd.percentage || 0);
        setStatus(pd.status);
        if (pd.status === "done") {
          clearInterval(pollRef.current);
          const rr = await fetch(`${BASE}/results/${progressId}`, { headers });
          const rd = await rr.json();
          if (!rr.ok) throw new Error(rd.error || "Results error");
          setResult(rd);
        }
        if (pd.status === "failed") {
          clearInterval(pollRef.current);
        }
      } catch (e) {
        setErr(e.message || String(e));
        clearInterval(pollRef.current);
      }
    }, 1100);
    return () => pollRef.current && clearInterval(pollRef.current);
  }, [progressId]);

  const copyJSON = async () => {
    if (!result) return;
    await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
  };

  return (
    <div className="tool-card">
      <div className="tool-head">
        <h3>3D Model Builder</h3>
        <button className="btn" onClick={start}>Run</button>
      </div>

      <div className="tool-inputs">
        <label htmlFor="td-prompt">Prompt</label>
        <input id="td-prompt" value={prompt} onChange={(e)=>setPrompt(e.target.value)} placeholder="Describe the scene..." />
      </div>

      {err && <div className="tool-err">{err}</div>}

      <div className="tool-progress">
        <div className="bar"><div className="fill" style={{ width: `${pct}%` }}/></div>
        <div className="meta">{status} • {pct}%</div>
      </div>

      {result && (
        <div className="tool-result">
          <div className="tool-actions">
            <button className="btn" onClick={copyJSON}>Copy JSON</button>
          </div>
          <pre>{JSON.stringify(result, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}