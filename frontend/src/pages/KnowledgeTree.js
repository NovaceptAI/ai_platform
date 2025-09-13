import React, { useMemo, useState, useEffect } from "react";
import knowledgeData from "../data/knowledgeData"; // keep your data in one place
import "./KnowledgeTree.css"; // your existing CSS (see tiny additions below)
// at top of KnowledgeTree.jsx (after React imports)
import timelineImg from "../assets/flows/Timeline_Path.png";
import codecraftImg from "../assets/flows/CodeCraft_&_Systems_Thinking_Path.png";
import deepReadingImg from "../assets/flows/Deep_Reading_&_Investigation.png";
import stemImg from "../assets/flows/STEM_Fundamentals.png";
import languageImg from "../assets/flows/Language_Learning_Path.png";
import creativeImg from "../assets/flows/Creative_Arts_&_Media_Path.png";

/* -----------------------------
   Helper utilities
----------------------------- */
function stageColor(stage) {
  switch (stage) {
    case "Discover": return "#2563eb";
    case "Organize": return "#f59e0b";
    case "Master": return "#22c55e";
    case "Create": return "#8b5cf6";
    case "Collaborate": return "#ec4899";
    default: return "#374151";
  }
}
function collectIds(node, out = []) {
  out.push(node.id);
  (node.children || []).forEach(c => collectIds(c, out));
  return out;
}
function matches(term, node) {
  if (!term) return true;
  const t = term.toLowerCase();
  return (node.name || "").toLowerCase().includes(t) ||
         (node.description || "").toLowerCase().includes(t);
}
function filterTree(node, term) {
  if (!term) return node;
  const kids = (node.children || [])
    .map(c => filterTree(c, term))
    .filter(Boolean);
  if (matches(term, node) || kids.length) {
    return { ...node, children: kids };
  }
  return null;
}

// Which tree node shows which flow image
const flowImages = {
  timeline: timelineImg,
  codecraft: codecraftImg,
  deep_reading: deepReadingImg,
  stem: stemImg,
  language: languageImg,
  creative: creativeImg,
};

// Collect unique tools (only stage tools) and all stages
function collectToolsAndStages(node, tools = new Set(), stages = new Set(), parentStage = null) {
  // If this node has a stage, remember it
  const currentStage = node.stage || parentStage;
  if (node.stage) stages.add(node.stage);

  const kids = node.children || [];
  if (!kids.length && currentStage) {
    // Treat as a tool if it’s a leaf and we know its parent stage
    tools.add(node.name);
  }

  kids.forEach(c => collectToolsAndStages(c, tools, stages, currentStage));
  return { tools: Array.from(tools).sort(), stages: Array.from(stages).sort() };
}


// Filter by query + stage + tool, but keep parents of matches
function filterTreeWith(node, { query, stage, tool }) {
  const q = (query || "").toLowerCase();

  const nameHit =
    !q || (node.name || "").toLowerCase().includes(q) ||
    (node.description || "").toLowerCase().includes(q);

  const stageHit = !stage || node.stage === stage;
  const toolHit = !tool || (node.name === tool);

  const kids = (node.children || [])
    .map(c => filterTreeWith(c, { query, stage, tool }))
    .filter(Boolean);

  // if a child matched, keep this parent
  if (kids.length) return { ...node, children: kids };

  // otherwise, keep node only if it matches all active filters
  const okQuery = !q || nameHit;
  const okStage = !stage || stageHit;
  const okTool  = !tool || toolHit;

  return (okQuery && okStage && okTool) ? { ...node, children: [] } : null;
}

// Find a node by name (for auto-selecting a tool) and return its ancestor chain
function findNodeAndPathByName(node, name, path = []) {
  const nextPath = [...path, node];
  if (node.name === name) return { node, path: nextPath };
  for (const c of (node.children || [])) {
    const r = findNodeAndPathByName(c, name, nextPath);
    if (r) return r;
  }
  return null;
}


