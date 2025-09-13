// src/pages/KnowledgeGraph.jsx
import React, { useEffect, useRef, useState, useMemo } from "react";
import "./ScoolishFlow.css";

/* ==============================
   CONFIG / CONSTANTS
============================== */
const ZOOM_MIN = 0.3;
const ZOOM_MAX = 2.5;
const NODE_RADIUS = 22;
const RING_MARGIN = 120;      // min space between rings
const LABEL_CHAR_PX = 7;      // label width approximation (px/char)
const SEQUENTIAL_DELAY = 70;  // ms between child reveals
const EXCLUSIVE_BRANCH = true; // collapse other top-level branches when opening one

const STAGE_COLORS = {
  Discover: "#2563eb",
  Organize: "#f59e0b",
  Master: "#22c55e",
  Create: "#8b5cf6",
  Collaborate: "#ec4899",
  Default: "#334155",
};

/* ==============================
   DATA (trim/add freely)
============================== */
const knowledgeData = {
  id: "root",
  name: "Scoolish",
  description: "Explorable Knowledge Map",
  children: [
    {
      id: "learning_paths",
      name: "Learning Paths",
      description: "Six curated learning paths → click to explore their stages and tools.",
      children: [
        {
          id: "timeline",
          name: "Timeline Path",
          description: "Discover → Organize → Practice → Create → Collaborate",
          children: [
            { id: "tl_disc", name: "Discover", stage: "Discover", children: [
              { id:"tl_comp", name:"Comparison" },
              { id:"tl_evid", name:"Evidence Extractor" },
              { id:"tl_read", name:"Readability & Style" },
              { id:"tl_chrono", name:"Chronology (date-strict)" },
              { id:"tl_sum", name:"Summarization" },
              { id:"tl_tlx", name:"Timeline Explorer" },
            ]},
            { id: "tl_org", name: "Organize", stage: "Organize", children: [
              { id:"tl_tag", name:"Tag & Taxonomy Manager" },
              { id:"tl_coll", name:"Collections / Boards" },
              { id:"tl_cg", name:"Concept Graph (events/actors map)" },
              { id:"tl_sv", name:"Saved Views" },
            ]},
            { id: "tl_master", name: "Practice & Mastery", stage: "Master", children: [
              { id:"tl_fcards", name:"Customizable Flashcard Creator" },
              { id:"tl_quiz", name:"Interactive Quiz Creator" },
            ]},
            { id: "tl_create", name: "Create", stage: "Create", children: [
              { id:"tl_dsb", name:"Data Story Builder" },
              { id:"tl_htb", name:"Historical Timeline Builder" },
              { id:"tl_aip", name:"AI Presentation Builder" },
            ]},
            { id: "tl_collab", name: "Collaborate", stage: "Collaborate", children: [
              { id:"tl_show", name:"Showcase & Share" },
              { id:"tl_debate", name:"Digital Debate Live" },
              { id:"tl_quizlive", name:"Quiz Competitions Live" },
            ]},
          ],
        },
        {
          id: "codecraft",
          name: "CodeCraft & Systems Thinking",
          description: "Code, systems, and ethical AI practice.",
          children: [
            { id:"cc_disc", name:"Discover", stage:"Discover", children:[
              { id:"cc_comp", name:"Comparison" },
              { id:"cc_sum", name:"Summarization" },
              { id:"cc_doc", name:"Document Analysis" },
              { id:"cc_seg", name:"Segmentation - docs/papers" },
            ]},
            { id:"cc_org", name:"Organize", stage:"Organize", children:[
              { id:"cc_tag", name:"Tag & Taxonomy Manager" },
              { id:"cc_coll", name:"Collections / Boards" },
              { id:"cc_cluster", name:"Cluster Builder" },
              { id:"cc_cg", name:"Concept Graph" },
              { id:"cc_sv", name:"Saved Views" },
            ]},
            { id:"cc_master", name:"Practice & Mastery", stage:"Master", children:[
              { id:"cc_ethics", name:"Ethical AI Tutor" },
              { id:"cc_fcards", name:"Customizable Flashcard Creator" },
              { id:"cc_hw", name:"AI Homework Creator & Helper" },
              { id:"cc_quiz", name:"Interactive Quiz Creator" },
              { id:"cc_code", name:"Code Playground - AI Coding" },
            ]},
            { id:"cc_create", name:"Create", stage:"Create", children:[
              { id:"cc_dsb", name:"Data Story Builder" },
              { id:"cc_aip", name:"AI Presentation Builder" },
            ]},
            { id:"cc_collab", name:"Collaborate", stage:"Collaborate", children:[
              { id:"cc_quizlive", name:"Quiz Competitions Live" },
              { id:"cc_mindmap", name:"Collaborative Mind Mapping" },
              { id:"cc_pair", name:"Co-authoring - Pair Programming" },
              { id:"cc_show", name:"Showcase & Share" },
            ]},
          ],
        },
        {
          id: "deep_reading",
          name: "Deep Reading & Investigation",
          description: "Close reading, evidence, and research.",
          children: [
            { id:"dr_disc", name:"Discover", stage:"Discover", children:[
              { id:"dr_chrono", name:"Chronology" },
              { id:"dr_sum", name:"Summarization" },
              { id:"dr_seg", name:"Segmentation" },
              { id:"dr_read", name:"Readability & Style" },
              { id:"dr_evid", name:"Evidence Extractor" },
              { id:"dr_doc", name:"Document Analysis" },
              { id:"dr_comp", name:"Comparison" },
            ]},
            { id:"dr_org", name:"Organize", stage:"Organize", children:[
              { id:"dr_coll", name:"Collections / Boards" },
              { id:"dr_tag", name:"Tag & Taxonomy Manager" },
              { id:"dr_cluster", name:"Cluster Builder" },
              { id:"dr_cg", name:"Concept Graph" },
              { id:"dr_sv", name:"Saved Views" },
            ]},
            { id:"dr_master", name:"Practice & Mastery", stage:"Master", children:[
              { id:"dr_fcards", name:"Customizable Flashcard Creator" },
              { id:"dr_hw", name:"AI Homework Creator & Helper" },
              { id:"dr_vsg", name:"Visual Study Guide / Study Pack" },
              { id:"dr_quiz", name:"Interactive Quiz Creator" },
            ]},
            { id:"dr_create", name:"Create", stage:"Create", children:[
              { id:"dr_cwp", name:"Creative Writing Prompts" },
              { id:"dr_dsb", name:"Data Story Builder" },
              { id:"dr_aip", name:"AI Presentation Builder" },
            ]},
            { id:"dr_collab", name:"Collaborate", stage:"Collaborate", children:[
              { id:"dr_peer", name:"Co-authoring & Peer Review" },
              { id:"dr_show", name:"Showcase & Share" },
            ]},
          ],
        },
        {
          id: "stem",
          name: "STEM Fundamentals",
          description: "Math, science, challenges, and presentations.",
          children: [
            { id:"st_disc", name:"Discover", stage:"Discover", children:[
              { id:"st_comp", name:"Comparison" },
              { id:"st_sum", name:"Summarization" },
              { id:"st_doc", name:"Document Analysis" },
              { id:"st_seg", name:"Segmentation" },
            ]},
            { id:"st_org", name:"Organize", stage:"Organize", children:[
              { id:"st_tag", name:"Tag & Taxonomy Manager" },
              { id:"st_coll", name:"Collections / Boards" },
              { id:"st_cluster", name:"Cluster Builder" },
              { id:"st_cg", name:"Concept Graph" },
              { id:"st_std", name:"Standards Alignment" },
              { id:"st_sv", name:"Saved Views" },
            ]},
            { id:"st_master", name:"Practice & Mastery", stage:"Master", children:[
              { id:"st_math", name:"Math Problem Visualizer" },
              { id:"st_lab", name:"Virtual Science Lab" },
              { id:"st_chal", name:"STEM Challenge Generator" },
              { id:"st_hw", name:"AI Homework Creator & Helper" },
              { id:"st_quiz", name:"Interactive Quiz Creator" },
            ]},
            { id:"st_create", name:"Create", stage:"Create", children:[
              { id:"st_3d", name:"3D Model Builder" },
              { id:"st_aip", name:"AI Presentation Builder" },
            ]},
            { id:"st_collab", name:"Collaborate", stage:"Collaborate", children:[
              { id:"st_show", name:"Showcase & Share" },
            ]},
          ],
        },
        {
          id: "language",
          name: "Language Learning",
          description: "Leveling, vocab, games, comics, and peer review.",
          children: [
            { id:"la_disc", name:"Discover", stage:"Discover", children:[
              { id:"la_sum", name:"Summarization" },
              { id:"la_sent", name:"Sentiment Analysis" },
              { id:"la_doc", name:"Document Analysis" },
              { id:"la_seg", name:"Segmentation" },
              { id:"la_read", name:"Readability / Leveling" },
            ]},
            { id:"la_org", name:"Organize", stage:"Organize", children:[
              { id:"la_coll", name:"Collections / Boards" },
              { id:"la_sv", name:"Saved Views" },
              { id:"la_cefr", name:"Tag & Taxonomy CEFR" },
            ]},
            { id:"la_master", name:"Practice & Mastery", stage:"Master", children:[
              { id:"la_draw", name:"Learn by Drawing (vocab/concepts)" },
              { id:"la_fcards", name:"Customizable Flashcard Creator" },
              { id:"la_hw", name:"AI Homework Creator & Helper" },
              { id:"la_quiz", name:"Interactive Quiz Creator" },
              { id:"la_games", name:"Language Learning Games / Coach" },
            ]},
            { id:"la_create", name:"Create", stage:"Create", children:[
              { id:"la_strip", name:"Interactive Comic Strip Builder" },
              { id:"la_comics", name:"Story to Comics Converter" },
              { id:"la_cwp", name:"Creative Writing Prompts" },
              { id:"la_aip", name:"AI Presentation Builder" },
            ]},
            { id:"la_collab", name:"Collaborate", stage:"Collaborate", children:[
              { id:"la_quizlive", name:"Quiz Competitions Live" },
              { id:"la_peer", name:"Co-authoring & Peer Review" },
              { id:"la_show", name:"Showcase & Share" },
            ]},
          ],
        },
        {
          id: "creative",
          name: "Creative Arts & Media",
          description: "Prompts, visualization, comics, AI art, and 3D.",
          children: [
            { id:"ca_disc", name:"Discover", stage:"Discover", children:[
              { id:"ca_sent", name:"Sentiment Analysis" },
              { id:"ca_sum", name:"Summarization" },
              { id:"ca_seg", name:"Segmentation" },
              { id:"ca_doc", name:"Document Analysis" },
            ]},
            { id:"ca_org", name:"Organize", stage:"Organize", children:[
              { id:"ca_tag", name:"Tag & Taxonomy Manager" },
              { id:"ca_coll", name:"Collections / Boards" },
              { id:"ca_cluster", name:"Cluster Builder" },
              { id:"ca_sv", name:"Saved Views" },
            ]},
            { id:"ca_master", name:"Practice & Mastery", stage:"Master", children:[
              { id:"ca_ethics", name:"Ethical AI Tutor" },
              { id:"ca_fcards", name:"Customizable Flashcard Creator - A-I-M-A-D-M-S-C" },
              { id:"ca_cps", name:"Creative Prompt Studio" },
              { id:"ca_storyviz", name:"Story Visualization" },
            ]},
            { id:"ca_create", name:"Create", stage:"Create", children:[
              { id:"ca_strip", name:"Interactive Comic Strip Builder" },
              { id:"ca_aip", name:"AI Presentation Builder" },
              { id:"ca_dsb", name:"Data Story Builder" },
              { id:"ca_art", name:"AI Art Creator for Kids" },
              { id:"ca_3d", name:"3D Model Builder" },
              { id:"ca_storyviz2", name:"Story Visualizer" },
              { id:"ca_story2comics", name:"Story → Comics Converter" },
            ]},
            { id:"ca_collab", name:"Collaborate", stage:"Collaborate", children:[
              { id:"ca_show", name:"Showcase & Share" },
              { id:"ca_mindmap", name:"Collaborative Mind Map" },
            ]},
          ],
        },
      ],
    },
    {
      id: "research",
      name: "Research",
      description: "Workspace: API Scraper, AI Browser, AI Chat, Live Knowledge, Vault.",
      children: [
        { id:"rs_api", name:"API Scraper" },
        { id:"rs_browser", name:"AI Browser" },
        { id:"rs_chat", name:"AI Chat" },
        { id:"rs_live", name:"Live Knowledge Tracking" },
        { id:"rs_vault", name:"Knowledge Vault" },
      ],
    },
    {
      id: "onboarding",
      name: "User Onboarding",
      description: "Learner / Educator / Professional / Organization flows.",
      children: [
        { id:"ob_learner", name:"Learner Flow" },
        { id:"ob_educator", name:"Educator Flow" },
        { id:"ob_prof", name:"Professional Flow" },
        { id:"ob_org", name:"Organizational Flow" },
      ],
    },
    {
      id: "rules",
      name: "Rules & Regulations",
      description: "File types, sizes, governance, and compliance.",
      children: [
        { id:"ru_types", name:"File Types (PDF, DOCX, PPTX, CSV, TXT, JSON, Audio, Video)" },
        { id:"ru_data", name:"Data Types (Text, Tables, Images, Audio Transcripts, JSON)" },
        { id:"ru_size", name:"Max File Size: 500 MB (example)" },
        { id:"ru_gov", name:"Governance & Compliance (Roles, Permissions, Vault, QA, Export)" },
      ],
    },
    {
      id: "roles",
      name: "Roles & Groups",
      description: "Learner, Educator, Professional, Organization; Teams, Study Groups, Cohorts.",
      children: [
        { id:"ro_roles", name:"Roles: Learner, Educator, Professional, Organization" },
        { id:"ro_groups", name:"Groups: Project Teams, Study Groups, Classroom Cohorts" },
      ],
    },
    {
      id: "models",
      name: "AI Models",
      description: "Hosted GPT, in-house fine-tunes, and open-source models.",
      children: [
        { id:"mo_gpt", name:"GPT (Hosted): GPT-4, GPT-4o" },
        { id:"mo_inhouse", name:"In-House (Fine-Tuned): Domain chats, Summarizers, Recommenders" },
        { id:"mo_oss", name:"Open-Source: LLaMA, Falcon, MPT" },
      ],
    },
  ],
};

