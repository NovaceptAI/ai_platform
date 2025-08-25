import React, { useEffect, useRef, useState } from "react";
import config from "../../config";
import "./story-to-comics-converter.css";

export default function StoryToComicsConverter() {
  const [story, setStory] = useState("Once upon a time. A fox appears. A child follows the fox into the forest.");
  const [panels, setPanels] = useState(6);
  const [style, setStyle] = useState("cartoon");
  const [generateImages, setGenerateImages] = useState(false);

  const [progressId, setProgressId] = useState(null);
  const [pct, setPct] = useState(0);
  const [status, setStatus] = useState("idle");
  const [result, setResult] = useState(null);
  const [err, setErr] = useState("");
  const pollRef = useRef(null);

  const token = localStorage.getItem("token");
  const headers = { "Authorization": `Bearer ${token || ""}`, "Content-Type": "application/json" };
  const BASE = `${config.API_BASE_URL}/story-to-comics-converter`;

  const start = async () => {
    setErr(""); setResult(null); setPct(0); setStatus("queued");
    try {
      const body = { params: { story, panels, style, generate_images: generateImages } };
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
        <h3>Story to Comics Converter</h3>
        <button className="btn" onClick={start}>Run</button>
      </div>

      <div className="tool-inputs">
        <label htmlFor="stc-story">Story</label>
        <textarea id="stc-story" rows={5} value={story} onChange={(e)=>setStory(e.target.value)} />
        <label htmlFor="stc-panels">Panels</label>
        <input id="stc-panels" type="number" min={1} max={12} value={panels} onChange={(e)=>setPanels(parseInt(e.target.value||"6",10))} />
        <label htmlFor="stc-style">Style</label>
        <select id="stc-style" value={style} onChange={(e)=>setStyle(e.target.value)}>
          <option value="cartoon">Cartoon</option>
          <option value="watercolor">Watercolor</option>
          <option value="comic">Comic</option>
        </select>
        <label className="checkbox">
          <input type="checkbox" checked={generateImages} onChange={(e)=>setGenerateImages(e.target.checked)} /> Generate images (Azure DALL·E)
        </label>
      </div>

      {err && <div className="tool-err">{err}</div>}

      <div className="tool-progress">
        <div className="bar"><div className="fill" style={{ width: `${pct}%` }}/></div>
        <div className="meta">{status} • {pct}%</div>
      </div>

      {result && (
        <div className="tool-result">
          <div className="panel-grid">
            {(result.panels || []).map(p => (
              <div key={p.idx} className="panel-card">
                {p.image_url ? <img src={p.image_url} alt={`Panel ${p.idx}`} /> : <div className="prompt">{p.image_prompt}</div>}
                <div className="caption">{p.caption}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}