/* -----------------------------
   Embedded “Docs” content
   (add/edit as you like)
----------------------------- */
const docsSections = [
  {
    id: "system-overview",
    title: "System Overview",
    items: [
      { h: "Architecture", p: "Frontend (React), Backend (Flask/FastAPI), Workers (Celery/Redis), DB (Postgres), Storage (Azure Blob – Knowledge Vault), AI (Azure OpenAI + in-house models)." },
      { h: "Data Flow", p: "Upload → Process (workers) → Persist (DB + Vault) → Surface (dashboard/tools)." },
    ],
  },
  {
    id: "roles-permissions",
    title: "Roles & Permissions",
    items: [
      { h: "Roles", p: "Learner, Educator, Professional, Organization (admin)." },
      { h: "Groups", p: "Project Teams, Study Groups, Classroom Cohorts." },
      { h: "Access", p: "Vault items can be private/shared; project roles: owner, collaborator, viewer." },
    ],
  },
  {
    id: "onboarding",
    title: "Onboarding Flows",
    items: [
      { h: "Learner", p: "Pick a Learning Path → start Discover stage." },
      { h: "Educator", p: "Create course → assign paths → track progress." },
      { h: "Professional", p: "Create research project → connect sources → analyze." },
      { h: "Organization", p: "SSO, bulk users, role provisioning, workspace setup." },
    ],
  },
  {
    id: "tools",
    title: "Stage-by-Stage Tools",
    items: [
      { h: "Discover", p: "Summarization, Sentiment, Segmentation, Chronology, Timeline Explorer, Comparison, Document Analysis, Visual Study Guide, Evidence Extractor, Readability/Style, Topic/Entity/Tag Miner." },
      { h: "Organize", p: "Cluster Builder, Tag & Taxonomy, Collections/Boards, Concept Graph, Saved Views, Consolidation, Cross-Doc Deduper & Merge, Knowledge Vault/Folders, Governance, Review Queue, Export/Sync." },
      { h: "Master", p: "Interactive Quiz, AI Homework Helper, Flashcards, Learn by Drawing, Language Games, Virtual Science Lab, Coding Playground (Kids), Math Visualizer, STEM Challenges, Ethical AI Tutor." },
      { h: "Create", p: "Historical Timelines, AI Presentations, Data Stories, Story→Comics, Interactive Comics, AI Art (Kids), 3D Models." },
      { h: "Collaborate", p: "Digital Debate, Mind Mapping, Co-authoring & Peer Review, Live Quizzes, Showcase & Share." },
    ],
  },
  {
    id: "learning-paths",
    title: "Learning Paths (6)",
    items: [
      { h: "Timeline", p: "Discover→Organize→Master→Create→Collaborate; strong chronology/timeline outputs." },
      { h: "CodeCraft & Systems", p: "Coding, systems thinking, ethical AI practice." },
      { h: "Deep Reading & Investigation", p: "Close reading, evidence-first analysis." },
      { h: "STEM Fundamentals", p: "Math/Science labs, standards alignment, challenges." },
      { h: "Language Learning", p: "Leveling (CEFR), vocab games, comics, peer review." },
      { h: "Creative Arts & Media", p: "Prompts, visualization, comics, AI art & 3D." },
    ],
  },
  {
    id: "research",
    title: "Research Workspace",
    items: [
      { h: "Modules", p: "API Scraper, AI Browser, AI Chat, Live Knowledge Tracking, Knowledge Vault." },
      { h: "Sources", p: "Social (FB/IG/Twitter/TikTok/YouTube etc.), Search (Google/Bing/Baidu/Tor), Music (Spotify/iTunes), Edu/Library (Scholar/WorldCat/Books/Open Library/Wikipedia/Medium/Udemy), App Stores (Play/Apple), E-commerce (Amazon/Ebay/Flipkart), Others (Reverse Image, Products, Stack Overflow)." },
      { h: "File Types & Limits", p: "PDF, DOCX, PPTX, CSV, TXT, JSON, Audio, Video; size up to ~500MB (configurable)." },
    ],
  },
  {
    id: "api",
    title: "API (Example Spec)",
    items: [
      { h: "Auth: Login", p: "POST /api/auth/login { username, password } → { token }. Content-Type: application/json." },
      { h: "OAuth/JWT", p: "JWT bearer in Authorization header for protected endpoints." },
      { h: "Errors", p: "JSON error model: { error, code, details } with 4xx/5xx status codes." },
      { h: "Testing", p: "Use Postman collections; include environment for base URLs and auth." },
    ],
  },
  {
    id: "models",
    title: "AI Models",
    items: [
      { h: "Hosted GPT", p: "GPT-4/GPT-4o for reasoning, summarization, chat." },
      { h: "In-House", p: "Fine-tuned assistants for flashcards, recommendations, domain chats." },
      { h: "Open-Source", p: "LLaMA, Falcon, MPT for specific pipelines where allowed." },
      { h: "Mapping", p: "Which tool uses which model (e.g., Summarizer→GPT-4, Quiz Generator→FT-3.5, Recommender→in-house ranker)." },
    ],
  },
  {
  id: "governance",
  title: "Governance & Compliance",
  items: [
    { h: "Permissions & Access Control", p: "Roles (Learner, Educator, Professional, Org Admin); project-level permissions (Owner, Collaborator, Viewer); Vault access (Private, Shared, Org-wide); audit logging of access." },
    { h: "Data Privacy", p: "Data stored in Azure Blob Vault; encryption at-rest (AES-256) & in-transit (TLS 1.2+); retention policies (default 1 year, configurable); right-to-erase support." },
    { h: "File & Data Handling", p: "File types: PDF, DOCX, PPTX, CSV, TXT, JSON, Audio, Video; size up to 500MB; exports: JSON, CSV, PDF; virus scanning and validation on upload." },
    { h: "Compliance Standards", p: "Aligned with FERPA/GDPR; internal governance; JWT-secured APIs; regular patching & monitoring." },
    { h: "Quality Assurance", p: "Review queue for educator/admin; human-in-the-loop validation; deduplication & merge; version control for datasets/projects." },
    { h: "Monitoring & Reporting", p: "Audit logs of actions; compliance dashboards; alerts for suspicious activity or failed ingestion." },
  ],
},
  {
    id: "roadmap",
    title: "Roadmap / Future",
    items: [
      { h: "SRS", p: "Spaced-repetition flashcards." },
      { h: "Live Collab", p: "Co-editing, chat, annotation." },
      { h: "Tutor", p: "Contextual multi-session guidance." },
    ],
  },
];