/* ==============================
   UTILS (pure helpers)
============================== */
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const colorForNode = (n) => STAGE_COLORS[n.stage] || STAGE_COLORS.Default;

function computeRingRadii(w, h, maxDepth) {
  const shorter = Math.min(w, h);
  const base = shorter * 0.44; // leave padding
  const radii = [];
  for (let d = 1; d <= maxDepth; d++) radii.push(base + (d - 1) * RING_MARGIN);
  return radii;
}

function placeOnRing(children, cx, cy, baseRadius) {
  if (!children.length) return [];
  const maxLabel = Math.max(...children.map(c => (c.name || "").length), 6);
  const labelPad = Math.max(0, maxLabel * LABEL_CHAR_PX * 0.6);
  const R = baseRadius + labelPad;

  const pts = [];
  const n = children.length;
  const offset = -Math.PI / 2;
  for (let i = 0; i < n; i++) {
    const t = offset + (i * 2 * Math.PI) / n;
    pts.push({ x: cx + Math.cos(t) * R, y: cy + Math.sin(t) * R });
  }
  return pts;
}

function collectVisible(root, expanded) {
  const out = [];
  (function dfs(node, depth) {
    out.push({ node, depth });
    if (expanded.has(node.id) && node.children?.length) node.children.forEach(c => dfs(c, depth + 1));
  })(root, 0);
  return out;
}

