import React, { useEffect, useMemo, useRef, useState } from "react";
import config from "../../config";
import "./learn-by-drawing.css";

function makeCirclePoints(cx=100, cy=100, r=60, n=40){
  const pts = [];
  for (let i=0;i<n;i++){
    const a = (2*Math.PI*i)/n;
    pts.push([cx + r*Math.cos(a), cy + r*Math.sin(a)]);
  }
  return pts;
}

export default function LearnByDrawing() {
  // In the future: replace with a real canvas & captured paths.
  const [paths, setPaths] = useState([]);
  const addSampleCircle = () => setPaths([{ points: makeCirclePoints() }]);
  const clearPaths = () => setPaths([]);

  const [progressId, setProgressId] = useState(null);
  const [pct, setPct] = useState(0);
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");
  const pollRef = useRef(null);

  const token = localStorage.getItem("token");
  const headers = { "Authorization": `Bearer ${token || ""}`, "Content-Type": "application/json" };
  const BASE = `${config.API_BASE_URL}/learn-by-drawing`;

  const start = async () => {
    setErr(""); setResult(null); setPct(0); setStatus("queued");
    try {
      const body = { params: { paths } };
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
        <h3>Learn by Drawing</h3>
        <button className="btn" onClick={start}>Analyze</button>
      </div>

      <div className="tool-inputs">
        <div className="row">
          <button className="btn" onClick={addSampleCircle}>Add Sample Circle Path</button>
          <button className="btn" onClick={clearPaths}>Clear Paths</button>
        </div>
        <details>
          <summary>Paths JSON</summary>
          <pre>{JSON.stringify(paths, null, 2)}</pre>
        </details>
      </div>

      {err && <div className="tool-err">{err}</div>}

      <div className="tool-progress">
        <div className="bar"><div className="fill" style={{ width: `${pct}%` }}/></div>
        <div className="meta">{status} • {pct}%</div>
      </div>

      {result && (
        <div className="tool-result">
          <h4>Detected</h4>
          <ul>{(result.detected || []).map((d,i)=><li key={i}>{d.shape} • {d.confidence}</li>)}</ul>
          <h4>Feedback</h4>
          <ul>{(result.feedback || []).map((t,i)=><li key={i}>{t}</li>)}</ul>
          <h4>Quiz</h4>
          <ul>{(result.quiz || []).map((q,i)=><li key={i}>{q.q} — {q.a.join(", ")} (answer index: {q.correct})</li>)}</ul>
        </div>
      )}
    </div>
  );
}