/* -----------------------------
   Tree row component
----------------------------- */
function TreeNode({ node, expanded, toggle, select, selectedId, depth = 0 }) {
  const hasChildren = node.children && node.children.length > 0;
  const isOpen = expanded.has(node.id);
  const isSelected = selectedId === node.id;

  return (
    <li className="kt-node" data-depth={depth}>
      <div className={`kt-row ${isSelected ? "is-selected" : ""}`}>
        {hasChildren ? (
          <button
            className={`kt-toggle ${isOpen ? "open" : ""}`}
            aria-label={isOpen ? "Collapse" : "Expand"}
            aria-expanded={isOpen}
            onClick={() => toggle(node.id)}
          />
        ) : (
          <span className="kt-toggle placeholder" />
        )}

        <button
          className="kt-label"
          onClick={() => select(node)}
          title={node.description || ""}
        >
          <span
            className="kt-bullet"
            style={{ backgroundColor: stageColor(node.stage) }}
          />
          <span className="kt-name">{node.name}</span>
        </button>
      </div>

      {hasChildren && isOpen && (
        <ul className="kt-children" role="group">
          {node.children.map(child => (
            <TreeNode
              key={child.id}
              node={child}
              expanded={expanded}
              toggle={toggle}
              select={select}
              selectedId={selectedId}
              depth={depth + 1}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

/* -----------------------------
   Page component
----------------------------- */
export default function KnowledgeTree() {
  const [expanded, setExpanded] = useState(new Set(["root"]));
const [selected, setSelected] = useState(knowledgeData);
const [query, setQuery] = useState("");
const [rightTab, setRightTab] = useState("details");
const [openDocIds, setOpenDocIds] = useState(new Set(docsSections.map(s => s.id)));
const [isFlowOpen, setIsFlowOpen] = useState(false);

// NEW: dropdown state first
const [selectedStage, setSelectedStage] = useState(""); // e.g., "Discover"
const [selectedTool, setSelectedTool]   = useState(""); // exact tool name

// NEW: derive options next
const { tools: toolOptions, stages: stageOptions } = useMemo(
  () => collectToolsAndStages(knowledgeData),
  []
);

// NOW it's safe to compute filtered
const filtered = useMemo(() => {
  return filterTreeWith(knowledgeData, {
    query,
    stage: selectedStage || "",
    tool: selectedTool || ""
  });
}, [query, selectedStage, selectedTool]);

  function toggle(id) {
    setExpanded(prev => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  }
  function expandAll() { if (filtered) setExpanded(new Set(collectIds(filtered))); }
  function collapseAll() { setExpanded(new Set(["root"])); }
  function select(node) {
    setSelected(node);
    setExpanded(prev => {
        const n = new Set(prev);
        n.add(node.id);

        // Auto-open API Scraper’s first-level groups
        if (node.id === "rs_api" && node.children) {
        node.children.forEach(c => n.add(c.id));
        }

        // Auto-open Rules & Regulations top-level groups
        if (node.id === "rules" && node.children) {
        node.children.forEach(c => n.add(c.id));
        }

        // Auto-open Governance & Compliance sub-groups
        if (node.id === "ru_governance" && node.children) {
        node.children.forEach(c => n.add(c.id));
        }

        return n;
    });
    }



function openFlow() { setIsFlowOpen(true); }
function closeFlow() { setIsFlowOpen(false); }

  // Docs helpers
  function toggleDoc(id) {
    setOpenDocIds(prev => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  }

  // inside KnowledgeTree()
    useEffect(() => {
    if (!isFlowOpen) return;

    const onKey = (e) => { if (e.key === "Escape") closeFlow(); };
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);

    return () => {
        window.removeEventListener("keydown", onKey);
        document.body.style.overflow = prev;
    };
    }, [isFlowOpen]);

  return (
    <div className="kt-layout">
      {/* Left: Tree */}
      <div className="kt-left">
        <div className="kt-toolbar">
            <input
                className="kt-search"
                placeholder="Search…"
                value={query}
                onChange={e => setQuery(e.target.value)}
            />

            {/* NEW: Stage filter */}
            <select
                className="kt-select"
                value={selectedStage}
                onChange={e => {
                setSelectedStage(e.target.value);
                // clear selectedTool when changing stage to avoid over-filtering
                setSelectedTool("");
                }}
                title="Filter by Stage"
            >
                <option value="">All Stages</option>
                {stageOptions.map(s => (
                <option key={s} value={s}>{s}</option>
                ))}
            </select>

            {/* NEW: Tool filter */}
            <select
                className="kt-select"
                value={selectedTool}
                onChange={e => {
                const t = e.target.value;
                setSelectedTool(t);
                if (t) {
                    // Auto-select and expand the path to this tool
                    const hit = findNodeAndPathByName(knowledgeData, t);
                    if (hit) {
                    setSelected(hit.node);
                    setExpanded(prev => {
                        const n = new Set(prev);
                        hit.path.forEach(p => n.add(p.id));
                        return n;
                    });
                    }
                }
                }}
                title="Filter by Tool"
            >
                <option value="">All Tools</option>
                {toolOptions.map(t => (
                <option key={t} value={t}>{t}</option>
                ))}
            </select>

            <div className="kt-spacer" />
            <button className="kt-btn" onClick={expandAll}>Expand All</button>
            <button className="kt-btn" onClick={collapseAll}>Collapse All</button>
            </div>


        {filtered ? (
          <ul className="kt-tree" role="tree">
            <TreeNode
              node={filtered}
              expanded={expanded}
              toggle={toggle}
              select={select}
              selectedId={selected?.id}
            />
          </ul>
        ) : (
          <div className="kt-empty">No matches</div>
        )}
      </div>

      {/* Right: Tabs */}
      <aside className="kt-panel">
        <div className="kt-tabs">
          <button
            className={`kt-tab ${rightTab === "details" ? "active" : ""}`}
            onClick={() => setRightTab("details")}
          >
            Details
          </button>
          <button
            className={`kt-tab ${rightTab === "docs" ? "active" : ""}`}
            onClick={() => setRightTab("docs")}
          >
            Docs
          </button>
        </div>

        {rightTab === "details" ? (
            <div className="kt-details">
                <h2 className="kt-panel-title">{selected?.name || "Details"}</h2>
                <p className="kt-panel-desc">{selected?.description || "—"}</p>
                {selected?.stage && (
                <p className="kt-badge">
                    Stage: <span style={{ color: stageColor(selected.stage) }}>{selected.stage}</span>
                </p>
                )}

                {/* NEW: View Flow button for learning paths */}
                {flowImages[selected?.id] && (
                <button className="kt-btn kt-btn-primary" onClick={openFlow} style={{ marginTop: 12 }}>
                    View Flow
                </button>
                )}
            </div>
            ) : (
          <div className="kg-docs">
            <div className="kg-docs-toolbar">
              <button className="kg-docs-btn" onClick={() => setOpenDocIds(new Set(docsSections.map(s => s.id)))}>Expand All</button>
              <button className="kg-docs-btn" onClick={() => setOpenDocIds(new Set())}>Collapse All</button>
            </div>

            <div className="kg-docs-sections">
              {docsSections.map(sec => (
                <section key={sec.id} className="kg-docs-section" id={sec.id}>
                  <button className="kg-docs-title" onClick={() => toggleDoc(sec.id)} aria-expanded={openDocIds.has(sec.id)}>
                    {sec.title}
                    <span className={`kg-docs-caret ${openDocIds.has(sec.id) ? "open" : ""}`} />
                  </button>

                  {openDocIds.has(sec.id) && (
                    <div className="kg-docs-content">
                      {sec.items.map((it, i) => (
                        <div className="kg-docs-item" key={i}>
                          <h4>{it.h}</h4>
                          <p>{it.p}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              ))}
            </div>
          </div>
        )}
      </aside>
      {/* Flow Image Modal */}
{isFlowOpen && (
  <div className="flow-modal" role="dialog" aria-modal="true" onClick={closeFlow}>
    <div className="flow-modal__content" onClick={(e) => e.stopPropagation()}>
      <div className="flow-modal__bar">
        <div className="flow-modal__title">{selected?.name} • Flow</div>
        <button className="flow-modal__close" onClick={closeFlow} aria-label="Close">✕</button>
      </div>
      <div className="flow-modal__body">
        <img
          src={flowImages[selected?.id]}
          alt={`${selected?.name} flow`}
          className="flow-modal__image"
        />
      </div>
    </div>
  </div>
)}

    </div>
  );
}