function fitCameraToBounds(nodesIndex, setCamera, container) {
  const vals = Object.values(nodesIndex);
  if (!vals.length) return;
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const { x, y } of vals) {
    minX = Math.min(minX, x - NODE_RADIUS);
    minY = Math.min(minY, y - NODE_RADIUS);
    maxX = Math.max(maxX, x + NODE_RADIUS);
    maxY = Math.max(maxY, y + NODE_RADIUS);
  }
  const w = maxX - minX, h = maxY - minY;
  const pad = 80;
  const sx = (container.clientWidth - pad) / Math.max(1, w);
  const sy = (container.clientHeight - pad) / Math.max(1, h);
  const scale = clamp(Math.min(sx, sy), ZOOM_MIN, ZOOM_MAX);
  const cx = container.clientWidth / 2 - ((minX + maxX) / 2) * scale;
  const cy = container.clientHeight / 2 - ((minY + maxY) / 2) * scale;
  setCamera({ x: cx, y: cy, scale });
}

/* ==============================
   COMPONENT
============================== */
export default function KnowledgeGraph() {
  const canvasRef = useRef(null);
  const ctxRef = useRef(null);
  const containerRef = useRef(null);

  const [side, setSide] = useState({ open: false, title: "Details", desc: "Click any node to see details." });
  const [expanded, setExpanded] = useState(() => new Set(["root"])); // start with only root open
  const [camera, setCamera] = useState({ x: 0, y: 0, scale: 1 });
  const [nodesIndex, setNodesIndex] = useState({}); // id -> { node, x, y }

  /* --------- Layout (rings) --------- */
  const layout = useMemo(() => {
    const vis = collectVisible(knowledgeData, expanded);
    const maxDepth = Math.min(3, Math.max(...vis.map(v => v.depth))); // keep it readable
    const container = containerRef.current || { clientWidth: 1200, clientHeight: 800 };
    const CW = container.clientWidth, CH = container.clientHeight;

    const idx = {};
    const cx = 0, cy = 0;
    idx[knowledgeData.id] = { node: knowledgeData, x: cx, y: cy };

    const rings = computeRingRadii(CW, CH, maxDepth);

    // depth 1
    const d1 = (knowledgeData.children || []).filter(c => vis.some(v => v.node.id === c.id));
    const p1 = placeOnRing(d1, cx, cy, rings[0] || 260);
    d1.forEach((n, i) => { idx[n.id] = { node: n, x: p1[i].x, y: p1[i].y }; });

    // depth 2 & 3 under expanded nodes
    for (const n1 of d1) {
      if (!expanded.has(n1.id)) continue;
      const ch2 = (n1.children || []).filter(c => vis.some(v => v.node.id === c.id));
      const p2 = placeOnRing(ch2, idx[n1.id].x, idx[n1.id].y, rings[1] || 400);
      ch2.forEach((n, i) => { idx[n.id] = { node: n, x: p2[i].x, y: p2[i].y }; });

      for (const n2 of ch2) {
        if (!expanded.has(n2.id)) continue;
        const ch3 = (n2.children || []).filter(c => vis.some(v => v.node.id === c.id));
        const p3 = placeOnRing(ch3, idx[n2.id].x, idx[n2.id].y, rings[2] || 520);
        ch3.forEach((n, i) => { idx[n.id] = { node: n, x: p3[i].x, y: p3[i].y }; });
      }
    }
    return idx;
  }, [expanded]);

  // Keep index + auto-fit camera to visible area
  useEffect(() => {
    setNodesIndex(layout);
    const container = containerRef.current;
    if (container) fitCameraToBounds(layout, setCamera, container);
  }, [layout]);

  /* --------- Canvas setup / resize --------- */
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current || canvas.parentElement;
    const ctx = canvas.getContext("2d");
    ctxRef.current = ctx;

    function fit() {
      const { clientWidth, clientHeight } = container;
      canvas.width = clientWidth * devicePixelRatio;
      canvas.height = clientHeight * devicePixelRatio;
      ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
      draw();
    }
    const ro = new ResizeObserver(fit);
    ro.observe(container);
    fit();
    return () => ro.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Redraw whenever layout or camera changes
  useEffect(() => { draw(); /* eslint-disable-next-line */ }, [layout, camera]);

  /* --------- Drawing helpers --------- */
  function draw() {
    const canvas = canvasRef.current, ctx = ctxRef.current;
    if (!canvas || !ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    ctx.translate(camera.x, camera.y);
    ctx.scale(camera.scale, camera.scale);

    // Links
    ctx.lineWidth = Math.max(1, 1.5 / camera.scale);
    ctx.strokeStyle = "rgba(148,163,184,0.5)";
    (function link(parent) {
      const p = nodesIndex[parent.id];
      if (!p || !parent.children) return;
      for (const c of parent.children) {
        const pc = nodesIndex[c.id];
        if (!pc) continue;
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
        ctx.lineTo(pc.x, pc.y);
        ctx.stroke();
        link(c);
      }
    })(knowledgeData);

    // Nodes + labels
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    for (const { node, x, y } of Object.values(nodesIndex)) {
      ctx.beginPath();
      ctx.fillStyle = colorForNode(node);
      ctx.strokeStyle = "#0f172a";
      ctx.lineWidth = 1 / camera.scale;
      ctx.arc(x, y, NODE_RADIUS, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      ctx.fillStyle = "#e5e7eb";
      ctx.font = `${12 / camera.scale}px Inter, system-ui, sans-serif`;
      let label = node.name || "";
      if (label.length > 28) label = label.slice(0, 27) + "…";
      ctx.fillText(label, x, y + NODE_RADIUS + 4 / camera.scale);
    }
    ctx.restore();
  }

  const screenToWorld = (sx, sy) => {
    const { scale, x: cx, y: cy } = camera;
    return { x: (sx - cx) / scale, y: (sy - cy) / scale };
  };

  function pickNode(sx, sy) {
    const { x, y } = screenToWorld(sx, sy);
    for (const { node, x: nx, y: ny } of Object.values(nodesIndex)) {
      const dx = nx - x, dy = ny - y;
      if (dx * dx + dy * dy <= NODE_RADIUS * NODE_RADIUS) return node;
    }
    return null;
  }

  /* --------- Interactions --------- */
  const lastPos = useRef({ x: 0, y: 0, dragging: false });

  function onPointerDown(e) { lastPos.current = { x: e.clientX, y: e.clientY, dragging: true }; }
  function onPointerMove(e) {
    if (!lastPos.current.dragging) return;
    const dx = e.clientX - lastPos.current.x;
    const dy = e.clientY - lastPos.current.y;
    lastPos.current.x = e.clientX; lastPos.current.y = e.clientY;
    setCamera(c => ({ ...c, x: c.x + dx, y: c.y + dy }));
  }
  function onPointerUp() { lastPos.current.dragging = false; }

  function onWheel(e) {
    e.preventDefault();
    const scaleDelta = e.deltaY < 0 ? 1.1 : 0.9;
    setCamera(c => {
      const newScale = clamp(c.scale * scaleDelta, ZOOM_MIN, ZOOM_MAX);
      // zoom around cursor
      const rect = canvasRef.current.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      const wx = (mx - c.x) / c.scale, wy = (my - c.y) / c.scale;
      const nx = mx - wx * newScale, ny = my - wy * newScale;
      return { scale: newScale, x: nx, y: ny };
    });
  }

  // 🔹 Sequential expand to reduce clutter
  function expandSequential(node) {
    setExpanded(prev => {
      const next = new Set(prev);

      // Exclusive top-level branch
      if (EXCLUSIVE_BRANCH && node.id !== "root") {
        const L1 = (knowledgeData.children || []).map(n => n.id);
        if (L1.includes(node.id)) { next.clear(); next.add("root"); }
      }

      // collapse if already open
      if (next.has(node.id)) { next.delete(node.id); return next; }

      // open the clicked node now
      next.add(node.id);

      // stagger children visibility (one level)
      if (node.children?.length) {
        node.children.forEach((child, i) => {
          setTimeout(() => {
            setExpanded(cur => {
              const copy = new Set(cur);
              copy.add(node.id);
              return copy;
            });
          }, i * SEQUENTIAL_DELAY);
        });
      }
      return next;
    });
  }

  function onClick(e) {
    // ignore quick drags
    if (Math.hypot(e.movementX, e.movementY) > 2 && lastPos.current.dragging) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const hit = pickNode(e.clientX - rect.left, e.clientY - rect.top);

    if (!hit) { setSide(s => ({ ...s, open: false })); return; }

    if (hit.children?.length) expandSequential(hit);

    setSide({
      open: true,
      title: hit.name || "Details",
      desc: hit.description || "—",
    });
  }

  function onReset() {
    setCamera({ x: 0, y: 0, scale: 1 });
    setExpanded(new Set(["root"]));
    setSide({ open: false, title: "Details", desc: "Click any node to see details." });
  }

  /* --------- JSX --------- */
  return (
    <div className="knowledge-graph">
      <div className="main-container" ref={containerRef}>
        <h1 className="title">Scoolish – Explorable Knowledge Map</h1>

        <div className="canvas-container" id="canvasContainer">
          <button className="reset-button" id="resetViewButton" onClick={onReset} title="Reset view" aria-label="Reset view">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
              <path strokeWidth="2" d="M3 12a9 9 0 1 0 3-6.7M3 4v6h6" />
            </svg>
          </button>

          <canvas
            id="knowledgeMapCanvas"
            ref={canvasRef}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerLeave={onPointerUp}
            onWheel={onWheel}
            onClick={onClick}
            style={{ width: "100%", height: "100%", display: "block" }}
          />
        </div>

        <aside className={`side-panel ${side.open ? "is-visible" : ""}`} id="sidePanel" aria-hidden={!side.open}>
          <div>
            <div className="panel-header">
              <div id="panelTitle">{side.title}</div>
              <button className="close-button" id="closePanelButton" onClick={() => setSide(s => ({ ...s, open: false }))} aria-label="Close">✕</button>
            </div>
            <div className="panel-content" id="panelDescription">{side.desc}</div>
          </div>
          <div style={{ fontSize: 12, color: "#6b7280" }}>Scoolish • Knowledge Map</div>
        </aside>
      </div>
    </div>
  );
}
