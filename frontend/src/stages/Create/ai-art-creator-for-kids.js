// frontend/src/stages/Create/ai-art-creator-for-kids.js
import React, { useEffect, useRef, useState } from "react";
import config from "../../config";
import "../../stages/StagesHome.css"; // keep if you had per-tool overrides; safe to leave

export default function AiArtCreatorForKids() {
  // form state
  const [prompt, setPrompt] = useState("A friendly dragon flying a kite");
  const [style, setStyle] = useState("crayon");
  const [count, setCount] = useState(4);

  // run state
  const [progressId, setProgressId] = useState(null);
  const [pct, setPct] = useState(0);
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");
  const pollRef = useRef(null);

  // auth + endpoints
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token || ""}`, "Content-Type": "application/json" };
  const BASE = `${config.API_BASE_URL}/ai-art-creator-for-kids`;

  // actions
  const start = async () => {
    setErr("");
    setResult(null);
    setPct(0);
    setStatus("queued");
    try {
      const body = { params: { prompt, style, count } };
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

  // simple progress bar using inline style (keeps your CSS contract)
  const Progress = () => (
    <div className="compact-progress" style={{ marginTop: 10 }}>
      <div
        style={{
          height: 8,
          background: "#e5e7eb",
          borderRadius: 999,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: "linear-gradient(90deg, #14b8a6, #0ea5e9)",
            transition: "width .4s ease",
          }}
        />
      </div>
      <div className="compact-status" style={{ justifyContent: "flex-end" }}>
        <span className="muted">{status} • {pct}%</span>
      </div>
    </div>
  );

  // responsive image grid using inline CSS (no extra classes required)
  const Images = () => (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
        gap: 14,
      }}
    >
      {(result?.images || []).map((img) => (
        <div
          key={img.idx}
          className="stage-card card-compact"
          style={{ background: "#fff" }}
        >
          <div style={{ borderRadius: 12, overflow: "hidden" }}>
            {img.image_url ? (
              <img
                src={img.image_url}
                alt={`art-${img.idx}`}
                style={{ width: "100%", height: 180, objectFit: "cover", display: "block" }}
              />
            ) : (
              <div className="rich-body" style={{ minHeight: 120 }}>
                <div className="muted">Prompt</div>
                <div>{img.prompt}</div>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className="stage-wrap">
      <header className="stage-header">
        <h1 className="stage-title">AI Art Creator for Kids</h1>
        <p className="stage-subtitle">Enter a playful idea, pick a style, and generate kid‑friendly art with Azure DALL·E.</p>
      </header>

      <div className="stage-grid" style={{ gridTemplateColumns: "minmax(260px, 380px) 1fr" }}>
        {/* Input / Controls */}
        <section className="stage-card" style={{ alignSelf: "start" }}>
          <div className="card-top" style={{ marginBottom: 10 }}>
            <div className="card-icon card-teal" style={{ color: "#064e3b", background: "linear-gradient(135deg,#99f6e4,#14b8a6)" }}>🎨</div>
            <h2 className="card-title">Prompt & Style</h2>
          </div>

          <form className="tool-form" onSubmit={(e) => { e.preventDefault(); start(); }}>
            <label className="form-label" htmlFor="aack-prompt">
              Prompt
              <input
                id="aack-prompt"
                className="form-input"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="e.g., A smiling robot painting a rainbow"
              />
            </label>

            <label className="form-label" htmlFor="aack-style">
              Style
              <select
                id="aack-style"
                className="form-select"
                value={style}
                onChange={(e) => setStyle(e.target.value)}
              >
                <option value="crayon">Crayon</option>
                <option value="watercolor">Watercolor</option>
                <option value="comic">Comic</option>
              </select>
            </label>

            <label className="form-label" htmlFor="aack-count">
              Number of images
              <input
                id="aack-count"
                className="form-input"
                type="number"
                min={1}
                max={6}
                value={count}
                onChange={(e) => setCount(parseInt(e.target.value || "4", 10))}
              />
            </label>

            <div className="form-actions">
              <button type="submit" className="btn-primary">Generate</button>
            </div>
          </form>

          {err && <div className="error-text" style={{ marginTop: 10 }}>{err}</div>}

          {/* Progress */}
          <Progress />
        </section>

        {/* Results */}
        <section className="stage-card" style={{ minHeight: 260 }}>
          <div className="card-top" style={{ marginBottom: 10 }}>
            <div className="card-icon card-purple" style={{ color: "#2e1065", background: "linear-gradient(135deg,#c4b5fd,#8b5cf6)" }}>🖼️</div>
            <h2 className="card-title">Results</h2>
          </div>

          {!result && (
            <div className="rich-body">
              <p className="muted">No images yet. Enter a prompt and click <strong>Generate</strong>.</p>
              <ul>
                <li>Keep prompts cheerful and age‑appropriate.</li>
                <li>Try different styles for variety.</li>
                <li>Up to 6 images per run.</li>
              </ul>
            </div>
          )}

          {result && <Images />}
        </section>
      </div>
    </div>
  );
}