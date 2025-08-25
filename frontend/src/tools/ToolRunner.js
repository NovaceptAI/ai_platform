import React, { useEffect, useState } from "react";
import config from "../config";
import "./ToolRunner.css";

export default function ToolRunner({ title, basePath, inputUI, buildPayload }) {
  const [progressId, setProgressId] = useState(null);
  const [pct, setPct] = useState(0);
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");

  const token = localStorage.getItem("token");
  const auth = { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" };

  const start = async () => {
    setErr(""); setResult(null); setPct(0); setStatus("queued");
    try {
      const body = buildPayload();
      const r = await fetch(`${config.API_BASE_URL}${basePath}/start`, { method: "POST", headers: auth, body: JSON.stringify(body) });
      const d = await r.json();
      if (!r.ok) throw new Error(d.error || "Failed to start");
      setProgressId(d.progress_id);
    } catch (e) { setErr(e.message); setStatus("failed"); }
  };

  useEffect(() => {
    if (!progressId) return;
    const t = setInterval(async () => {
      const rp = await fetch(`${config.API_BASE_URL}${basePath}/progress/${progressId}`, { headers: auth });
      const pd = await rp.json();
      if (!rp.ok) { setErr(pd.error || "Progress error"); clearInterval(t); return; }
      setPct(pd.percentage || 0); setStatus(pd.status);
      if (pd.status === "done") {
        clearInterval(t);
        const rr = await fetch(`${config.API_BASE_URL}${basePath}/results/${progressId}`, { headers: auth });
        const rd = await rr.json();
        if (rr.ok) setResult(rd); else setErr(rd.error || "Results error");
      }
      if (pd.status === "failed") clearInterval(t);
    }, 1100);
    return () => clearInterval(t);
  }, [progressId]);

  return (
    <div className="tool-card">
      <div className="tool-head">
        <h3>{title}</h3>
        <button className="btn" onClick={start}>Run</button>
      </div>
      {inputUI}
      {err && <div className="tool-err">{err}</div>}
      <div className="tool-progress">
        <div className="bar"><div className="fill" style={{ width: `${pct}%` }}/></div>
        <div className="meta">{status} • {pct}%</div>
      </div>
      {result && <div className="tool-result"><pre>{JSON.stringify(result, null, 2)}</pre></div>}
    </div>
  );
}